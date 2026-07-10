/**
 * Artifact validation: read Markdown frontmatter (or pure YAML), resolve the envelope,
 * and run structural validation against the compiled JSON Schema via ajv. The result
 * object serializes (via stableStringify) byte-identically to the Python CLI output.
 */
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import type { ValidateFunction } from "ajv/dist/2020.js";
import Ajv2020 from "ajv/dist/2020.js";
import type { z } from "zod";
import {
  applyEnforcedExtras,
  ENFORCEMENT_UNSUPPORTED_MESSAGE,
  EnforcementUnsupportedError,
} from "./canonicalize.js";
import { EnvelopeAmbiguityError, inferEnvelopeKey } from "./core/envelope.js";
import type {
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
} from "./core/results.js";
import {
  collapseAdditionalProperties,
  compareStructuralRecords,
  normalizeAjvError,
  type SchemaInvalidErrorRecord,
  type SchemaInvalidReason,
  type StructuralErrorRecord,
  schemaInvalidError,
} from "./errors.js";
import { isMapping } from "./guards.js";
import {
  type Contract,
  contractToOutput,
  metadataToOutput,
  parseSchemaMetadata,
  pyTypeName,
  type SchemaMetadata,
  SchemaMetadataError,
  type SchemaWarning,
  validateContractId,
  validateSchemaId,
} from "./models.js";
import { firstUnsupportedPattern } from "./portable-pattern.js";
import {
  DEFAULT_VALIDATION_LIMITS,
  normalizePortableValue,
  PortableValueError,
  PortableYamlSyntaxError,
  parsePortableYaml,
  resolveValidationLimits,
  type ValidationLimitOverrides,
} from "./yaml-value-domain.js";

export { EnvelopeAmbiguityError, inferEnvelopeKey } from "./core/envelope.js";
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
} from "./core/results.js";

const JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema";

const ARTIFACT_PARSE_MESSAGES: Record<ArtifactParseReason, string> = {
  frontmatter: "artifact frontmatter delimiters are malformed",
  syntax: "artifact is not valid YAML",
  root: "artifact YAML root must be a mapping",
  value_domain: "artifact contains a non-portable YAML value",
};
const ARTIFACT_INPUT_MESSAGES: Record<ArtifactInputReason, string> = {
  not_found: "artifact path does not exist",
  unreadable: "artifact path cannot be read",
  directory_requires_recursive: "artifact directory requires --recursive",
};

/**
 * Raised when YAML fails to parse. Mirrors the Python `YAMLError`/`FmFormatError`
 * branch so a malformed document becomes a `parse_error` validation result (exit 1)
 * instead of an uncaught exception.
 */
export class YamlParseError extends Error {
  readonly line: number | null;
  readonly column: number | null;

  constructor(
    message: string,
    options: ErrorOptions & { line?: number | null; column?: number | null } = {},
  ) {
    super(message, options);
    this.line = options.line ?? null;
    this.column = options.column ?? null;
  }
}

/** A leading frontmatter fence has no closing delimiter. */
export class ArtifactFrontmatterError extends YamlParseError {}

/** A readable artifact parsed successfully but its YAML root is not a mapping. */
export class ArtifactRootError extends YamlParseError {}

/** An explicit artifact operand is a directory without recursive validation. */
export class ArtifactDirectoryError extends Error {}

function decodeUtf8(encoded: Uint8Array): string {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(encoded);
  } catch (error) {
    throw new YamlParseError("invalid UTF-8 input", { cause: error });
  }
}

function parseYaml(
  text: string,
  validationLimits: ValidationLimitOverrides = {},
  encodedSize?: number,
): unknown {
  try {
    return parsePortableYaml(text, validationLimits, { encodedSize });
  } catch (err) {
    if (err instanceof PortableYamlSyntaxError) {
      throw new YamlParseError(err.message, {
        cause: err,
        line: err.line,
        column: err.column,
      });
    }
    throw err;
  }
}

/**
 * Read the YAML inside a document's leading `---` frontmatter fence. Returns
 * `hasFence: false` with a null value when there is no fence or the fence is empty (the
 * caller then treats the file as pure YAML). Throws `YamlParseError` on an unterminated
 * fence or non-mapping frontmatter, byte-matching the Python `frontmatter_format` errors.
 */
function readFrontmatter(
  path: string,
  validationLimits: ValidationLimitOverrides = {},
): RawFrontmatter {
  if (statSync(path).isDirectory()) throw new ArtifactDirectoryError();
  const limits = resolveValidationLimits(validationLimits);
  const encoded = readFileSync(path);
  if (encoded.byteLength > limits.maxResourceBytes) {
    throw new PortableValueError("maximum resource size exceeded");
  }
  const text = decodeUtf8(encoded);
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== "---") return { hasFence: false, value: null };
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i]?.trim() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) {
    // Unterminated fence: Python's frontmatter_format raises FmFormatError.
    throw new ArtifactFrontmatterError(
      `Delimiter \`---\` for end of frontmatter not found: \`${path}\``,
    );
  }
  // Empty frontmatter (end-fence at line 1, zero content lines between fences):
  // Python's fmf_read returns metadata=None → no_frontmatter.
  if (end === 1) return { hasFence: false, value: null };
  const parsed = parsePortableYaml(lines.slice(1, end).join("\n"), validationLimits, {
    encodedSize: encoded.byteLength,
    lineOffset: 1,
  });
  if (!isMapping(parsed)) {
    // frontmatter-format's fmf_read rejects non-mapping frontmatter: a whitespace-only
    // block (YAML `null`), a list, or a bare scalar. Match its message and Python class
    // names (`NoneType`, `list`, `str`, …) so the parse error is byte-identical to the
    // Python CLI across every entrypoint (ss-eero / ss-7cbb).
    throw new ArtifactRootError(
      `Expected YAML metadata to be a dict, got <class '${pyTypeName(parsed)}'>: \`${path}\``,
    );
  }
  return { hasFence: true, value: parsed };
}

