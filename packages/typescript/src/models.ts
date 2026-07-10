/**
 * Language-neutral contract and metadata models. Field names mirror the Python
 * package; the `*Output` helpers emit the snake_case shapes the CLI serializes,
 * so JSON output is byte-identical across implementations.
 */
import {
  SchemaMetadataError,
  validateContractId,
  validateExtensionNamespace,
} from "./core/identity.js";
import { type JsonValue, normalizePortableValue } from "./core/value-domain.js";

export {
  SchemaMetadataError,
  validateContractId,
  validateExtensionNamespace,
  validateSchemaId,
} from "./core/identity.js";

export type SchemaStatus = "soft" | "permissive" | "enforced";
export type SchemaProfile = "frontmatter-md" | "pure-yaml";
export const ARTIFACT_FORMAT_VERSION = "1" as const;

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
  format?: "1";
  extensions?: Record<string, JsonValue>;
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

/** Construct a contract after validating its public logical identity. */
export function defineContract(contract: Contract): Contract {
  const id = validateContractId(contract.id);
  return Object.freeze({ ...contract, id });
}

const LEGACY_METADATA_KEYS = new Set(["contract", "schema", "envelope", "status"]);
const FORMAT_1_METADATA_KEYS = new Set([...LEGACY_METADATA_KEYS, "format", "extensions"]);
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
    const hasFormat = Object.hasOwn(obj, "format");
    if (hasFormat && obj.format !== ARTIFACT_FORMAT_VERSION) {
      throw new SchemaMetadataError('softschema metadata format must be the quoted string "1"');
    }
    const knownKeys = hasFormat ? FORMAT_1_METADATA_KEYS : LEGACY_METADATA_KEYS;
    // The spec makes unknown keys in the softschema: block a validation error.
    const unknown = Object.keys(obj).filter((key) => !knownKeys.has(key));
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
    if (!hasFormat) return { contractId: contract, schema, envelope, status };

    let extensions: Record<string, JsonValue> | undefined;
    if (Object.hasOwn(obj, "extensions")) {
      let normalized: JsonValue;
      try {
        normalized = normalizePortableValue(obj.extensions).value;
      } catch (error) {
        throw new SchemaMetadataError("softschema metadata extensions are not portable", {
          cause: error,
        });
      }
      if (normalized === null || typeof normalized !== "object" || Array.isArray(normalized)) {
        throw new SchemaMetadataError("softschema metadata extensions must be a mapping");
      }
      extensions = normalized;
      for (const namespace of Object.keys(extensions)) validateExtensionNamespace(namespace);
    }
    return {
      contractId: contract,
      schema,
      envelope,
      status,
      format: ARTIFACT_FORMAT_VERSION,
      ...(extensions === undefined ? {} : { extensions }),
    };
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
  const output: Record<string, unknown> = {
    contract: metadata.contractId,
    envelope: metadata.envelope,
    schema: metadata.schema,
    status: metadata.status,
  };
  if (metadata.format === ARTIFACT_FORMAT_VERSION) {
    output.format = ARTIFACT_FORMAT_VERSION;
    if (metadata.extensions !== undefined) output.extensions = metadata.extensions;
  }
  return output;
}
