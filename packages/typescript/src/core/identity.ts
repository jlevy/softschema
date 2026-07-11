/** Portable logical-contract and schema-resource identity rules. */

export class SchemaMetadataError extends Error {}

const CONTRACT_ID_RE =
  /^(?:[a-z0-9_]+(?:\.[a-z0-9_]+)*:)?[A-Za-z_][A-Za-z0-9_]*(?:\/[A-Za-z0-9_.-]+)?$/;
const URN_RE = /^urn:([a-z0-9]|[a-z0-9][a-z0-9-]{0,30}[a-z0-9]):([A-Za-z0-9._~!$&'()*+,;=:@/%-]+)$/;
const HTTPS_PATH_RE = /^[A-Za-z0-9._~!$&'()*+,;=:@/%-]*$/;
const HTTPS_QUERY_RE = /^[A-Za-z0-9._~!$&'()*+,;=:@/?%-]*$/;
const UNRESERVED = /^[A-Za-z0-9._~-]$/;
const REVERSE_DNS_NAMESPACE_RE =
  /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$/;

/** Validate the logical contract-ID grammar at every public boundary. */
export function validateContractId(contract: unknown): string {
  if (typeof contract !== "string" || contract.length === 0) {
    throw new SchemaMetadataError(
      "malformed contract ID: softschema metadata requires a non-empty string 'contract'",
    );
  }
  if (!CONTRACT_ID_RE.test(contract)) {
    throw new SchemaMetadataError(
      `malformed contract ID '${contract}': expected [namespace:]Name[/version] ` +
        "(namespace lowercase [a-z0-9_], dot-separated; name starts with a letter or " +
        "underscore; at most one ':' and one '/'; no whitespace)",
    );
  }
  return contract;
}

function hasCanonicalPercentEscapes(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] !== "%") continue;
    const digits = value.slice(index + 1, index + 3);
    if (!/^[0-9A-F]{2}$/.test(digits)) return false;
    if (UNRESERVED.test(String.fromCharCode(Number.parseInt(digits, 16)))) return false;
    index += 2;
  }
  return true;
}

/** Validate the canonical absolute schema-identifier profile. */
export function validateSchemaId(value: unknown): string {
  if (typeof value !== "string") {
    throw new Error(
      `malformed schema ID ${JSON.stringify(value)}: expected a canonical absolute HTTPS or ` +
        "URN identifier without a fragment",
    );
  }
  let valid =
    value.length > 0 &&
    /^[A-Za-z0-9:/?[\]@!$&'()*+,;=._~%-]+$/.test(value) &&
    !value.includes("#") &&
    !value.includes("\\") &&
    hasCanonicalPercentEscapes(value);

  if (valid && value.startsWith("urn:")) {
    valid = URN_RE.test(value);
  } else if (valid && value.startsWith("https://")) {
    try {
      const parsed = new URL(value);
      const remainder = value.slice("https://".length);
      const authorityEnd = remainder.search(/[/?#]/);
      const authority = authorityEnd === -1 ? remainder : remainder.slice(0, authorityEnd);
      const pathAndQuery = authorityEnd === -1 ? "" : remainder.slice(authorityEnd);
      const rawPath = pathAndQuery.split("?", 1)[0] ?? "";
      const pathSegments = rawPath.split("/");
      const portText = authority.match(/:(\d+)$/)?.[1];
      valid =
        parsed.protocol === "https:" &&
        parsed.hostname.length > 0 &&
        !authority.includes("@") &&
        authority === authority.toLowerCase() &&
        !authority.endsWith(":") &&
        !parsed.hostname.endsWith(".") &&
        (portText === undefined ||
          (portText === String(Number.parseInt(portText, 10)) && portText !== "443")) &&
        !pathSegments.includes(".") &&
        !pathSegments.includes("..") &&
        HTTPS_PATH_RE.test(parsed.pathname) &&
        HTTPS_QUERY_RE.test(parsed.search.slice(1)) &&
        !value.endsWith("?") &&
        parsed.href === value;
    } catch {
      valid = false;
    }
  } else {
    valid = false;
  }
  if (!valid) {
    throw new Error(
      `malformed schema ID ${JSON.stringify(value)}: expected a canonical absolute HTTPS or ` +
        "URN identifier without a fragment",
    );
  }
  return value;
}

/** Validate one canonical extension namespace. */
export function validateExtensionNamespace(value: unknown): string {
  if (typeof value === "string" && REVERSE_DNS_NAMESPACE_RE.test(value)) return value;
  if (typeof value === "string" && value.startsWith("https://")) {
    try {
      return validateSchemaId(value);
    } catch {
      // Replace the schema-ID diagnostic with the extension-specific contract below.
    }
  }
  throw new SchemaMetadataError(
    `invalid softschema extension namespace ${JSON.stringify(value)}: expected canonical ` +
      "HTTPS or lowercase reverse-DNS",
  );
}