function resolveSchemaPath(schemaPath: string, docPath: string): string | null {
  if (existsSync(schemaPath)) return schemaPath;
  for (const base of [dirname(docPath), process.cwd()]) {
    const candidate = join(base, schemaPath);
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

function structuralError(kind: string, message: string, extra: Record<string, unknown> = {}) {
  return { kind, message, ...extra };
}

function warning(code: SchemaWarning["code"], message: string): SchemaWarning {
  return { code, message, severity: "warning" };
}

function createSchemaAjv() {
  const ajv = new Ajv2020({
    allErrors: true,
    logger: false,
    strict: false,
    validateFormats: false,
    verbose: true,
  });
  return ajv;
}

function structuralFailure(error: SchemaInvalidErrorRecord): StructuralResult {
  return {
    ok: false,
    errors: [error],
    engine: "json_schema",
    skipped_reason: null,
  };
}

function schemaFailure(
  reason: SchemaInvalidReason,
  schemaPath: string,
  details: Omit<
    Partial<SchemaInvalidErrorRecord>,
    "kind" | "reason" | "message" | "schema_path"
  > = {},
): StructuralResult {
  return structuralFailure(schemaInvalidError(reason, schemaPath, details));
}

function schemaPreflight(
  schema: SchemaResource,
  allowBoolean: boolean,
  legacyCompatible: boolean,
): { error: SchemaInvalidErrorRecord | null; legacyIdentity: boolean } {
  if (typeof schema === "boolean") {
    return allowBoolean
      ? { error: null, legacyIdentity: false }
      : { error: schemaInvalidError("root", ""), legacyIdentity: false };
  }

  const dialect = schema.$schema;
  if (typeof dialect === "string" && dialect !== JSON_SCHEMA_DRAFT_2020_12) {
    return {
      error: schemaInvalidError("dialect", "/$schema", { dialect }),
      legacyIdentity: false,
    };
  }

  const cyclePath = firstCyclePath(schema);
  if (cyclePath !== null) {
    return {
      error: schemaInvalidError("compile", cyclePath),
      legacyIdentity: false,
    };
  }

  const invalidPattern = firstUnsupportedPattern(schema);
  if (invalidPattern !== null) {
    return {
      error: schemaInvalidError("pattern", jsonPointer(invalidPattern.path), {
        pattern: invalidPattern.pattern,
      }),
      legacyIdentity: false,
    };
  }

  const ajv = createSchemaAjv();
  let valid: boolean;
  try {
    valid = ajv.validateSchema(schema) as boolean;
  } catch {
    return {
      error: schemaInvalidError("metaschema", "/$schema"),
      legacyIdentity: false,
    };
  }
  if (!valid) {
    const first = [...(ajv.errors ?? [])].sort((left, right) => {
      if (left.instancePath < right.instancePath) return -1;
      if (left.instancePath > right.instancePath) return 1;
      if (left.keyword < right.keyword) return -1;
      if (left.keyword > right.keyword) return 1;
      return 0;
    })[0];
    return {
      error: schemaInvalidError("metaschema", first?.instancePath ?? ""),
      legacyIdentity: false,
    };
  }

  if (legacyCompatible) {
    const legacy = legacyIdentity(schema);
    if (legacy.error !== null) return { error: legacy.error, legacyIdentity: false };
    if (legacy.matches) return { error: null, legacyIdentity: true };
  }
  if (typeof schema.$id === "string") {
    try {
      validateSchemaId(schema.$id);
    } catch {
      return {
        error: schemaInvalidError("identity", "/$id", { detail: "invalid_root_id" }),
        legacyIdentity: false,
      };
    }
  }
  return { error: null, legacyIdentity: false };
}

function firstCyclePath(
  value: unknown,
  path: readonly (string | number)[] = [],
  active: Set<object> = new Set(),
  complete: Set<object> = new Set(),
): string | null {
  if (!isMapping(value) && !Array.isArray(value)) return null;
  if (active.has(value)) return jsonPointer(path);
  if (complete.has(value)) return null;

  active.add(value);
  const entries: [string | number, unknown][] = Array.isArray(value)
    ? [...value.entries()]
    : Object.keys(value)
        .sort()
        .map((key) => [key, value[key]]);
  for (const [key, item] of entries) {
    const cyclePath = firstCyclePath(item, [...path, key], active, complete);
    if (cyclePath !== null) return cyclePath;
  }
  active.delete(value);
  complete.add(value);
  return null;
}

function legacyIdentity(schema: Record<string, unknown>): {
  matches: boolean;
  error: SchemaInvalidErrorRecord | null;
} {
  const schemaId = schema.$id;
  const metadata = schema["x-softschema"];
  const contractId = isMapping(metadata) ? metadata.contract : undefined;
  if (
    typeof schemaId !== "string" ||
    typeof contractId !== "string" ||
    !isContractId(schemaId) ||
    !isContractId(contractId)
  ) {
    return { matches: false, error: null };
  }
  if (schemaId !== contractId) {
    return {
      matches: false,
      error: schemaInvalidError("profile", "/$id", {
        detail: "legacy_contract_id_mismatch",
      }),
    };
  }
  return { matches: true, error: null };
}

function isContractId(value: string): boolean {
  try {
    parseSchemaMetadata(value);
  } catch (error) {
    if (error instanceof SchemaMetadataError) return false;
    throw error;
  }
  return true;
}

interface SchemaReference {
  reference: string;
  schemaPath: string;
  source: SchemaResource;
  baseUri: string | null;
  origin: string;
  legacyRoot: boolean;
}

interface SchemaBundleIndex {
  resources: Record<string, SchemaResource>;
  references: SchemaReference[];
  resourceCount: number;
}

const SINGLE_SCHEMA_KEYWORDS = new Set([
  "additionalProperties",
  "contains",
  "contentSchema",
  "else",
  "if",
  "items",
  "not",
  "propertyNames",
  "then",
  "unevaluatedItems",
  "unevaluatedProperties",
]);
const ARRAY_SCHEMA_KEYWORDS = new Set(["allOf", "anyOf", "oneOf", "prefixItems"]);
const MAPPING_SCHEMA_KEYWORDS = new Set([
  "$defs",
  "dependentSchemas",
  "patternProperties",
  "properties",
]);
const ALL_SCHEMA_KEYWORDS = [
  ...SINGLE_SCHEMA_KEYWORDS,
  ...ARRAY_SCHEMA_KEYWORDS,
  ...MAPPING_SCHEMA_KEYWORDS,
].sort();

interface SchemaChild {
  path: readonly (string | number)[];
  schema: SchemaResource;
}

function compareUnicode(left: string, right: string): number {
  const leftPoints = [...left].map((value) => value.codePointAt(0) as number);
  const rightPoints = [...right].map((value) => value.codePointAt(0) as number);
  const length = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < length; index += 1) {
    const difference = (leftPoints[index] as number) - (rightPoints[index] as number);
    if (difference !== 0) return difference;
  }
  return leftPoints.length - rightPoints.length;
}

function schemaChildren(
  schema: Record<string, unknown>,
  path: readonly (string | number)[],
): SchemaChild[] {
  const children: SchemaChild[] = [];
  for (const keyword of ALL_SCHEMA_KEYWORDS) {
    const value = schema[keyword];
    if (SINGLE_SCHEMA_KEYWORDS.has(keyword)) {
      if (isSchemaResource(value)) children.push({ path: [...path, keyword], schema: value });
    } else if (ARRAY_SCHEMA_KEYWORDS.has(keyword)) {
      if (Array.isArray(value)) {
        for (const [index, item] of value.entries()) {
          if (isSchemaResource(item)) {
            children.push({ path: [...path, keyword, index], schema: item });
          }
        }
      }
    } else if (isMapping(value)) {
      for (const name of Object.keys(value).sort(compareUnicode)) {
        const item = value[name];
        if (isSchemaResource(item)) {
          children.push({ path: [...path, keyword, name], schema: item });
        }
      }
    }
  }
  return children;
}

const RELATIVE_SCHEMA_PATH_RE = /^[A-Za-z0-9._~!$&'()*+,;=:@/%-]*$/;
const RELATIVE_SCHEMA_QUERY_RE = /^[A-Za-z0-9._~!$&'()*+,;=:@/?%-]*$/;
const URI_UNRESERVED_RE = /^[A-Za-z0-9._~-]$/;

function hasCanonicalRelativeSchemaIdSpelling(schemaId: string): boolean {
  const hash = schemaId.indexOf("#");
  if (hash !== -1 && schemaId.slice(hash + 1).length > 0) return false;
  const resourceReference = hash === -1 ? schemaId : schemaId.slice(0, hash);
  const queryStart = resourceReference.indexOf("?");
  let path = queryStart === -1 ? resourceReference : resourceReference.slice(0, queryStart);
  const query = queryStart === -1 ? "" : resourceReference.slice(queryStart + 1);
  if (path.startsWith("//")) {
    const authorityEnd = path.indexOf("/", 2);
    if (authorityEnd === -1) return false;
    const authority = path.slice(2, authorityEnd);
    try {
      validateSchemaId(`https://${authority}/`);
    } catch {
      return false;
    }
    path = path.slice(authorityEnd);
  }
  if (!RELATIVE_SCHEMA_PATH_RE.test(path) || !RELATIVE_SCHEMA_QUERY_RE.test(query)) return false;
  for (let index = 0; index < resourceReference.length; index += 1) {
    if (resourceReference[index] !== "%") continue;
    const digits = resourceReference.slice(index + 1, index + 3);
    if (!/^[0-9A-F]{2}$/.test(digits)) return false;
    if (URI_UNRESERVED_RE.test(String.fromCharCode(Number.parseInt(digits, 16)))) return false;
    index += 2;
  }
  return true;
}

function resolveNestedSchemaId(schemaId: string, baseUri: string | null): string | null {
  let resolved: string;
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(schemaId)) {
    resolved = schemaId;
  } else if (baseUri !== null && hasCanonicalRelativeSchemaIdSpelling(schemaId)) {
    try {
      resolved = new URL(schemaId, baseUri).href;
    } catch {
      return null;
    }
  } else {
    return null;
  }
  const hash = resolved.indexOf("#");
  if (hash !== -1 && resolved.slice(hash + 1).length > 0) return null;
  const resourceUri = hash === -1 ? resolved : resolved.slice(0, hash);
  try {
    return validateSchemaId(resourceUri);
  } catch {
    return null;
  }
}

interface WalkSchemaOptions {
  path: readonly (string | number)[];
  baseUri: string | null;
  source: SchemaResource;
  origin: string;
  resourceIndex: Record<string, SchemaResource>;
  references: SchemaReference[];
  resourceRoot: boolean;
  legacyRoot: boolean;
}

function walkSchemaResources(
  schema: SchemaResource,
  options: WalkSchemaOptions,
): SchemaInvalidErrorRecord | null {
  if (!isMapping(schema)) return null;
  let currentBase = options.baseUri;
  let currentSource = options.source;

  if (!options.resourceRoot && !options.legacyRoot && Object.hasOwn(schema, "$id")) {
    const resolvedId =
      typeof schema.$id === "string" ? resolveNestedSchemaId(schema.$id, currentBase) : null;
    if (resolvedId === null) {
      return schemaInvalidError("identity", jsonPointer([...options.path, "$id"]), {
        detail: "invalid_nested_id",
      });
    }
    if (Object.hasOwn(options.resourceIndex, resolvedId)) {
      return schemaInvalidError("identity", jsonPointer([...options.path, "$id"]), {
        detail: "nested_resource_collision",
      });
    }
    options.resourceIndex[resolvedId] = schema;
    currentBase = resolvedId;
    currentSource = schema;
  }

  for (const key of ["$dynamicRef", "$ref"] as const) {
    const reference = schema[key];
    if (typeof reference === "string") {
      options.references.push({
        reference,
        schemaPath: jsonPointer([...options.path, key]),
        source: currentSource,
        baseUri: currentBase,
        origin: options.origin,
        legacyRoot: options.legacyRoot,
      });
    }
  }

  for (const child of schemaChildren(schema, options.path)) {
    const error = walkSchemaResources(child.schema, {
      ...options,
      path: child.path,
      baseUri: currentBase,
      source: currentSource,
      resourceRoot: false,
    });
    if (error !== null) return error;
  }
  return null;
}

function buildSchemaBundleIndex(
  schema: Record<string, unknown>,
  resources: Record<string, SchemaResource>,
  legacyIdentity: boolean,
): { bundle: SchemaBundleIndex | null; error: SchemaInvalidErrorRecord | null } {
  const resourceIndex: Record<string, SchemaResource> = { ...resources };
  const rootId = schema.$id;
  let rootBase: string | null = null;
  if (!legacyIdentity && typeof rootId === "string") {
    if (Object.hasOwn(resourceIndex, rootId)) {
      return {
        bundle: null,
        error: schemaInvalidError("identity", "/$id", { detail: "root_resource_collision" }),
      };
    }
    resourceIndex[rootId] = schema;
    rootBase = rootId;
  }

  const references: SchemaReference[] = [];
  let error = walkSchemaResources(schema, {
    path: [],
    baseUri: rootBase,
    source: schema,
    origin: "",
    resourceIndex,
    references,
    resourceRoot: true,
    legacyRoot: legacyIdentity,
  });
  if (error !== null) return { bundle: null, error };

  for (const uri of Object.keys(resources).sort(compareUnicode)) {
    const resource = resources[uri] as SchemaResource;
    error = walkSchemaResources(resource, {
      path: [],
      baseUri: uri,
      source: resource,
      origin: uri,
      resourceIndex,
      references,
      resourceRoot: true,
      legacyRoot: false,
    });
    if (error !== null) return { bundle: null, error };
  }

  references.sort(
    (left, right) =>
      compareUnicode(left.origin, right.origin) ||
      compareUnicode(left.schemaPath, right.schemaPath) ||
      compareUnicode(left.reference, right.reference),
  );
  const legacyExternal = references.find(
    (reference) => reference.legacyRoot && !reference.reference.startsWith("#"),
  );
  if (legacyExternal !== undefined) {
    return {
      bundle: null,
      error: schemaInvalidError("profile", legacyExternal.schemaPath, {
        detail: "legacy_external_reference",
      }),
    };
  }
  const resourceCount = Object.keys(resourceIndex).length + (rootBase === null ? 1 : 0);
  return { bundle: { resources: resourceIndex, references, resourceCount }, error: null };
}

function firstUnavailableReference(bundle: SchemaBundleIndex): SchemaReference | null {
  for (const candidate of bundle.references) {
    if (!referenceIsAvailable(candidate, bundle.resources)) {
      return candidate;
    }
  }
  return null;
}

function referenceIsAvailable(candidate: SchemaReference, resources: SchemaResources): boolean {
  const { reference } = candidate;
  if (reference.startsWith("#")) return fragmentExists(candidate.source, reference.slice(1));
  const hash = reference.indexOf("#");
  const resourceUri = hash === -1 ? reference : reference.slice(0, hash);
  const fragment = hash === -1 ? "" : reference.slice(hash + 1);
  if (resourceUri === "") return fragmentExists(candidate.source, fragment);
  const resolvedUri = resolveReferenceUri(resourceUri, candidate.baseUri);
  if (resolvedUri === null || !Object.hasOwn(resources, resolvedUri)) return false;
  return fragmentExists(resources[resolvedUri] as SchemaResource, fragment);
}

function resolveReferenceUri(reference: string, baseUri: string | null): string | null {
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(reference)) return reference;
  if (baseUri === null) return null;
  try {
    return new URL(reference, baseUri).href;
  } catch {
    return null;
  }
}

function fragmentExists(resource: SchemaResource, encodedFragment: string): boolean {
  let fragment: string;
  try {
    fragment = decodeURIComponent(encodedFragment);
  } catch {
    return false;
  }
  if (fragment === "") return true;
  if (fragment.startsWith("/")) {
    let current: unknown = resource;
    for (const encodedToken of fragment.slice(1).split("/")) {
      const token = encodedToken.replace(/~1/g, "/").replace(/~0/g, "~");
      if (isMapping(current) && Object.hasOwn(current, token)) {
        current = current[token];
      } else if (Array.isArray(current) && /^\d+$/.test(token) && Number(token) < current.length) {
        current = current[Number(token)];
      } else {
        return false;
      }
    }
    return true;
  }
  return hasAnchor(resource, fragment);
}

function hasAnchor(value: unknown, anchor: string, resourceRoot = true): boolean {
  if (!isMapping(value)) return false;
  if (!resourceRoot && Object.hasOwn(value, "$id")) return false;
  if (value.$anchor === anchor || value.$dynamicAnchor === anchor) return true;
  return schemaChildren(value, []).some((child) => hasAnchor(child.schema, anchor, false));
}

function isSchemaResource(value: unknown): value is SchemaResource {
  return typeof value === "boolean" || isMapping(value);
}

function referenceFromError(error: unknown): string | null {
  if (typeof error !== "object" || error === null) return null;
  const record = error as Record<string, unknown>;
  if (typeof record.missingRef === "string") return record.missingRef;
  return referenceFromError(record.cause);
}

function findReference(candidates: SchemaReference[], reference: string): SchemaReference | null {
  return (
    candidates.find((candidate) => {
      const hash = candidate.reference.indexOf("#");
      const resourceUri = hash === -1 ? candidate.reference : candidate.reference.slice(0, hash);
      const resolved = resolveReferenceUri(resourceUri, candidate.baseUri);
      const referenceHash = reference.indexOf("#");
      const reportedUri = referenceHash === -1 ? reference : reference.slice(0, referenceHash);
      return candidate.reference === reference || resolved === reportedUri;
    }) ?? (candidates.length === 1 ? (candidates[0] as SchemaReference) : null)
  );
}

function jsonPointer(path: readonly (string | number)[]): string {
  return path.map((part) => `/${String(part).replace(/~/g, "~0").replace(/\//g, "~1")}`).join("");
}

/**
 * Validate values against a compiled schema. `resources` contains only already-loaded
 * mapping or boolean schemas; validation never retrieves an external resource.
 */
interface StructuralValidationOptions {
  strictExtras?: boolean;
  resources?: SchemaResources;
  validationLimits?: ValidationLimitOverrides;
}

export function validateStructural(
  values: unknown,
  schemaObject: unknown,
  options: StructuralValidationOptions = {},
): StructuralResult {
  return validateStructuralCore(values, schemaObject, options, undefined);
}

function validateStructuralCore(
  values: unknown,
  schemaObject: unknown,
  options: StructuralValidationOptions,
  encodedSchemaSize: number | undefined,
): StructuralResult {
  const limits = resolveValidationLimits(options.validationLimits);
  let portableSchema: unknown;
  let bundleSize: number;
  try {
    const normalized = normalizePortableValue(schemaObject, limits, encodedSchemaSize);
    portableSchema = normalized.value;
    bundleSize = normalized.sizeBytes;
  } catch (error) {
    if (!(error instanceof PortableValueError)) throw error;
    return schemaFailure("value_domain", error.path);
  }
  if (!isMapping(portableSchema)) return schemaFailure("root", "");

  const rootPreflight = schemaPreflight(portableSchema, false, true);
  if (rootPreflight.error !== null) return structuralFailure(rootPreflight.error);

  const rawResources = options.resources ?? {};
  if (1 + Object.keys(rawResources).length > limits.maxResources) {
    return schemaFailure("value_domain", "");
  }
  if (bundleSize > limits.maxBundleBytes) return schemaFailure("value_domain", "");
  const resources: Record<string, SchemaResource> = {};
  for (const uri of Object.keys(rawResources).sort()) {
    try {
      validateSchemaId(uri);
    } catch {
      return schemaFailure("identity", "", { detail: "invalid_registry_key" });
    }
    let resource: unknown;
    let resourceSize: number;
    try {
      const normalized = normalizePortableValue(rawResources[uri], limits);
      resource = normalized.value;
      resourceSize = normalized.sizeBytes;
    } catch (error) {
      if (!(error instanceof PortableValueError)) throw error;
      return schemaFailure("value_domain", error.path);
    }
    if (!isSchemaResource(resource)) return schemaFailure("root", "");
    bundleSize += resourceSize;
    if (bundleSize > limits.maxBundleBytes) return schemaFailure("value_domain", "");
    const resourcePreflight = schemaPreflight(resource, true, false);
    if (resourcePreflight.error !== null) return structuralFailure(resourcePreflight.error);
    if (isMapping(resource) && "$id" in resource && resource.$id !== uri) {
      return schemaFailure("identity", "/$id", { detail: "resource_id_mismatch" });
    }
    resources[uri] = resource;
  }

  const indexed = buildSchemaBundleIndex(portableSchema, resources, rootPreflight.legacyIdentity);
  if (indexed.error !== null) return structuralFailure(indexed.error);
  if (indexed.bundle === null) throw new Error("schema bundle index is missing after preflight");
  const bundle = indexed.bundle;
  if (bundle.resourceCount > limits.maxResources) return schemaFailure("value_domain", "");

  const unavailable = firstUnavailableReference(bundle);
  if (unavailable !== null) {
    return schemaFailure("reference", unavailable.schemaPath, {
      reference: unavailable.reference,
    });
  }

  let schema: Record<string, unknown>;
  try {
    schema = options.strictExtras ? applyEnforcedExtras(portableSchema) : { ...portableSchema };
  } catch (error) {
    if (!(error instanceof EnforcementUnsupportedError)) throw error;
    return {
      ok: false,
      errors: [
        {
          kind: "enforcement_unsupported",
          message: ENFORCEMENT_UNSUPPORTED_MESSAGE,
          schema_path: error.schemaPath,
        },
      ],
      engine: "json_schema",
      skipped_reason: null,
    };
  }
  if (rootPreflight.legacyIdentity) {
    schema = { ...schema };
    delete schema.$id;
  }
  const preparedResources = { ...resources };

  const ajv = createSchemaAjv();
  let validateFn: ValidateFunction;
  try {
    for (const uri of Object.keys(preparedResources).sort()) {
      ajv.addSchema(preparedResources[uri] as object | boolean, uri);
    }
    validateFn = ajv.compile(schema);
  } catch (error) {
    const reference = referenceFromError(error);
    if (reference !== null) {
      const located = findReference(bundle.references, reference);
      return schemaFailure("reference", located?.schemaPath ?? "", {
        reference: located?.reference ?? reference,
      });
    }
    return schemaFailure("compile", "");
  }

  let ok: boolean;
  try {
    ok = validateFn(values) as boolean;
  } catch (error) {
    const reference = referenceFromError(error);
    if (reference !== null) {
      const located = findReference(bundle.references, reference);
      return schemaFailure("reference", located?.schemaPath ?? "", {
        reference: located?.reference ?? reference,
      });
    }
    return schemaFailure("compile", "");
  }
  const errors: StructuralErrorRecord[] = ok
    ? []
    : collapseAdditionalProperties((validateFn.errors ?? []).map((e) => normalizeAjvError(e)));
  errors.sort(compareStructuralRecords);
  return { ok: errors.length === 0, errors, engine: "json_schema", skipped_reason: null };
}

/**
 * Semantic validation via Zod `safeParse`: the idiomatic mirror of the Python Pydantic
 * layer. Errors are implementation-specific (Zod issues) and are not part of the
 * cross-language byte contract; only pass/fail and the field path are portable.
 */
export function validateSemantic(values: unknown, model: z.ZodType): SemanticResult {
  const result = model.safeParse(values);
  if (result.success) return { ok: true, errors: [], skipped_reason: null };
  const errors = result.error.issues.map((issue) => ({
    code: issue.code,
    path: issue.path,
    message: issue.message,
  }));
  return { ok: false, errors, skipped_reason: null };
}

/**
 * Validate a pre-extracted values mapping against a model, a schema, or both: the
 * idiomatic mirror of Python `validate_values`. `resources` has the same already-loaded,
 * no-retrieval semantics as `validateStructural`. Throws if neither layer is supplied.
 */
export function validateValues(
  values: unknown,
  options: {
    model?: z.ZodType;
    schema?: unknown;
    resources?: SchemaResources;
    validationLimits?: ValidationLimitOverrides;
  } = {},
): ValidationResult {
  if (options.model === undefined && options.schema === undefined) {
    throw new Error("validateValues() requires at least one of model or schema");
  }
  const structural =
    options.schema !== undefined
      ? validateStructural(values, options.schema, {
          resources: options.resources,
          validationLimits: options.validationLimits,
        })
      : { ok: true, errors: [], engine: "json_schema", skipped_reason: null };
  const semantic = options.model
    ? validateSemantic(values, options.model)
    : { ok: true, errors: [], skipped_reason: null };
  return { structural, semantic };
}

function buildResult(args: {
  docPath: string;
  contract: Contract;
  metadata: SchemaMetadata | null;
  values: Record<string, unknown> | null;
  structural: StructuralResult;
  semantic: SemanticResult;
  warnings: SchemaWarning[];
}): ArtifactValidationResult {
  const { contract, structural, semantic } = args;
  return {
    ok: structural.ok && semantic.ok,
    output: {
      contract: contractToOutput(contract),
      contract_id: contract.id,
      document_metadata: metadataToOutput(args.metadata),
      path: args.docPath,
      profile: contract.profile,
      semantic,
      status: contract.status,
      structural,
      values: args.values,
      warnings: args.warnings,
    },
  };
}

function failure(
  docPath: string,
  contract: Contract,
  metadata: SchemaMetadata | null,
  kind: string,
  message: string,
  warnings: SchemaWarning[] = [],
  extra: Record<string, unknown> = {},
): ArtifactValidationResult {
  return buildResult({
    docPath,
    contract,
    metadata,
    values: null,
    structural: {
      ok: false,
      errors: [structuralError(kind, message, extra)],
      engine: "json_schema",
      skipped_reason: null,
    },
    semantic: { ok: false, errors: [], skipped_reason: kind },
    warnings,
  });
}

function artifactValueDomainFailure(
  docPath: string,
  contract: Contract,
  error: PortableValueError,
): ArtifactValidationResult {
  return failureFromArtifactRecord(
    docPath,
    contract,
    artifactParseErrorRecord(docPath, "value_domain", { path: error.path }),
  );
}

/** Build a stable discriminated record for a readable artifact parse failure. */
export function artifactParseErrorRecord(
  source: string,
  reason: ArtifactParseReason,
  options: {
    path?: string;
    line?: number | null;
    column?: number | null;
    includeLocation?: boolean;
  } = {},
): Record<string, unknown> {
  const record: Record<string, unknown> = {
    kind: "parse_error",
    reason,
    message: ARTIFACT_PARSE_MESSAGES[reason],
    source,
  };
  if (reason === "value_domain") record.path = options.path ?? "";
  else if (options.path !== undefined) record.path = options.path;
  if (options.includeLocation === true) {
    if (options.line !== undefined && options.line !== null) record.line = options.line;
    if (options.column !== undefined && options.column !== null) record.column = options.column;
  }
  return record;
}

/** Build a stable discriminated record for an artifact access failure. */
export function artifactInputErrorRecord(
  source: string,
  reason: ArtifactInputReason,
): Record<string, unknown> {
  return { kind: "input_error", reason, message: ARTIFACT_INPUT_MESSAGES[reason], source };
}

/** Normalize a parser/filesystem exception without exposing runtime-specific prose. */
export function artifactErrorRecord(
  source: string,
  error: unknown,
  options: { includeLocation?: boolean } = {},
): Record<string, unknown> | null {
  if (error instanceof PortableValueError) {
    return artifactParseErrorRecord(source, "value_domain", {
      path: error.path,
      line: error.line,
      column: error.column,
      includeLocation: options.includeLocation,
    });
  }
  if (error instanceof ArtifactFrontmatterError) {
    return artifactParseErrorRecord(source, "frontmatter");
  }
  if (error instanceof ArtifactRootError) return artifactParseErrorRecord(source, "root");
  if (error instanceof ArtifactDirectoryError) {
    return artifactInputErrorRecord(source, "directory_requires_recursive");
  }
  if (error instanceof PortableYamlSyntaxError) {
    return artifactParseErrorRecord(source, "syntax", {
      line: error.line,
      column: error.column,
      includeLocation: options.includeLocation,
    });
  }
  if (error instanceof YamlParseError) {
    return artifactParseErrorRecord(source, "syntax", {
      line: error.line,
      column: error.column,
      includeLocation: options.includeLocation,
    });
  }
  if (error instanceof Error && "code" in error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "EISDIR") return artifactInputErrorRecord(source, "directory_requires_recursive");
    if (code === "ENOENT" || code === "ENOTDIR") {
      return artifactInputErrorRecord(source, "not_found");
    }
    if (typeof code === "string") return artifactInputErrorRecord(source, "unreadable");
  }
  return null;
}

