"""Portable logical-contract and schema-resource identity rules."""

from __future__ import annotations

import re
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from urllib.parse import urlsplit

_CONTRACT_ID_RE = re.compile(
    r"^(?:[a-z0-9_]+(?:\.[a-z0-9_]+)*:)?[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z0-9_.-]+)?$"
)
_REVERSE_DNS_NAMESPACE_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$"
)
_URN_RE = re.compile(
    r"^urn:([a-z0-9]|[a-z0-9][a-z0-9-]{0,30}[a-z0-9]):"
    r"([A-Za-z0-9._~!$&'()*+,;=:@/%-]+)$"
)
_PERCENT_ESCAPE_RE = re.compile(r"%([0-9A-Fa-f]{2})")
_URI_ASCII_RE = re.compile(r"^[A-Za-z0-9:/?\[\]@!$&'()*+,;=._~%-]+$")
_HTTPS_PATH_RE = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@/%-]*$")
_HTTPS_QUERY_RE = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@/?%-]*$")
_IPV4_NUMBER_RE = re.compile(r"^(?:0[xX][0-9A-Fa-f]+|[0-9]+)$")
_UNRESERVED_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def validate_contract_id(value: object) -> str:
    """Return a valid logical contract ID or raise ``ValueError``."""
    if not isinstance(value, str) or not _CONTRACT_ID_RE.fullmatch(value):
        raise ValueError(
            f"malformed contract ID {value!r}: expected [namespace:]Name[/version] "
            "(namespace lowercase [a-z0-9_], dot-separated; name starts with a letter "
            "or underscore; at most one ':' and one '/'; no whitespace)"
        )
    return value


def _has_canonical_percent_escapes(value: str) -> bool:
    matches = list(_PERCENT_ESCAPE_RE.finditer(value))
    if value.count("%") != len(matches):
        return False
    return all(
        match.group(1) == match.group(1).upper()
        and int(match.group(1), 16) not in _UNRESERVED_BYTES
        for match in matches
    )


def _has_canonical_https_port(netloc: str, hostname: str, port: int | None) -> bool:
    if netloc.startswith("["):
        closing_bracket = netloc.find("]")
        suffix = netloc[closing_bracket + 1 :] if closing_bracket >= 0 else netloc
    else:
        suffix = netloc[len(hostname) :]
    if not suffix:
        return True
    if not suffix.startswith(":"):
        return False
    port_text = suffix[1:]
    return port is not None and port != 443 and port_text.isdecimal() and port_text == str(port)


def _canonical_https_host(hostname: str) -> str | None:
    if "%" in hostname:
        return None
    if ":" in hostname:
        try:
            return f"[{IPv6Address(hostname).compressed}]"
        except AddressValueError:
            return None
    if all(_IPV4_NUMBER_RE.fullmatch(label) for label in hostname.split(".")):
        try:
            return str(IPv4Address(hostname))
        except AddressValueError:
            return None
    return hostname


def validate_schema_id(value: object) -> str:
    """Return a canonical absolute HTTPS or URN schema identifier."""
    if not isinstance(value, str):
        raise ValueError(
            f"malformed schema ID {value!r}: expected a canonical absolute HTTPS or URN "
            "identifier without a fragment"
        )
    valid = bool(value) and _URI_ASCII_RE.fullmatch(value) is not None
    valid = valid and "#" not in value and "\\" not in value
    valid = valid and _has_canonical_percent_escapes(value)
    if valid and value.startswith("urn:"):
        valid = _URN_RE.fullmatch(value) is not None
    elif valid and value.startswith("https://"):
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            valid = False
        else:
            path_segments = parsed.path.split("/")
            canonical_host = _canonical_https_host(parsed.hostname) if parsed.hostname else None
            canonical_netloc = canonical_host
            if canonical_netloc is not None and port is not None:
                canonical_netloc = f"{canonical_netloc}:{port}"
            valid = (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and parsed.netloc == parsed.netloc.lower()
                and parsed.netloc == canonical_netloc
                and not parsed.hostname.endswith(".")
                and _has_canonical_https_port(parsed.netloc, parsed.hostname, port)
                and parsed.path.startswith("/")
                and _HTTPS_PATH_RE.fullmatch(parsed.path) is not None
                and _HTTPS_QUERY_RE.fullmatch(parsed.query) is not None
                and "." not in path_segments
                and ".." not in path_segments
                and not value.endswith(("?", "#"))
                and parsed.geturl() == value
            )
    else:
        valid = False
    if not valid:
        raise ValueError(
            f"malformed schema ID {value!r}: expected a canonical absolute HTTPS or URN "
            "identifier without a fragment"
        )
    return value


def validate_extension_namespace(value: object) -> str:
    """Return a canonical extension namespace or raise ``ValueError``."""
    if isinstance(value, str) and _REVERSE_DNS_NAMESPACE_RE.fullmatch(value):
        return value
    if isinstance(value, str) and value.startswith("https://"):
        try:
            return validate_schema_id(value)
        except ValueError:
            pass
    raise ValueError(
        f"invalid softschema extension namespace {value!r}: expected canonical HTTPS "
        "or lowercase reverse-DNS"
    )
