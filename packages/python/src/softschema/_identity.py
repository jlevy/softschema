"""The one grammar every resource identity must follow.

A resource identity is a root ``$id``, a nested ``$id``, the ``$id`` or key of a
supplied resource, or the ``schema_id`` that ``compile_model`` writes as the root
``$id``. Python's ``referencing`` (through ``urllib.parse``) and Ajv's fast-uri each
normalize URIs their own way, so an identity spelled in a form either library rewrites
can name one resource for one engine and another, or nothing, for the other. The grammar
admits only spellings both leave as written:

- printable ASCII with no whitespace, and no fragment (not even an empty ``#``);
- percent-escapes as uppercase ``%HH``, never for letters, digits, or ``-._~``;
- a lowercase scheme, so an absolute identity is ``scheme:...``;
- ``//host`` only after ``http:``, ``https:``, or ``file:``, which require it: a lowercase
  host name, a canonical IPv4 or RFC 5952 IPv6 address, an optional non-default port, no
  user information, and a path of at least ``/`` (``file:`` takes an empty host, as in
  ``file:///path``);
- no other scheme ``urllib.parse`` writes with ``//`` (``ftp``, ``ws``, ``git``, ...);
  every other scheme uses the opaque form ``scheme:path``, its path not starting with
  ``/``;
- for ``urn:``, a lowercase namespace identifier and a name, as in ``urn:example:name``,
  and a lowercase UUID after ``urn:uuid:``;
- no empty (``//``), ``.``, or ``..`` path segment, no path ending in ``;``, no empty
  query, and no ``'`` in a query.

A nested ``$id`` may instead be a relative path reference under the same rules. Every
other spelling is ``schema_invalid`` with ``reason: resource_identity`` before either
engine runs. Kept identical, pattern for pattern and check for check, to TypeScript's
``identity.ts``.
"""

from __future__ import annotations

import json
import re

from softschema.enforcement import SchemaGraphError

