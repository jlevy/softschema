/** JSON-compatible normalized validation result contracts. */

import type {
  EnforcementUnsupportedErrorRecord,
  SchemaInvalidErrorRecord,
  SchemaViolationErrorRecord,
} from "../errors.js";
import type {
  ContractWire,
  SchemaMetadataWire,
  SchemaProfile,
  SchemaStatus,
  SchemaWarning,
} from "../models.js";
import type { JsonObject, JsonValue } from "./value-domain.js";

/** Trusted structural-validation input; normalized before entering wire results. */
export type SchemaResource = boolean | Record<string, unknown>;
export type SchemaResources = Readonly<Record<string, SchemaResource>>;

export type JsonPathSegment = string | number;

/** One implementation-specific semantic issue with a portable path and message. */
export interface SemanticIssue {
  code: string;
  path: JsonPathSegment[];
  message: string;
}

/** Stable parse failure from the artifact-input-v1 conformance schema. */
export interface ArtifactParseErrorRecord {
  kind: "parse_error";
  reason: ArtifactParseReason;
  message: string;
  source: string;
  path?: string;
  line?: number;
  column?: number;
}

/** Stable access failure from the artifact-input-v1 conformance schema. */
export interface ArtifactInputErrorRecord {
  kind: "input_error";
  reason: ArtifactInputReason;
  message: string;
  source: string;
}

/** Successful artifact-input-v1 record. */
export interface ArtifactInputSuccessResult {
  kind: "artifact_input";
  ok: true;
  source: string;
  profile: SchemaProfile;
  values: JsonObject;
}

/** Discriminated artifact-input-v1 result. */
export type ArtifactInputResult =
  | ArtifactInputSuccessResult
  | ArtifactParseErrorRecord
  | ArtifactInputErrorRecord;

/** Artifact-boundary failure kinds currently serialized in the structural layer. */
export type ArtifactStructuralErrorKind =
  | "contract_unknown"
  | "no_frontmatter"
  | "frontmatter_not_mapping"
  | "metadata_invalid"
  | "document_softschema_invalid"
  | "document_contract_mismatch"
  | "envelope_mismatch"
  | "envelope_ambiguous"
  | "envelope_missing"
  | "envelope_not_mapping"
  | "values_not_mapping"
  | "schema_missing";

/**
 * Artifact-boundary structural error. The conformance schema intentionally permits
 * kind-specific extension fields; those values remain restricted to the JSON domain.
 */
export interface ArtifactStructuralErrorRecord {
  kind: ArtifactStructuralErrorKind;
  message: string;
  contract_id?: string;
  expected?: JsonValue;
  actual?: JsonValue;
  path?: string;
  expected_key?: string;
  actual_keys?: string[];
  [key: string]: JsonValue | undefined;
}

/** Every error record accepted by the legacy structural layer. */
export type StructuralIssue =
  | SchemaViolationErrorRecord
  | SchemaInvalidErrorRecord
  | EnforcementUnsupportedErrorRecord
  | ArtifactStructuralErrorRecord
  | ArtifactParseErrorRecord
  | ArtifactInputErrorRecord;

/** Alias emphasizing that `StructuralIssue` is the public wire union. */
export type StructuralErrorWire = StructuralIssue;

export interface StructuralResult {
  ok: boolean;
  errors: StructuralIssue[];
  engine: "json_schema";
  skipped_reason: string | null;
}

export interface SemanticResult {
  ok: boolean;
  errors: SemanticIssue[];
  skipped_reason: string | null;
}

export interface ValidationResult {
  structural: StructuralResult;
  semantic: SemanticResult;
}

export interface ArtifactValidationResult {
  ok: boolean;
  output: ValidationResultLegacyWire;
}

/** Stable legacy single-artifact wire shape from validation-result-legacy. */
export interface ValidationResultLegacyWire {
  contract: ContractWire | null;
  contract_id: string;
  document_metadata: SchemaMetadataWire | null;
  path: string;
  profile: SchemaProfile;
  semantic: SemanticResult;
  status: SchemaStatus;
  structural: StructuralResult;
  values: JsonObject | null;
  warnings: SchemaWarning[];
}

export type MetadataMode = "enforced" | "advisory";

export interface RawFrontmatter {
  hasFence: boolean;
  value: unknown;
}

export type ArtifactParseReason = "frontmatter" | "syntax" | "root" | "value_domain";
export type ArtifactInputReason =
  | "not_found"
  | "unreadable"
  | "directory_requires_recursive"
  | "no_matches"
  | "discovery_limit";
