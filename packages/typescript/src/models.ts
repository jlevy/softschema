/**
 * Language-neutral contract and metadata models. Field names mirror the Python
 * package; the `*Output` helpers emit the snake_case shapes the CLI serializes,
 * so JSON output is byte-identical across implementations.
 */

export type SchemaStatus = "soft" | "permissive" | "enforced";
export type SchemaProfile = "frontmatter-md" | "pure-yaml";

const SCHEMA_STATUSES: readonly SchemaStatus[] = ["soft", "permissive", "enforced"];

export function isSchemaStatus(value: unknown): value is SchemaStatus {
  return typeof value === "string" && (SCHEMA_STATUSES as readonly string[]).includes(value);
}

/**
 * Document-level `softschema:` metadata: the self-description quartet of
 * `contract` (what), `schema` (where the compiled schema lives), `envelope`
 * (which top-level key carries the payload), and `status` (how strictly).
 */
export interface SchemaMetadata {
  contractId: string;
  schema: string | null;
  envelope: string | null;
  status: SchemaStatus | null;
}

/** Public warning codes (the `document-*` family). */
export type WarningCode = "document-contract-mismatch" | "document-status-mismatch";

export interface SchemaWarning {
  code: WarningCode;
  message: string;
  severity: "info" | "warning";
}

/** One artifact payload contract: how to validate a document with this id. */
export interface Contract {
  readonly id: string;
  /** A label for the semantic model (e.g. a Zod module spec), or null when schema-only. */
  readonly model: string | null;
  readonly envelopeKey: string | null;
  readonly status: SchemaStatus;
  readonly profile: SchemaProfile;
  readonly schemaPath: string | null;
}

/** Python `type(x).__name__` for the type names used in error messages. */
export function pyTypeName(value: unknown): string {
  if (value === null || value === undefined) return "NoneType";
  if (Array.isArray(value)) return "list";
  if (typeof value === "string") return "str";
  if (typeof value === "boolean") return "bool";
  if (typeof value === "number") return Number.isInteger(value) ? "int" : "float";
  if (typeof value === "object") return "dict";
  return typeof value;
}

/** Raised for a malformed `softschema:` metadata block (→ document_softschema_invalid). */
export class SchemaMetadataError extends Error {}

// Enforced contract-ID grammar (mirrors Python `_CONTRACT_ID_RE`):
//   contract-id = [ namespace ":" ] name [ "/" version ]
//   namespace = segment *( "." segment ), segment = [a-z0-9_]+
//   name = [A-Za-z_][A-Za-z0-9_]*, version = [A-Za-z0-9_.-]+
const CONTRACT_ID_RE =
  /^(?:[a-z0-9_]+(?:\.[a-z0-9_]+)*:)?[A-Za-z_][A-Za-z0-9_]*(?:\/[A-Za-z0-9_.-]+)?$/;

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

const URN_RE = /^urn:([a-z0-9]|[a-z0-9][a-z0-9-]{0,30}[a-z0-9]):([A-Za-z0-9._~!$&'()*+,;=:@/%-]+)$/;
const HTTPS_PATH_RE = /^[A-Za-z0-9._~!$&'()*+,;=:@/%-]*$/;
const HTTPS_QUERY_RE = /^[A-Za-z0-9._~!$&'()*+,;=:@/?%-]*$/;
const UNRESERVED = /^[A-Za-z0-9._~-]$/;

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

/** Construct a contract after validating its public logical identity. */
export function defineContract(contract: Contract): Contract {
  const id = validateContractId(contract.id);
  return Object.freeze({ ...contract, id });
}

const KNOWN_METADATA_KEYS = new Set(["contract", "schema", "envelope", "status"]);

/** Require an optional metadata key, when present, to be a non-empty string. */
function checkOptionalString(obj: Record<string, unknown>, key: string): string | null {
  const value = obj[key];
  if (value === undefined || value === null) return null;
  if (typeof value !== "string" || value.length === 0) {
    throw new SchemaMetadataError(
      `softschema metadata '${key}' must be a non-empty string, got ${pyTypeName(value)}`,
    );
  }
  return value;
}

/** Parse compact (string) or expanded (mapping) document-level `softschema:` metadata. */
export function parseSchemaMetadata(raw: unknown): SchemaMetadata | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  if (typeof raw === "string") {
    return { contractId: validateContractId(raw), schema: null, envelope: null, status: null };
  }
  if (typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    // The spec makes unknown keys in the softschema: block a validation error.
    const unknown = Object.keys(obj).filter((key) => !KNOWN_METADATA_KEYS.has(key));
    if (unknown.length > 0) {
      throw new SchemaMetadataError(`softschema metadata has unknown keys: ${unknown.join(", ")}`);
    }
    const contract = validateContractId(obj.contract);
    const schema = checkOptionalString(obj, "schema");
    const envelope = checkOptionalString(obj, "envelope");
    let status: SchemaStatus | null = null;
    if (obj.status !== undefined && obj.status !== null) {
      if (!isSchemaStatus(obj.status)) {
        throw new SchemaMetadataError(`invalid softschema status: ${String(obj.status)}`);
      }
      status = obj.status;
    }
    return { contractId: contract, schema, envelope, status };
  }
  throw new SchemaMetadataError(
    `softschema metadata must be a string or mapping, got ${pyTypeName(raw)}`,
  );
}

/** The contract block as the CLI serializes it (snake_case, matching Python). */
export function contractToOutput(contract: Contract): Record<string, unknown> {
  return {
    envelope_key: contract.envelopeKey,
    id: contract.id,
    model: contract.model,
    profile: contract.profile,
    schema_path: contract.schemaPath,
    status: contract.status,
  };
}

/** The document metadata block as the CLI serializes it (snake_case, matching Python). */
export function metadataToOutput(metadata: SchemaMetadata | null): Record<string, unknown> | null {
  if (metadata === null) {
    return null;
  }
  return {
    contract: metadata.contractId,
    envelope: metadata.envelope,
    schema: metadata.schema,
    status: metadata.status,
  };
}
