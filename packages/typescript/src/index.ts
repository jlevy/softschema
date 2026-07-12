/** Public API for softschema. Targets Node.js / Bun runtimes (uses `node:` builtins transitively). */
export { applyEnforcedExtras, canonicalizeJsonSchema } from "./canonicalize.js";
export {
  type CompileOptions,
  type CompileResult,
  compileSchema,
} from "./compile.js";
export {
  normalizeAjvError,
  renderStructuralMessage,
  type StructuralErrorRecord,
  structuralErrorRecord,
} from "./errors.js";
export {
  type GeneratedSection,
  parseSections,
  type RegenerateResult,
  regenerate,
} from "./generate.js";
export {
  type Contract,
  parseSchemaMetadata,
  type SchemaMetadata,
  type SchemaProfile,
  type SchemaStatus,
  type SchemaWarning,
  type WarningCode,
} from "./models.js";
export { Contracts } from "./registry.js";
export { type FieldInfo, SchemaView } from "./schemaView.js";
export { canonicalJson, schemaSha256, stableStringify } from "./settings.js";
export {
  type RepairKind,
  type SoftFieldOptions,
  type SoftOwner,
  type SoftTier,
  softField,
  softFieldMeta,
} from "./softField.js";
export {
  type ArtifactValidationResult,
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type MetadataMode,
  type RawFrontmatter,
  readFrontmatter,
  type SemanticResult,
  type StructuralResult,
  type ValidationResult,
  validateArtifact,
  validateSemantic,
  validateStructural,
  validateValues,
} from "./validate.js";
