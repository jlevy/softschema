/** Public API for softschema. Targets Node.js / Bun runtimes (uses `node:` builtins transitively). */
export {
  type CompileOptions,
  type CompileResult,
  compileSchema,
} from "./compile.js";
export {
  CONFORM_KIND,
  type ConformOptions,
  type ConformRecord,
  type ConformResult,
  conformArtifact,
} from "./conform.js";
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
export {
  REPAIR_KIND,
  type RepairResult,
  repairArtifact,
  repairYamlText,
} from "./repair.js";
export {
  type RepairAndValidateOptions,
  repairAndValidateArtifact,
} from "./repairValidate.js";
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
  clearValidatorCache,
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type ParsedDocument,
  type RepairRecord,
  readFrontmatterDoc,
  readYamlDoc,
  resolveBoundSchema,
  type SemanticResult,
  type StructuralResult,
  type ValidationResult,
  validateArtifact,
  validateSemantic,
  validateStructural,
  validateValues,
} from "./validate.js";
