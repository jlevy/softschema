/** Public API for softschema. Targets Node.js / Bun runtimes (uses `node:` builtins transitively). */
export { applyEnforcedExtras, canonicalizeJsonSchema } from "./canonicalize.js";
export {
  type CompileOptions,
  type CompileResult,
  compileSchema,
  SOFTSCHEMA_FORMAT_VERSION,
} from "./compile.js";
export {
  normalizeAjvError,
  renderStructuralMessage,
  type SchemaInvalidErrorRecord,
  type SchemaInvalidReason,
  type StructuralErrorRecord,
  schemaInvalidError,
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
  defineContract,
  parseSchemaMetadata,
  type SchemaMetadata,
  type SchemaProfile,
  type SchemaStatus,
  type SchemaWarning,
  validateContractId,
  validateSchemaId,
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
  ArtifactDirectoryError,
  ArtifactFrontmatterError,
  type ArtifactInputReason,
  type ArtifactParseReason,
  ArtifactRootError,
  type ArtifactValidationResult,
  artifactErrorRecord,
  artifactInputErrorRecord,
  artifactParseErrorRecord,
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type MetadataMode,
  type RawFrontmatter,
  readFrontmatter,
  readPureYamlArtifact,
  type SchemaResource,
  type SchemaResources,
  type SemanticResult,
  type StructuralResult,
  type ValidationResult,
  validateArtifact,
  validateSemantic,
  validateStructural,
  validateValues,
} from "./validate.js";
export {
  DEFAULT_VALIDATION_LIMITS,
  type ValidationLimitOverrides,
  type ValidationLimits,
} from "./yaml-value-domain.js";