function failureFromArtifactRecord(
  docPath: string,
  contract: Contract,
  record: Record<string, unknown>,
): ArtifactValidationResult {
  const { kind, message, ...extra } = record;
  return failure(docPath, contract, null, String(kind), String(message), [], extra);
}

function artifactReadFailure(
  docPath: string,
  contract: Contract,
  error: unknown,
): ArtifactValidationResult | null {
  const record = artifactErrorRecord(docPath, error);
  return record === null ? null : failureFromArtifactRecord(docPath, contract, record);
}

/** Read one bounded pure-YAML artifact and require a mapping root. */
export function readPureYamlArtifact(
  path: string,
  validationLimits: ValidationLimitOverrides = {},
): Record<string, unknown> {
  if (statSync(path).isDirectory()) throw new ArtifactDirectoryError();
  const encoded = readFileSync(path);
  const raw = parseYaml(decodeUtf8(encoded), validationLimits, encoded.byteLength);
  if (!isMapping(raw)) {
    throw new ArtifactRootError(`YAML root is ${pyTypeName(raw)}, expected mapping`);
  }
  return raw;
}

/** Load a resolved compiled-schema file and run structural validation against it. */
function structuralAgainstSchemaFile(
  resolved: string,
  values: unknown,
  strictExtras: boolean,
  validationLimits: ValidationLimitOverrides,
): StructuralResult {
  let compiledSchema: unknown;
  let encodedSchemaSize = 0;
  try {
    const encoded = readFileSync(resolved);
    encodedSchemaSize = encoded.byteLength;
    const text = decodeUtf8(encoded);
    compiledSchema = parseYaml(text, validationLimits, encoded.byteLength);
  } catch (err) {
    if (err instanceof PortableValueError) {
      return schemaFailure("value_domain", err.path);
    }
    if (err instanceof YamlParseError) {
      return schemaFailure("syntax", "");
    }
    if (err instanceof Error && "code" in err) {
      return schemaFailure("syntax", "");
    }
    throw err;
  }
  return validateStructuralCore(
    values,
    compiledSchema,
    { strictExtras, validationLimits },
    encodedSchemaSize,
  );
}

