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

/** Document-level `softschema:` metadata. */
export interface SchemaMetadata {
  contractId: string;
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
function pyTypeName(value: unknown): string {
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

/** Parse compact (string) or expanded (mapping) document-level `softschema:` metadata. */
export function parseSchemaMetadata(raw: unknown): SchemaMetadata | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  if (typeof raw === "string") {
    return { contractId: raw, status: null };
  }
  if (typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    // The spec makes unknown keys in the softschema: block a validation error.
    const unknown = Object.keys(obj).filter((key) => key !== "contract" && key !== "status");
    if (unknown.length > 0) {
      throw new SchemaMetadataError(`softschema metadata has unknown keys: ${unknown.join(", ")}`);
    }
    const contract = obj.contract;
    if (typeof contract !== "string" || contract.length === 0) {
      throw new SchemaMetadataError("softschema metadata requires a non-empty string 'contract'");
    }
    let status: SchemaStatus | null = null;
    if (obj.status !== undefined && obj.status !== null) {
      if (!isSchemaStatus(obj.status)) {
        throw new SchemaMetadataError(`invalid softschema status: ${String(obj.status)}`);
      }
      status = obj.status;
    }
    return { contractId: contract, status };
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
  return { contract: metadata.contractId, status: metadata.status };
}
