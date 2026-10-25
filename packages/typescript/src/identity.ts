/**
 * The one grammar every resource identity must follow.
 *
 * A resource identity is a root `$id`, a nested `$id`, the `$id` or key of a supplied
 * resource, or the `schemaId` that `compileSchema` writes as the root `$id`. Python's
 * `referencing` (through `urllib.parse`) and Ajv's fast-uri each normalize URIs their own
 * way, so an identity spelled in a form either library rewrites can name one resource for
 * one engine and another, or nothing, for the other. The grammar admits only spellings
 * both leave as written; Python's `_identity.py` lists the rules. A nested `$id` may
 * instead be a relative path reference under the same rules. Every other spelling is
 * `schema_invalid` with `reason: resource_identity` before either engine runs.
 *
 * Kept identical, pattern for pattern and check for check, to Python's `_identity.py`:
 * each pattern below is the Python pattern's text, anchored where Python uses
 * `fullmatch`.
 */

import { SchemaGraphError } from "./enforcement.js";

const PRINTABLE_ASCII = /^(?:[\x21-\x7e]+)$/;
const SCHEME = /^([A-Za-z][A-Za-z0-9+.-]*):/;
const LOWERCASE_SCHEME = /^(?:[a-z][a-z0-9+.-]*)$/;
// A `%` that does not start an uppercase escape of a reserved or non-ASCII byte. fast-uri
// decodes escaped unreserved characters and uppercases hex digits; Python does neither.
const BAD_ESCAPE = /%(?!(?:[01][0-9A-F]|2[0-9A-CF]|3[A-F]|40|5[B-E]|60|7[B-DF]|[89A-F][0-9A-F]))/;
const PATH = /^(?:(?:[A-Za-z0-9._~!$&'()*+,;=:@/-]|%[0-9A-F]{2})*)$/;
// No `'` in a query: the WHATWG URL parser escapes it there for http, https, and file.
const QUERY = /^(?:(?:[A-Za-z0-9._~!$&()*+,;=:@/?-]|%[0-9A-F]{2})+)$/;
// fast-uri's `URN_REG` with a lowercase namespace identifier, which fast-uri lowercases.
const URN_NAME = /^(?:[a-z0-9][a-z0-9-]{0,31}:(?:[A-Za-z0-9_!$'()*+,./:;=@-]|%[0-9A-F]{2})+)$/;
const UUID = /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/;
const HOST_NAME = /^(?:[a-z0-9-]+(?:\.[a-z0-9-]+)*)$/;
const IPV4 =
  /^(?:(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9]))$/;
const IPV6_TEXT = /^(?:[0-9a-f:]+)$/;
const IPV6_GROUP = /^(?:0|[1-9a-f][0-9a-f]{0,3})$/;
const PORT = /^(?:[1-9][0-9]{0,4})$/;
const DEFAULT_PORTS: Record<string, string> = { http: "80", https: "443" };
// The only schemes written with `//host`: both engines resolve relative references against
// them the same way. Python leaves a relative reference unresolved against any scheme
// outside `urllib.parse.uses_relative`, where fast-uri and the WHATWG parser resolve it.
const HOST_SCHEMES = new Set(["file", "http", "https"]);
// The schemes `urllib.parse` (`uses_netloc`) always writes with `//`: Python rewrites
// `scheme:path` to `scheme:///path`, and fast-uri's WebSocket handler rewrites `ws:` and
// `wss:`, so outside `HOST_SCHEMES` they are refused in either form.
const NETLOC_SCHEMES = new Set([
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
]);

const EMPTY = "not be empty";
const ASCII = "use printable ASCII with no whitespace";
const FRAGMENT = "not have a fragment, not even an empty #";
const ESCAPE = "spell percent-escapes as uppercase %HH and not escape letters, digits, or -._~";
const ABSOLUTE = "be an absolute URI";
const SCHEME_CASE = "use a lowercase scheme";
const NETLOC_SCHEME = "not use a scheme that takes //host, other than http, https, and file";
const HOST_SCHEME = "not use //host with a scheme other than http, https, or file";
const RELATIVE = "be a relative path, with no // and no colon in its first segment";
const EMPTY_QUERY = "not have an empty query";
const CHARACTERS = "use only URI characters";
const URN = "name a lowercase namespace identifier and a name, as in urn:example:name";
const URN_UUID = "follow urn:uuid: with a lowercase UUID";
const AUTHORITY_FORM = "use the scheme://host/path form for this scheme";
const FILE_HOST = "have an empty host, as in file:///path";
const AUTHORITY =
  "have a lowercase host name or a canonical IP address, an optional non-default port, " +
  "and no user information";
const EMPTY_PATH = "have a path, at least / after the host";
const NO_PATH = "have a path";
const OPAQUE_SLASH = "not start the path with / without //host";
const SEGMENT = "not have an empty (//), . or .. path segment";
const SEMICOLON = "not end the path with ;";

/**
 * Whether `text` is an IPv6 address in the RFC 5952 form fast-uri writes: lowercase hex
 * groups without leading zeros, the longest run of two or more zero groups (the leftmost
 * on a tie) written as `::`, and no embedded IPv4 address or zone.
 */
function canonicalIpv6(text: string): boolean {
  if (!IPV6_TEXT.test(text) || text.split("::").length - 1 > 1) return false;
  let groups: string[];
  if (text.includes("::")) {
    const [head = "", tail = ""] = text.split("::");
    const left = head ? head.split(":") : [];
    const right = tail ? tail.split(":") : [];
    const missing = 8 - left.length - right.length;
    if (missing < 1) return false;
    groups = [...left, ...Array<string>(missing).fill("0"), ...right];
  } else {
    groups = text.split(":");
  }
  if (groups.length !== 8 || !groups.every((group) => IPV6_GROUP.test(group))) return false;
  let bestStart = -1;
  let bestLength = 0;
  let runStart = -1;
  let runLength = 0;
  groups.forEach((group, index) => {
    if (group !== "0") {
      runLength = 0;
      return;
    }
    if (runLength === 0) runStart = index;
    runLength += 1;
    if (runLength > bestLength) {
      bestStart = runStart;
      bestLength = runLength;
    }
  });
  const canonical =
    bestLength < 2
      ? groups.join(":")
      : `${groups.slice(0, bestStart).join(":")}::${groups.slice(bestStart + bestLength).join(":")}`;
  return canonical === text;
}

function authorityProblem(scheme: string, authority: string): string | null {
  if (scheme === "file") return authority === "" ? null : FILE_HOST;
  let port: string | null = null;
  if (authority.startsWith("[")) {
    const end = authority.indexOf("]");
    if (end === -1 || !canonicalIpv6(authority.slice(1, end))) return AUTHORITY;
    const rest = authority.slice(end + 1);
    if (rest) {
      if (!rest.startsWith(":")) return AUTHORITY;
      port = rest.slice(1);
    }
  } else {
    const colon = authority.indexOf(":");
    const host = colon === -1 ? authority : authority.slice(0, colon);
    if (colon !== -1) port = authority.slice(colon + 1);
    if (!HOST_NAME.test(host)) return AUTHORITY;
    // A numeric last label makes the host an IPv4 address to URL parsers.
    if (/^[0-9]/.test(host.slice(host.lastIndexOf(".") + 1)) && !IPV4.test(host)) {
      return AUTHORITY;
    }
  }
  if (
    port !== null &&
    (!PORT.test(port) || Number(port) > 65535 || DEFAULT_PORTS[scheme] === port)
  ) {
    return AUTHORITY;
  }
  return null;
}

/**
 * The first rule `identity` breaks, as the end of a "must ..." sentence, or null. With
 * `absolute: false` (a nested `$id`), a relative path reference is allowed.
 */
export function identityProblem(identity: string, absolute: boolean): string | null {
  if (identity === "") return EMPTY;
  if (!PRINTABLE_ASCII.test(identity)) return ASCII;
  if (identity.includes("#")) return FRAGMENT;
  if (BAD_ESCAPE.test(identity)) return ESCAPE;
  const match = SCHEME.exec(identity);
  let scheme: string | null = null;
  let rest = identity;
  if (match === null) {
    if (absolute) return ABSOLUTE;
  } else {
    scheme = match[1] ?? "";
    if (!LOWERCASE_SCHEME.test(scheme)) return SCHEME_CASE;
    if (NETLOC_SCHEMES.has(scheme) && !HOST_SCHEMES.has(scheme)) return NETLOC_SCHEME;
    rest = identity.slice(match[0].length);
  }
  const question = rest.indexOf("?");
  const hierarchy = question === -1 ? rest : rest.slice(0, question);
  if (question !== -1) {
    const query = rest.slice(question + 1);
    if (query === "") return EMPTY_QUERY;
    if (!QUERY.test(query)) return CHARACTERS;
  }
  let path: string;
  if (scheme === "urn") {
    if (!URN_NAME.test(hierarchy)) return URN;
    if (hierarchy.startsWith("uuid:") && !UUID.test(hierarchy.slice(5))) return URN_UUID;
    path = hierarchy;
  } else if (hierarchy.startsWith("//")) {
    if (scheme === null) return RELATIVE;
    if (!HOST_SCHEMES.has(scheme)) return HOST_SCHEME;
    const slash = hierarchy.indexOf("/", 2);
    const authority = slash === -1 ? hierarchy.slice(2) : hierarchy.slice(2, slash);
    path = slash === -1 ? "" : hierarchy.slice(slash);
    const problem = authorityProblem(scheme, authority);
    if (problem !== null) return problem;
    if (path === "") return EMPTY_PATH;
  } else {
    if (scheme !== null && HOST_SCHEMES.has(scheme)) return AUTHORITY_FORM;
    path = hierarchy;
    if (path === "") return NO_PATH;
    if (scheme !== null && path.startsWith("/")) return OPAQUE_SLASH;
    if (scheme === null && (path.split("/")[0] ?? "").includes(":")) return RELATIVE;
  }
  if (scheme !== "urn" && !PATH.test(path)) return CHARACTERS;
  // fast-uri drops `.` and `..` segments and collapses `//`; Python keeps both.
  if (
    path.includes("//") ||
    path.split("/").some((segment) => segment === "." || segment === "..")
  ) {
    return SEGMENT;
  }
  if (path.endsWith(";")) return SEMICOLON;
  return null;
}

/**
 * Throw `resource_identity` when `identity` breaks the grammar. `label` names the identity
 * in the message, such as `the root $id`; the message is byte-identical to Python's.
 */
export function checkIdentity(identity: string, label: string, absolute: boolean): void {
  const problem = identityProblem(identity, absolute);
  if (problem !== null) {
    throw new SchemaGraphError(
      "resource_identity",
      `${label} must ${problem}, got ${JSON.stringify(identity)}`,
    );
  }
}

/** Check a root `$id`, which must be absolute; `compileSchema` uses it too. */
export function checkRootId(rootId: string): void {
  checkIdentity(rootId, "the root $id", true);
}