/** Is `child` inside `base` after normalization? */
function isContained(base: string, child: string): boolean {
  const rel = relative(base, child);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

/**
 * Resolve a document-declared `softschema.schema` value, strictly bounded.
 * Stricter than `resolveSchemaPath` because the value comes from the document,
 * not the caller: it must be relative, resolves from the document's directory,
 * and the normalized result must stay inside the document directory or the
 * working directory. Mirrors the Python `_resolve_metadata_schema`.
 */
function resolveMetadataSchema(
  schemaRef: string,
  docPath: string,
): { path: string | null; error: string | null } {
  if (isAbsolute(schemaRef)) {
    return { path: null, error: `softschema.schema must be a relative path: ${schemaRef}` };
  }
  const docDir = resolve(dirname(docPath));
  const resolved = resolve(docDir, schemaRef);
  const cwd = resolve(process.cwd());
  if (!isContained(docDir, resolved) && !isContained(cwd, resolved)) {
    return {
      path: null,
      error:
        "softschema.schema escapes the document directory and the working " +
        `directory: ${schemaRef}`,
    };
  }
  if (!existsSync(resolved) || !statSync(resolved).isFile()) {
    return { path: null, error: `compiled schema not found: ${schemaRef}` };
  }
  return { path: resolved, error: null };
}

function structuralForValues(
  contract: Contract,
  values: unknown,
  docPath: string,
  metadata: SchemaMetadata | null,
  validationLimits: ValidationLimitOverrides,
): StructuralResult {
  // Schema precedence (host over document): a caller/registry schemaPath, then
  // the document's own softschema.schema binding, then none.
  if (contract.schemaPath !== null) {
    const resolved = resolveSchemaPath(contract.schemaPath, docPath);
    if (resolved === null) {
      return {
        ok: false,
        errors: [
          structuralError("schema_missing", `compiled schema not found: ${contract.schemaPath}`, {
            path: contract.schemaPath,
          }),
        ],
        engine: "json_schema",
        skipped_reason: null,
      };
    }
    return structuralAgainstSchemaFile(
      resolved,
      values,
      contract.status === "enforced",
      validationLimits,
    );
  }
  const metadataSchema = metadata?.schema ?? null;
  if (metadataSchema !== null) {
    const bound = resolveMetadataSchema(metadataSchema, docPath);
    if (bound.path === null) {
      return {
        ok: false,
        errors: [
          structuralError("schema_missing", bound.error ?? "", {
            path: metadataSchema,
          }),
        ],
        engine: "json_schema",
        skipped_reason: null,
      };
    }
    return structuralAgainstSchemaFile(
      bound.path,
      values,
      contract.status === "enforced",
      validationLimits,
    );
  }
  if (contract.model !== null) {
    return { ok: true, errors: [], engine: "json_schema", skipped_reason: "inferred_via_model" };
  }
  return { ok: true, errors: [], engine: "json_schema", skipped_reason: "no_schema" };
}

function validateExtracted(
  docPath: string,
  contract: Contract,
  values: Record<string, unknown>,
  metadata: SchemaMetadata | null,
  warnings: SchemaWarning[],
  semanticModel: z.ZodType | undefined,
  validationLimits: ValidationLimitOverrides,
): ArtifactValidationResult {
  const structural = structuralForValues(contract, values, docPath, metadata, validationLimits);
  const semantic: SemanticResult =
    semanticModel !== undefined
      ? validateSemantic(values, semanticModel)
      : { ok: true, errors: [], skipped_reason: "no_semantic_model" };
  return buildResult({ docPath, contract, metadata, values, structural, semantic, warnings });
}

/** Run the metadata checks shared by the frontmatter-md and pure-yaml paths. */
function checkMetadata(
  docPath: string,
  root: Record<string, unknown>,
  contract: Contract,
  warnings: SchemaWarning[],
  metadataMode: MetadataMode,
): { metadata: SchemaMetadata | null } | { failed: ArtifactValidationResult } {
  let metadata: SchemaMetadata | null;
  try {
    metadata = parseSchemaMetadata(root.softschema ?? null);
  } catch (err) {
    if (err instanceof SchemaMetadataError) {
      return {
        failed: failure(docPath, contract, null, "document_softschema_invalid", err.message),
      };
    }
    throw err;
  }
  if (metadata !== null && metadata.contractId !== contract.id) {
    const message = `document declares '${metadata.contractId}'; contract uses '${contract.id}'`;
    if (metadataMode === "advisory") {
      warnings.push(warning("document-contract-mismatch", message));
    } else {
      return {
        failed: failure(
          docPath,
          contract,
          metadata,
          "document_contract_mismatch",
          message,
          warnings,
        ),
      };
    }
  }
  if (metadata !== null && metadata.status !== null && metadata.status !== contract.status) {
    warnings.push(
      warning(
        "document-status-mismatch",
        `document declares status '${metadata.status}'; contract uses '${contract.status}'`,
      ),
    );
  }
  return { metadata };
}

/** Validate an artifact against a contract (frontmatter-md or pure-yaml). */
export function validateArtifact(
  docPath: string,
  contract: Contract,
  options: {
    semanticModel?: z.ZodType;
    metadataMode?: MetadataMode;
    validationLimits?: ValidationLimitOverrides;
    /**
     * An already-parsed frontmatter (from `readFrontmatter`); when supplied for a
     * frontmatter-md contract the document is not re-read. The CLI passes what it
     * parsed for binding inference so the file is read once.
     */
    preParsed?: RawFrontmatter;
    /** Already-parsed pure-YAML root; used by the CLI to avoid a second file read. */
    preParsedYaml?: unknown;
  } = {},
): ArtifactValidationResult {
  validateContractId(contract.id);
  const validationLimits = options.validationLimits ?? DEFAULT_VALIDATION_LIMITS;
  const warnings: SchemaWarning[] = [];
  const metadataMode = options.metadataMode ?? "enforced";
  if (contract.profile === "pure-yaml") {
    let raw: unknown;
    if (options.preParsedYaml !== undefined) {
      try {
        raw = normalizePortableValue(options.preParsedYaml, validationLimits).value;
      } catch (err) {
        const failed = artifactReadFailure(docPath, contract, err);
        if (failed !== null) return failed;
        throw err;
      }
    } else {
      try {
        raw = readPureYamlArtifact(docPath, validationLimits);
      } catch (err) {
        const failed = artifactReadFailure(docPath, contract, err);
        if (failed !== null) return failed;
        throw err;
      }
    }
    if (!isMapping(raw)) {
      return failureFromArtifactRecord(
        docPath,
        contract,
        artifactParseErrorRecord(docPath, "root"),
      );
    }
    // Same metadata rules as frontmatter: the softschema: block is recognized
    // (and checked), never validated as payload data. The envelope differs by
    // design: an explicit envelopeKey nests the payload; otherwise the
    // remaining root IS the payload (a pure-yaml file is "the whole document
    // is the structured payload", e.g. a companion data file).
    const checked = checkMetadata(docPath, raw, contract, warnings, metadataMode);
    if ("failed" in checked) return checked.failed;
    let values: unknown;
    // Envelope precedence (host over document): a registry/caller envelopeKey,
    // then the document's own softschema.envelope, then the whole root.
    const declaredEnvelope = contract.envelopeKey ?? checked.metadata?.envelope ?? null;
    if (declaredEnvelope !== null) {
      if (!(declaredEnvelope in raw)) {
        const actualKeys = Object.keys(raw).filter((key) => key !== "softschema");
        return failure(
          docPath,
          contract,
          checked.metadata,
          "envelope_mismatch",
          `contract '${contract.id}' expects '${declaredEnvelope}'`,
          warnings,
          { expected_key: declaredEnvelope, actual_keys: actualKeys },
        );
      }
      values = raw[declaredEnvelope];
    } else {
      values = Object.fromEntries(Object.entries(raw).filter(([k]) => k !== "softschema"));
    }
    if (!isMapping(values)) {
      return failure(
        docPath,
        contract,
        checked.metadata,
        "envelope_not_mapping",
        `envelope value is ${pyTypeName(values)}, expected mapping`,
        warnings,
      );
    }
    return validateExtracted(
      docPath,
      contract,
      values,
      checked.metadata,
      warnings,
      options.semanticModel,
      validationLimits,
    );
  }

  let parsed: RawFrontmatter;
  if (options.preParsed !== undefined) {
    try {
      parsed = {
        hasFence: options.preParsed.hasFence,
        value:
          options.preParsed.value === null
            ? null
            : normalizePortableValue(options.preParsed.value, validationLimits).value,
      };
    } catch (error) {
      if (!(error instanceof PortableValueError)) throw error;
      return artifactValueDomainFailure(docPath, contract, error);
    }
  } else {
    try {
      parsed = readFrontmatter(docPath, validationLimits);
    } catch (err) {
      const failed = artifactReadFailure(docPath, contract, err);
      if (failed !== null) return failed;
      throw err;
    }
  }
  const { hasFence, value: frontmatter } = parsed;
  if (!hasFence) {
    return failure(docPath, contract, null, "no_frontmatter", `no frontmatter in ${docPath}`);
  }
  if (!isMapping(frontmatter)) {
    return failureFromArtifactRecord(docPath, contract, artifactParseErrorRecord(docPath, "root"));
  }

  const checked = checkMetadata(docPath, frontmatter, contract, warnings, metadataMode);
  if ("failed" in checked) return checked.failed;
  const metadata = checked.metadata;

  let values: unknown;
  // Envelope precedence (host over document): a registry/caller envelopeKey,
  // then the document's own softschema.envelope, then single-key inference.
  const declaredEnvelope = contract.envelopeKey ?? metadata?.envelope ?? null;
  if (declaredEnvelope !== null) {
    if (!(declaredEnvelope in frontmatter)) {
      const actualKeys = Object.keys(frontmatter).filter((key) => key !== "softschema");
      return failure(
        docPath,
        contract,
        metadata,
        "envelope_mismatch",
        `contract '${contract.id}' expects '${declaredEnvelope}'`,
        warnings,
        { expected_key: declaredEnvelope, actual_keys: actualKeys },
      );
    }
    values = frontmatter[declaredEnvelope];
  } else {
    // The spec's envelope rules: exactly one non-softschema top-level key is
    // the envelope by convention; zero or several candidates are rejected.
    let envelopeKey: string | null;
    try {
      envelopeKey = inferEnvelopeKey(frontmatter);
    } catch (err) {
      if (err instanceof EnvelopeAmbiguityError) {
        return failure(docPath, contract, metadata, "envelope_ambiguous", err.message, warnings);
      }
      throw err;
    }
    if (envelopeKey === null) {
      return failure(
        docPath,
        contract,
        metadata,
        "envelope_missing",
        "document has no payload key beside softschema",
        warnings,
      );
    }
    values = frontmatter[envelopeKey];
  }

  if (!isMapping(values)) {
    return failure(
      docPath,
      contract,
      metadata,
      "envelope_not_mapping",
      `envelope value is ${pyTypeName(values)}, expected mapping`,
      warnings,
    );
  }

  return validateExtracted(
    docPath,
    contract,
    values,
    metadata,
    warnings,
    options.semanticModel,
    validationLimits,
  );
}

export { readFrontmatter };
