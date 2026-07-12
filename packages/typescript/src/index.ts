/** Public API for softschema. Targets Node.js / Bun runtimes (uses `node:` builtins transitively). */
export {
  type CompileOptions,
  type CompileResult,
  compileSchema,
} from "./compile.js";
export {
  type GeneratedSection,
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
export {
  type RepairKind,
  type SoftFieldOptions,
  type SoftOwner,
  type SoftTier,
  softField,
} from "./softField.js";
export {
  type ArtifactValidationResult,
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type SemanticResult,
  type StructuralResult,
  type ValidationResult,
  validateArtifact,
  validateSemantic,
  validateStructural,
  validateValues,
} from "./validate.js";