_PRINTABLE_ASCII = re.compile(r"[\x21-\x7e]+")
_SCHEME = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*):")
_LOWERCASE_SCHEME = re.compile(r"[a-z][a-z0-9+.-]*")
# A `%` that does not start an uppercase escape of a reserved or non-ASCII byte. fast-uri
# decodes escaped unreserved characters and uppercases hex digits; Python does neither.
_BAD_ESCAPE = re.compile(
    r"%(?!(?:[01][0-9A-F]|2[0-9A-CF]|3[A-F]|40|5[B-E]|60|7[B-DF]|[89A-F][0-9A-F]))"
)
_PATH = re.compile(r"(?:[A-Za-z0-9._~!$&'()*+,;=:@/-]|%[0-9A-F]{2})*")
# No `'` in a query: the WHATWG URL parser escapes it there for http, https, and file.
_QUERY = re.compile(r"(?:[A-Za-z0-9._~!$&()*+,;=:@/?-]|%[0-9A-F]{2})+")
# fast-uri's `URN_REG` with a lowercase namespace identifier, which fast-uri lowercases.
_URN_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,31}:(?:[A-Za-z0-9_!$'()*+,./:;=@-]|%[0-9A-F]{2})+")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_HOST_NAME = re.compile(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*")
_IPV4 = re.compile(
    r"(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])"
)
_IPV6_TEXT = re.compile(r"[0-9a-f:]+")
_IPV6_GROUP = re.compile(r"0|[1-9a-f][0-9a-f]{0,3}")
_PORT = re.compile(r"[1-9][0-9]{0,4}")
_DEFAULT_PORTS = {"http": "80", "https": "443"}
# The only schemes written with `//host`: both engines resolve relative references against
# them the same way. Python leaves a relative reference unresolved against any scheme
# outside `urllib.parse.uses_relative`, where fast-uri and the WHATWG parser resolve it.
_HOST_SCHEMES = frozenset({"file", "http", "https"})
# The schemes `urllib.parse` (`uses_netloc`) always writes with `//`: Python rewrites
# `scheme:path` to `scheme:///path`, and fast-uri's WebSocket handler rewrites `ws:` and
# `wss:`, so outside `_HOST_SCHEMES` they are refused in either form.
_NETLOC_SCHEMES = frozenset(
    {
        "file",
        "ftp",
        "git",
        "git+ssh",
        "gopher",
        "http",
        "https",
        "imap",
        "itms-services",
        "mms",
        "nfs",
        "nntp",
        "prospero",
        "rsync",
        "rtsp",
        "rtsps",
        "rtspu",
        "sftp",
        "shttp",
        "snews",
        "svn",
        "svn+ssh",
        "telnet",
        "wais",
        "ws",
        "wss",
    }
)

_EMPTY = "not be empty"
_ASCII = "use printable ASCII with no whitespace"
_FRAGMENT = "not have a fragment, not even an empty #"
_ESCAPE = "spell percent-escapes as uppercase %HH and not escape letters, digits, or -._~"
_ABSOLUTE = "be an absolute URI"
_SCHEME_CASE = "use a lowercase scheme"
_NETLOC_SCHEME = "not use a scheme that takes //host, other than http, https, and file"
_HOST_SCHEME = "not use //host with a scheme other than http, https, or file"
_RELATIVE = "be a relative path, with no // and no colon in its first segment"
_EMPTY_QUERY = "not have an empty query"
_CHARACTERS = "use only URI characters"
_URN = "name a lowercase namespace identifier and a name, as in urn:example:name"
_URN_UUID = "follow urn:uuid: with a lowercase UUID"
_AUTHORITY_FORM = "use the scheme://host/path form for this scheme"
_FILE_HOST = "have an empty host, as in file:///path"
_AUTHORITY = (
    "have a lowercase host name or a canonical IP address, an optional non-default port, "
    "and no user information"
)
_EMPTY_PATH = "have a path, at least / after the host"
_NO_PATH = "have a path"
_OPAQUE_SLASH = "not start the path with / without //host"
_SEGMENT = "not have an empty (//), . or .. path segment"
_SEMICOLON = "not end the path with ;"


def _canonical_ipv6(text: str) -> bool:
    """Whether ``text`` is an IPv6 address in the RFC 5952 form fast-uri writes.

    That is lowercase hex groups without leading zeros, the longest run of two or more
    zero groups (the leftmost on a tie) written as ``::``, and no embedded IPv4 address
    or zone.
    """
    if not _IPV6_TEXT.fullmatch(text) or text.count("::") > 1:
        return False
    if "::" in text:
        head, tail = text.split("::")
        left = head.split(":") if head else []
        right = tail.split(":") if tail else []
        missing = 8 - len(left) - len(right)
        if missing < 1:
            return False
        groups = [*left, *(["0"] * missing), *right]
    else:
        groups = text.split(":")
    if len(groups) != 8 or not all(_IPV6_GROUP.fullmatch(group) for group in groups):
        return False
    best_start, best_length, run_start, run_length = -1, 0, -1, 0
    for index, group in enumerate(groups):
        if group != "0":
            run_length = 0
            continue
        if run_length == 0:
            run_start = index
        run_length += 1
        if run_length > best_length:
            best_start, best_length = run_start, run_length
    if best_length < 2:
        canonical = ":".join(groups)
    else:
        head_text = ":".join(groups[:best_start])
        tail_text = ":".join(groups[best_start + best_length :])
        canonical = f"{head_text}::{tail_text}"
    return canonical == text


def _authority_problem(scheme: str, authority: str) -> str | None:
    if scheme == "file":
        return None if authority == "" else _FILE_HOST
    port: str | None = None
    if authority.startswith("["):
        end = authority.find("]")
        if end == -1 or not _canonical_ipv6(authority[1:end]):
            return _AUTHORITY
        rest = authority[end + 1 :]
        if rest:
            if not rest.startswith(":"):
                return _AUTHORITY
            port = rest[1:]
    else:
        host, separator, port_text = authority.partition(":")
        if separator:
            port = port_text
        if not _HOST_NAME.fullmatch(host):
            return _AUTHORITY
        # A numeric last label makes the host an IPv4 address to URL parsers.
        if host.rsplit(".", 1)[-1][0].isdigit() and not _IPV4.fullmatch(host):
            return _AUTHORITY
    if port is not None and (
        not _PORT.fullmatch(port) or int(port) > 65535 or _DEFAULT_PORTS.get(scheme) == port
    ):
        return _AUTHORITY
    return None


def identity_problem(identity: str, *, absolute: bool) -> str | None:
    """The first rule ``identity`` breaks, as the end of a "must ..." sentence, or None.

    With ``absolute=False`` (a nested ``$id``), a relative path reference is allowed.
    """
    if identity == "":
        return _EMPTY
    if not _PRINTABLE_ASCII.fullmatch(identity):
        return _ASCII
    if "#" in identity:
        return _FRAGMENT
    if _BAD_ESCAPE.search(identity):
        return _ESCAPE
    match = _SCHEME.match(identity)
    scheme: str | None = None
    rest = identity
    if match is None:
        if absolute:
            return _ABSOLUTE
    else:
        found: str = match.group(1)
        if not _LOWERCASE_SCHEME.fullmatch(found):
            return _SCHEME_CASE
        if found in _NETLOC_SCHEMES and found not in _HOST_SCHEMES:
            return _NETLOC_SCHEME
        scheme = found
        rest = identity[match.end() :]
    hierarchy, question, query = rest.partition("?")
    if question:
        if query == "":
            return _EMPTY_QUERY
        if not _QUERY.fullmatch(query):
            return _CHARACTERS
    if scheme == "urn":
        if not _URN_NAME.fullmatch(hierarchy):
            return _URN
        if hierarchy.startswith("uuid:") and not _UUID.fullmatch(hierarchy[5:]):
            return _URN_UUID
        path = hierarchy
    elif hierarchy.startswith("//"):
        if scheme is None:
            return _RELATIVE
        if scheme not in _HOST_SCHEMES:
            return _HOST_SCHEME
        slash = hierarchy.find("/", 2)
        authority = hierarchy[2:] if slash == -1 else hierarchy[2:slash]
        path = "" if slash == -1 else hierarchy[slash:]
        problem = _authority_problem(scheme, authority)
        if problem is not None:
            return problem
        if path == "":
            return _EMPTY_PATH
    else:
        if scheme in _HOST_SCHEMES:
            return _AUTHORITY_FORM
        path = hierarchy
        if path == "":
            return _NO_PATH
        if scheme is not None and path.startswith("/"):
            return _OPAQUE_SLASH
        if scheme is None and ":" in path.split("/", 1)[0]:
            return _RELATIVE
    if scheme != "urn" and not _PATH.fullmatch(path):
        return _CHARACTERS
    # fast-uri drops `.` and `..` segments and collapses `//`; Python keeps both.
    if "//" in path or any(segment in (".", "..") for segment in path.split("/")):
        return _SEGMENT
    if path.endswith(";"):
        return _SEMICOLON
    return None


def check_identity(identity: str, label: str, *, absolute: bool) -> None:
    """Raise ``resource_identity`` when ``identity`` breaks the grammar.

    ``label`` names the identity in the message, such as ``the root $id``. The message is
    byte-identical to TypeScript's, the identity quoted as ``JSON.stringify`` quotes it.
    """
    problem = identity_problem(identity, absolute=absolute)
    if problem is not None:
        raise SchemaGraphError(
            "resource_identity",
            f"{label} must {problem}, got {json.dumps(identity, ensure_ascii=False)}",
        )


def check_root_id(root_id: str) -> None:
    """Check a root ``$id``, which must be absolute; ``compile_model`` uses it too."""
    check_identity(root_id, "the root $id", absolute=True)
