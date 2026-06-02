/** Public API for @softschema/core. */
export { canonicalizeJsonSchema } from "./canonicalize.js";
export { compileSchema, type CompileResult, type CompileOptions } from "./compile.js";
export {
  type StructuralErrorRecord,
  structuralErrorRecord,
  renderStructuralMessage,
  normalizeAjvError,
} from "./errors.js";
export {
  type Contract,
  type SchemaStatus,
  type SchemaProfile,
  type SchemaMetadata,
  type SchemaWarning,
  type WarningCode,
  parseSchemaMetadata,
} from "./models.js";
export { Contracts } from "./registry.js";
export { stableStringify, canonicalJson, schemaSha256 } from "./settings.js";
export {
  validateArtifact,
  validateStructural,
  validateSemantic,
  validateValues,
  type ArtifactValidationResult,
  type StructuralResult,
  type SemanticResult,
  type ValidationResult,
  type MetadataMode,
} from "./validate.js";
export {
  softField,
  softFieldMeta,
  type SoftFieldOptions,
  type SoftOwner,
  type SoftTier,
  type RepairKind,
} from "./softField.js";
export { SchemaView, type FieldInfo } from "./schemaView.js";
export { regenerate, parseSections, type RegenerateResult } from "./generate.js";
