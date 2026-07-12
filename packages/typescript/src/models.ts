/**
 * Language-neutral contract and metadata models. Field names mirror the Python
 * package; the `*Output` helpers emit the same portable snake_case structures that
 * the Python CLI serializes.
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
  id: string;
  /** A label for the semantic model (e.g. a Zod module spec), or null when schema-only. */
  model: string | null;
  envelopeKey: string | null;
  status: SchemaStatus;
  profile: SchemaProfile;
  schemaPath: string | null;
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

/** Validate the contract-ID grammar; throws on a malformed value. */
export function checkContractId(contract: unknown): string {
  if (typeof contract !== "string" || contract.length === 0) {
    throw new SchemaMetadataError("softschema metadata requires a non-empty string 'contract'");
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
    return { contractId: checkContractId(raw), schema: null, envelope: null, status: null };
  }
  if (typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    // The spec makes unknown keys in the softschema: block a validation error.
    const unknown = Object.keys(obj).filter((key) => !KNOWN_METADATA_KEYS.has(key));
    if (unknown.length > 0) {
      throw new SchemaMetadataError(`softschema metadata has unknown keys: ${unknown.join(", ")}`);
    }
    const contract = checkContractId(obj.contract);
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
