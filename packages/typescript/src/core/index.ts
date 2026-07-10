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
  renderStructuralMessage,
  type SchemaInvalidErrorRecord,
  type SchemaInvalidReason,
  type StructuralErrorRecord,
  schemaInvalidError,
  structuralErrorRecord,
} from "../errors.js";
export {
  ARTIFACT_FORMAT_VERSION,
  type Contract,
  contractToOutput,
  defineContract,
  isSchemaStatus,
  metadataToOutput,
  parseSchemaMetadata,
  pyTypeName,
  type SchemaMetadata,
  SchemaMetadataError,
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
  ArtifactInputReason,
  ArtifactParseReason,
  ArtifactValidationResult,
  MetadataMode,
  RawFrontmatter,
  SchemaResource,
  SchemaResources,
  SemanticResult,
  StructuralResult,
  ValidationResult,
} from "./results.js";
export {
  canonicalPortableJsonSize,
  DEFAULT_VALIDATION_LIMITS,
  type JsonValue,
  type NormalizedValue,
  normalizePortableValue,
  PortableValueError,
  PortableYamlError,
  resolveValidationLimits,
  type ValidationLimitOverrides,
  type ValidationLimits,
} from "./value-domain.js";
