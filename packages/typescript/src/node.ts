/** Explicit Node.js/Bun library adapter, including path-based compatibility APIs. */
export { applyEnforcedExtras, canonicalizeJsonSchema } from "./canonicalize.js";
export {
  type CompileOptions,
  type CompileResult,
  compileSchema,
  SOFTSCHEMA_FORMAT_VERSION,
} from "./compile.js";
export {
  type NodeSource,
  type SourceAnchor,
  SourceMap,
  type SourcePoint,
  type SourceSpan,
} from "./core/source-map.js";
export {
  type EnforcementUnsupportedErrorRecord,
  normalizeAjvError,
  renderStructuralMessage,
  type SchemaInvalidErrorRecord,
  type SchemaInvalidReason,
  type SchemaViolationErrorRecord,
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
  ARTIFACT_FORMAT_VERSION,
  type Contract,
  type ContractDescriptor,
  type ContractWire,
  defineContract,
  defineContractDescriptor,
  parseSchemaMetadata,
  type SchemaMetadata,
  type SchemaMetadataWire,
  type SchemaProfile,
  type SchemaStatus,
  type SchemaWarning,
  validateContractId,
  validateExtensionNamespace,
  validateSchemaId,
  type WarningCode,
} from "./models.js";
export { Contracts } from "./registry.js";
export { bindContract, RuntimeContract } from "./runtime-contract.js";
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
  type ArtifactInputErrorRecord,
  type ArtifactInputReason,
  type ArtifactInputResult,
  type ArtifactInputSuccessResult,
  type ArtifactParseErrorRecord,
  type ArtifactParseReason,
  ArtifactRootError,
  type ArtifactStructuralErrorKind,
  type ArtifactStructuralErrorRecord,
  type ArtifactValidationOptions,
  type ArtifactValidationResult,
  artifactErrorRecord,
  artifactInputErrorRecord,
  artifactParseErrorRecord,
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type LegacyArtifactValidationOptions,
  type MetadataMode,
  type RawFrontmatter,
  readFrontmatter,
  readPureYamlArtifact,
  type SchemaResource,
  type SchemaResources,
  type SemanticIssue,
  type SemanticResult,
  type StructuralErrorWire,
  type StructuralIssue,
  type StructuralResult,
  type ValidationResult,
  type ValidationResultLegacyWire,
  validateArtifact,
  validateSemantic,
  validateStructural,
  validateValues,
} from "./validate.js";
export {
  DEFAULT_VALIDATION_LIMITS,
  type JsonObject,
  type JsonValue,
  type ParsedPortableYaml,
  PortableValueError,
  PortableYamlError,
  PortableYamlSyntaxError,
  parsePortableYaml,
  parsePortableYamlWithLocations,
  type ValidationLimitOverrides,
  type ValidationLimits,
} from "./yaml-value-domain.js";
