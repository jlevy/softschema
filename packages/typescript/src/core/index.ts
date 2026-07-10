/**
 * Runtime-neutral softschema contract core.
 *
 * This entrypoint accepts and returns JSON-compatible values. It does not parse YAML,
 * touch the filesystem, load Zod models, dynamically import code, or implement a CLI.
 */
export {
  applyEnforcedExtras,
  canonicalizeJsonSchema,
  ENFORCEMENT_UNSUPPORTED_MESSAGE,
  EnforcementUnsupportedError,
} from "../canonicalize.js";
export {
  type EnforcementUnsupportedErrorRecord,
  renderStructuralMessage,
  type SchemaInvalidErrorRecord,
  type SchemaInvalidReason,
  type SchemaViolationErrorRecord,
  type StructuralErrorRecord,
  schemaInvalidError,
  structuralErrorRecord,
} from "../errors.js";
export {
  ARTIFACT_FORMAT_VERSION,
  type Contract,
  type ContractDescriptor,
  type ContractWire,
  contractToOutput,
  defineContract,
  defineContractDescriptor,
  isSchemaStatus,
  metadataToOutput,
  parseSchemaMetadata,
  pyTypeName,
  type SchemaMetadata,
  SchemaMetadataError,
  type SchemaMetadataWire,
  type SchemaProfile,
  type SchemaStatus,
  type SchemaWarning,
  validateContractId,
  validateExtensionNamespace,
  validateSchemaId,
  type WarningCode,
} from "../models.js";
export {
  firstUnsupportedPattern,
  isPortablePattern,
  PORTABLE_PATTERN_MAX_QUANTIFIER,
  PORTABLE_PATTERN_PROFILE,
  PortablePatternError,
  portablePatternMatches,
  type UnsupportedPattern,
} from "../portable-pattern.js";
export { Contracts } from "../registry.js";
export { canonicalJson, stableStringify } from "./canonical-json.js";
export { EnvelopeAmbiguityError, inferEnvelopeKey } from "./envelope.js";
export type {
  ArtifactInputErrorRecord,
  ArtifactInputReason,
  ArtifactInputResult,
  ArtifactInputSuccessResult,
  ArtifactParseErrorRecord,
  ArtifactParseReason,
  ArtifactStructuralErrorKind,
  ArtifactStructuralErrorRecord,
  ArtifactValidationResult,
  JsonPathSegment,
  MetadataMode,
  RawFrontmatter,
  SchemaResource,
  SchemaResources,
  SemanticIssue,
  SemanticResult,
  StructuralErrorWire,
  StructuralIssue,
  StructuralResult,
  ValidationResult,
  ValidationResultLegacyWire,
} from "./results.js";
export {
  canonicalPortableJsonSize,
  DEFAULT_VALIDATION_LIMITS,
  type JsonObject,
  type JsonValue,
  type NormalizedValue,
  normalizePortableValue,
  PortableValueError,
  PortableYamlError,
  resolveValidationLimits,
  type ValidationLimitOverrides,
  type ValidationLimits,
} from "./value-domain.js";
