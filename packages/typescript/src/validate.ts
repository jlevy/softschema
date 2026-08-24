/**
 * Artifact validation: read Markdown frontmatter (or pure YAML), resolve the envelope,
 * and run structural validation against the compiled JSON Schema via ajv. The result
 * object has the same portable fields and meaning as the Python result.
 */
import { existsSync, realpathSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import type { ValidateFunction } from "ajv";
import Ajv2020 from "ajv/dist/2020.js";
import type { z } from "zod";
import {
  EnforcementUnsupportedError,
  prepareSchemaGraph,
  SchemaGraphError,
} from "./enforcement.js";
import {
  collapseUndeclaredProperties,
  compareStructuralRecords,
  dropConditionalWrappers,
  normalizeAjvError,
  type StructuralErrorRecord,
} from "./errors.js";
import { isMapping } from "./guards.js";
import {
  type Contract,
  checkContractId,
  contractToOutput,
  metadataToOutput,
  parseSchemaMetadata,
  pyTypeName,
  type SchemaMetadata,
  SchemaMetadataError,
  type SchemaStatus,
  type SchemaWarning,
} from "./models.js";
import { PortableInputError, parsePortableYaml, readUtf8 } from "./portable.js";

export interface StructuralResult {
  ok: boolean;
  errors: (StructuralErrorRecord | Record<string, unknown>)[];
  engine: string;
  skipped_reason: string | null;
}

export interface SemanticResult {
  ok: boolean;
  errors: Record<string, unknown>[];
  skipped_reason: string | null;
}

export interface ValidationResult {
  structural: StructuralResult;
  semantic: SemanticResult;
}

export interface ArtifactValidationResult {
  readonly ok: boolean;
  contract: Record<string, unknown>;
  contract_id: string;
  document_metadata: Record<string, unknown> | null;
  outcome: "valid" | "invalid" | "input_error";
  path: string;
  profile: string;
  semantic: SemanticResult;
  status: string;
  structural: StructuralResult;
  values: Record<string, unknown> | null;
  warnings: SchemaWarning[];
}

export type MetadataMode = "enforced" | "advisory";

/**
 * A document root already decoded by `readFrontmatterDoc` or `readYamlDoc`, ready to
 * hand to `validateArtifact` as `document` without the file being read a second time.
 */
export interface ParsedDocument {
  /**
   * Frontmatter-md only: false when the document has no fence, which validation reports
   * as `no_frontmatter`. Pure-yaml has no fence to speak of and ignores this.
   */
  hasFence: boolean;
  value: unknown;
}

/**
 * Raised when YAML fails to parse. Mirrors the Python `YAMLError`/`FmFormatError`
 * branch so a malformed document becomes a `parse_error` validation result (exit 1)
 * instead of an uncaught exception.
 */
export class YamlParseError extends Error {}

function parseYaml(text: string): unknown {
  try {
    return parsePortableYaml(text);
  } catch (err) {
    if (err instanceof PortableInputError) {
      throw new YamlParseError(err.message, { cause: err });
    }
    throw new YamlParseError((err as Error).message);
  }
}

/**
 * Read the YAML inside a document's leading `---` frontmatter fence. Returns
 * `hasFence: false` with a null value when there is no fence or the fence is empty (the
 * caller then treats the file as pure YAML). Throws `YamlParseError` on an unterminated
 * fence or non-mapping frontmatter with the portable error contract.
 *
 * This is the supported way to produce the `document` option of `validateArtifact` for a
 * frontmatter-md contract: decoding goes through the portable YAML rules, so validating
 * the result is equivalent to letting `validateArtifact` read the file itself.
 */
function readFrontmatterDoc(path: string): ParsedDocument {
  const text = readUtf8(path);
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trimEnd() !== "---") return { hasFence: false, value: null };
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i]?.trimEnd() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) {
    throw new YamlParseError(`Delimiter \`---\` for end of frontmatter not found: \`${path}\``);
  }
  // Empty frontmatter (end-fence at line 1) is the portable no_frontmatter case.
  if (end === 1) return { hasFence: false, value: null };
  const parsed = parseYaml(lines.slice(1, end).join("\n"));
  if (!isMapping(parsed)) {
    // Reject the same non-mapping values as Python: a whitespace-only block (YAML
    // `null`), a list, or a bare scalar. Use the portable type names from the shared
    // error contract.
    throw new YamlParseError(
      `Expected YAML metadata to be a dict, got ${pyTypeName(parsed)}: \`${path}\``,
    );
  }
  return { hasFence: true, value: parsed };
}

/**
 * Read a pure-yaml artifact into its parsed document root, the counterpart to
 * `readFrontmatterDoc` and the supported way to produce the `document` option of
 * `validateArtifact` for a pure-yaml contract. Decoding goes through the portable YAML
 * rules, which a host YAML library does not enforce; see `validateArtifact`.
 */
function readYamlDoc(path: string): ParsedDocument {
  return { hasFence: false, value: parsePortableYaml(readUtf8(path)) };
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

const VALIDATOR_CACHE_SIZE = 256;
const validatorCache = new Map<string, ValidateFunction>();

/**
 * Check a compiled schema, apply the `enforced` overlay, and compile it with Ajv.
 *
 * Throws propagate to `validateStructural`, which turns them into a `schema_invalid`
 * result, and only a schema that compiles is ever cached.
 */
function buildValidator(
  schemaObject: Record<string, unknown>,
  strictExtras: boolean,
  resources: Record<string, Record<string, unknown>>,
): ValidateFunction {
  const ajv = new Ajv2020({
    allErrors: true,
    strict: false,
    verbose: true,
    validateFormats: false,
  });
  for (const document of [schemaObject, ...Object.values(resources)]) {
    checkPatterns(document);
    if (!ajv.validateSchema(document)) {
      throw new SchemaGraphError("dialect", `schema is invalid: ${ajv.errorsText(ajv.errors)}`);
    }
  }
  if (!strictExtras) checkSchemaIdentities(schemaObject, resources);
  const prepared = strictExtras
    ? prepareSchemaGraph(schemaObject, resources)
    : { root: schemaObject, resources };
  for (const [key, resource] of Object.entries(prepared.resources)) {
    ajv.addSchema(resource, typeof resource.$id === "string" ? resource.$id : key);
  }
  return ajv.compile(prepared.root);
}

/**
 * Memoize `buildValidator` for the no-`resources` case, mirroring the Python
 * `_cached_validator`.
 *
 * A compiled schema is a build output, so checking it, applying the overlay, and
 * compiling it produce the same validator every time. Doing that work per call
 * dominated large suites, which is what the Python cache already fixed; without this
 * the two runtimes had the same schema and very different cost.
 *
 * Keyed on the schema's own content rather than on a file path and stat, so a rewritten
 * schema can never be served from a stale entry and two paths holding identical schemas
 * correctly share one. Before returning a checked-enforcement hit, the graph is prepared
 * again because shared in-memory object identity is not represented by JSON content.
 * Serializing to build the key is negligible against what a hit avoids.
 * Least-recently-used entries are evicted past `VALIDATOR_CACHE_SIZE`.
 */
function cachedValidator(
  schemaObject: Record<string, unknown>,
  strictExtras: boolean,
  resources: Record<string, Record<string, unknown>>,
): ValidateFunction {
  if (Object.keys(resources).length > 0) {
    // `resources` is a plain object of schemas, so it is neither cheap to fingerprint
    // nor the common path; build fresh rather than risk a wrong cache key. Same call
    // this made before the cache existed, and the same choice Python makes.
    return buildValidator(schemaObject, strictExtras, resources);
  }
  let serialized: string | undefined;
  try {
    serialized = JSON.stringify(schemaObject);
  } catch (error) {
    if (strictExtras) {
      prepareSchemaGraph(schemaObject);
    }
    throw error;
  }
  const key = `${strictExtras ? "1" : "0"}\u0000${serialized}`;
  const hit = validatorCache.get(key);
  if (hit !== undefined) {
    if (strictExtras) {
      prepareSchemaGraph(schemaObject);
    }
    // Re-insert to mark this entry most recently used; Map iterates in insertion order.
    validatorCache.delete(key);
    validatorCache.set(key, hit);
    return hit;
  }
  const built = buildValidator(schemaObject, strictExtras, resources);
  validatorCache.set(key, built);
  if (validatorCache.size > VALIDATOR_CACHE_SIZE) {
    const oldest = validatorCache.keys().next();
    if (!oldest.done) validatorCache.delete(oldest.value);
  }
  return built;
}

/**
 * Drop every memoized validator, the counterpart to Python's `clear_validator_cache`.
 *
 * Only needed by a long-lived process that regenerates compiled schemas in place, such
 * as a watch mode or a language server; ordinary callers never have to call it, because
 * a rewritten schema misses the cache on its own.
 */
export function clearValidatorCache(): void {
  validatorCache.clear();
}

export function validateStructural(
  values: unknown,
  schemaObject: Record<string, unknown>,
  options: { strictExtras?: boolean; resources?: Record<string, Record<string, unknown>> } = {},
): StructuralResult {
  try {
    const validateFn = cachedValidator(
      schemaObject,
      options.strictExtras ?? false,
      options.resources ?? {},
    );
    const ok = validateFn(values);
    const errors: StructuralErrorRecord[] = ok
      ? []
      : collapseUndeclaredProperties(
          dropConditionalWrappers(
            (validateFn.errors ?? []).map((error) => normalizeAjvError(error, values)),
          ),
        );
    errors.sort(compareStructuralRecords);
    return { ok: errors.length === 0, errors, engine: "json_schema", skipped_reason: null };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (error instanceof EnforcementUnsupportedError) {
      return {
        ok: false,
        errors: [
          {
            kind: "enforcement_unsupported",
            reason: error.reason,
            schema_path: error.schemaPath,
            message,
          },
        ],
        engine: "json_schema",
        skipped_reason: null,
      };
    }
    if (error instanceof SchemaGraphError) return schemaInvalid(error.reason, message);
    return schemaInvalid(schemaFailureReason(message), message);
  }
}

const SCHEMA_MAPS = new Set([
  "$defs",
  "definitions",
  "properties",
  "patternProperties",
  "dependentSchemas",
]);
const SCHEMA_LISTS = new Set(["allOf", "anyOf", "oneOf", "prefixItems"]);
const SCHEMA_SINGLES = new Set([
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
const MAX_PATTERN_LENGTH = 1_024;
const UNSUPPORTED_PATTERN_PARTS = ["(?<", "(?P", "\\A", "\\Z", "\\z", "\\p", "\\P"];

function* iterSchemas(root: Record<string, unknown>): Iterable<Record<string, unknown>> {
  const stack = [root];
  const seen = new Set<Record<string, unknown>>();
  while (stack.length > 0) {
    const schema = stack.pop() as Record<string, unknown>;
    if (seen.has(schema)) {
      continue;
    }
    seen.add(schema);
    yield schema;
    for (const [key, value] of Object.entries(schema)) {
      if (SCHEMA_MAPS.has(key) && isMapping(value)) {
        stack.push(...Object.values(value).filter(isMapping));
      } else if (SCHEMA_LISTS.has(key) && Array.isArray(value)) {
        stack.push(...value.filter(isMapping));
      } else if (SCHEMA_SINGLES.has(key) && isMapping(value)) {
        stack.push(value);
      }
    }
  }
}

function checkPatterns(schema: Record<string, unknown>): void {
  const check = (pattern: unknown): void => {
    if (typeof pattern !== "string" || pattern.length > MAX_PATTERN_LENGTH) {
      throw new Error("pattern must be a string of at most 1024 characters");
    }
    if (
      UNSUPPORTED_PATTERN_PARTS.some((part) => pattern.includes(part)) ||
      /\\[1-9]|\(\?[aiLmsux-]/u.test(pattern)
    ) {
      throw new Error("pattern uses syntax outside the portable subset");
    }
    try {
      new RegExp(pattern, "u");
    } catch (error) {
      throw new Error(`pattern is invalid: ${String(error)}`);
    }
  };

  for (const node of iterSchemas(schema)) {
    const pattern = node.pattern;
    if (pattern !== undefined) check(pattern);
    if (isMapping(node.patternProperties)) {
      for (const propertyPattern of Object.keys(node.patternProperties)) {
        check(propertyPattern);
      }
    }
  }
}

function checkSchemaIdentities(
  schema: Record<string, unknown>,
  resources: Record<string, Record<string, unknown>>,
): void {
  const seen = new Set<string>();
  for (const document of [schema, ...Object.values(resources)]) {
    for (const node of iterSchemas(document)) {
      if (typeof node.$id !== "string") continue;
      if (seen.has(node.$id)) throw new Error(`duplicate schema resource identity: ${node.$id}`);
      seen.add(node.$id);
    }
  }
}

function schemaFailureReason(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("reference") || lower.includes("resolve")) return "reference";
  if (lower.includes("pattern")) return "pattern";
  if (lower.includes("duplicate schema resource")) return "resource_identity";
  return "compilation";
}

function schemaInvalid(reason: string, message: string): StructuralResult {
  return {
    ok: false,
    errors: [{ kind: "schema_invalid", reason, message }],
    engine: "json_schema",
    skipped_reason: null,
  };
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
 * idiomatic mirror of Python `validate_values`. Throws if neither is supplied.
 */
export function validateValues(
  values: unknown,
  options: {
    model?: z.ZodType;
    schema?: Record<string, unknown>;
    status?: SchemaStatus;
    resources?: Record<string, Record<string, unknown>>;
  } = {},
): ValidationResult {
  if (options.model === undefined && options.schema === undefined) {
    throw new Error("validateValues() requires at least one of model or schema");
  }
  let structural: StructuralResult;
  if (options.schema !== undefined) {
    structural = validateStructural(values, options.schema, {
      strictExtras: options.status === "enforced",
      resources: options.resources,
    });
  } else if (options.status === "enforced") {
    structural = enforcedSchemaRequired();
  } else {
    structural = { ok: true, errors: [], engine: "json_schema", skipped_reason: "no_schema" };
  }
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
  const ok = structural.ok && semantic.ok;
  const firstKind = structural.errors[0]?.kind;
  const inputCodes = new Set(["artifact_unreadable", "artifact_invalid_utf8"]);
  const result = {
    contract: contractToOutput(contract),
    contract_id: contract.id,
    document_metadata: metadataToOutput(args.metadata),
    outcome: ok ? "valid" : inputCodes.has(String(firstKind)) ? "input_error" : "invalid",
    path: args.docPath,
    profile: contract.profile,
    semantic,
    status: contract.status,
    structural,
    values: args.values,
    warnings: args.warnings,
  } as ArtifactValidationResult;
  Object.defineProperty(result, "ok", { value: ok, enumerable: false });
  return result;
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

/** Load a resolved compiled-schema file and run structural validation against it. */
function structuralAgainstSchemaFile(
  resolved: string,
  values: unknown,
  strictExtras: boolean,
): StructuralResult {
  let compiledSchema: unknown;
  try {
    compiledSchema = parsePortableYaml(readUtf8(resolved));
  } catch (err) {
    if (err instanceof PortableInputError) {
      return schemaInvalid("syntax", err.message);
    }
    throw err;
  }
  if (!isMapping(compiledSchema)) {
    return schemaInvalid("syntax", "compiled schema root must be a mapping");
  }
  return validateStructural(values, compiledSchema, { strictExtras });
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
  const docDir = realpathSync(resolve(dirname(docPath)));
  const candidate = resolve(docDir, schemaRef);
  const cwd = realpathSync(resolve(process.cwd()));
  if (!isContained(docDir, candidate) && !isContained(cwd, candidate)) {
    return {
      path: null,
      error:
        "softschema.schema escapes the document directory and the working " +
        `directory: ${schemaRef}`,
    };
  }
  if (!existsSync(candidate) || !statSync(candidate).isFile()) {
    return { path: null, error: `compiled schema not found: ${schemaRef}` };
  }
  const resolved = realpathSync(candidate);
  if (!isContained(docDir, resolved) && !isContained(cwd, resolved)) {
    return {
      path: null,
      error:
        "softschema.schema escapes the document directory and the working " +
        `directory: ${schemaRef}`,
    };
  }
  return { path: resolved, error: null };
}

function structuralForValues(
  contract: Contract,
  values: unknown,
  docPath: string,
  metadata: SchemaMetadata | null,
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
    return structuralAgainstSchemaFile(resolved, values, contract.status === "enforced");
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
    return structuralAgainstSchemaFile(bound.path, values, contract.status === "enforced");
  }
  if (contract.status === "enforced") return enforcedSchemaRequired();
  if (contract.model !== null) {
    return { ok: true, errors: [], engine: "json_schema", skipped_reason: "inferred_via_model" };
  }
  return { ok: true, errors: [], engine: "json_schema", skipped_reason: "no_schema" };
}

function enforcedSchemaRequired(): StructuralResult {
  return {
    ok: false,
    errors: [
      {
        kind: "enforced_schema_required",
        message: "status 'enforced' requires a structural schema",
      },
    ],
    engine: "json_schema",
    skipped_reason: null,
  };
}

function validateExtracted(
  docPath: string,
  contract: Contract,
  values: Record<string, unknown>,
  metadata: SchemaMetadata | null,
  warnings: SchemaWarning[],
  semanticModel: z.ZodType | undefined,
): ArtifactValidationResult {
  const structural = structuralForValues(contract, values, docPath, metadata);
  const semantic: SemanticResult =
    semanticModel !== undefined
      ? validateSemantic(values, semanticModel)
      : { ok: true, errors: [], skipped_reason: "no_semantic_model" };
  return buildResult({ docPath, contract, metadata, values, structural, semantic, warnings });
}

/** Multiple top-level payload candidates; the envelope must be designated. */
export class EnvelopeAmbiguityError extends Error {
  candidates: string[];

  constructor(candidates: string[]) {
    super(
      "multiple top-level frontmatter keys; designate the softschema payload " +
        `(candidates: ${candidates.join(", ")})`,
    );
    this.candidates = candidates;
  }
}

/**
 * Infer the spec's single envelope key from a frontmatter mapping: the single
 * non-`softschema` top-level key, null when there is no candidate; throws
 * EnvelopeAmbiguityError when several keys are present. Mirrors Python's
 * `infer_envelope_key`.
 */
export function inferEnvelopeKey(frontmatter: Record<string, unknown>): string | null {
  const candidates = Object.keys(frontmatter).filter((key) => key !== "softschema");
  if (candidates.length === 0) return null;
  if (candidates.length === 1) return candidates[0] as string;
  throw new EnvelopeAmbiguityError(candidates);
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

/**
 * Validate an artifact against a contract (frontmatter-md or pure-yaml).
 *
 * A supplied `document` is trusted as already decoded, so it bypasses the portable YAML
 * rules (merge keys, explicit tags, aliases, the nesting depth bound) that reading from
 * disk enforces. Parse it with `readFrontmatterDoc` or `readYamlDoc` to keep the two
 * paths equivalent; a root decoded by a host YAML library directly may validate here and
 * be rejected by another softschema implementation reading the same file.
 */
export function validateArtifact(
  docPath: string,
  contract: Contract,
  options: {
    semanticModel?: z.ZodType;
    metadataMode?: MetadataMode;
    /**
     * An already-parsed document root, from `readFrontmatterDoc` or `readYamlDoc`. When
     * supplied the file is not re-read, on either profile, which is what lets a caller
     * that already parsed the artifact validate it without paying for a second parse.
     * The CLI passes what it parsed for binding inference so the file is read once.
     */
    document?: ParsedDocument;
  } = {},
): ArtifactValidationResult {
  checkContractId(contract.id);
  const warnings: SchemaWarning[] = [];
  const metadataMode = options.metadataMode ?? "enforced";
  if (contract.profile === "pure-yaml") {
    let raw: unknown;
    if (options.document !== undefined) {
      raw = options.document.value;
    } else {
      try {
        raw = readYamlDoc(docPath).value;
      } catch (err) {
        if (err instanceof PortableInputError) {
          return failure(docPath, contract, null, portableArtifactKind(err), err.message);
        }
        if (
          err instanceof Error &&
          "code" in err &&
          (err.code === "ENOENT" || err.code === "EACCES")
        ) {
          return failure(
            docPath,
            contract,
            null,
            "artifact_unreadable",
            (err as NodeJS.ErrnoException).message,
          );
        }
        throw err;
      }
    }
    if (!isMapping(raw)) {
      return failure(
        docPath,
        contract,
        null,
        "yaml_not_mapping",
        `YAML root is ${pyTypeName(raw)}, expected mapping`,
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
    );
  }

  let parsed: ParsedDocument;
  if (options.document !== undefined) {
    parsed = options.document;
  } else {
    try {
      parsed = readFrontmatterDoc(docPath);
    } catch (err) {
      if (err instanceof PortableInputError) {
        return failure(docPath, contract, null, portableArtifactKind(err), err.message);
      }
      if (err instanceof YamlParseError) {
        const cause = err.cause;
        const kind =
          cause instanceof PortableInputError ? portableArtifactKind(cause) : "yaml_parse_error";
        return failure(docPath, contract, null, kind, err.message);
      }
      if (
        err instanceof Error &&
        "code" in err &&
        (err.code === "ENOENT" || err.code === "EACCES")
      ) {
        return failure(
          docPath,
          contract,
          null,
          "artifact_unreadable",
          (err as NodeJS.ErrnoException).message,
        );
      }
      throw err;
    }
  }
  const { hasFence, value: frontmatter } = parsed;
  if (!hasFence) {
    return failure(docPath, contract, null, "no_frontmatter", `no frontmatter in ${docPath}`);
  }
  if (!isMapping(frontmatter)) {
    return failure(
      docPath,
      contract,
      null,
      "frontmatter_not_mapping",
      "frontmatter is not a mapping",
    );
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

  return validateExtracted(docPath, contract, values, metadata, warnings, options.semanticModel);
}

export { readFrontmatterDoc, readYamlDoc };

function portableArtifactKind(error: PortableInputError): string {
  if (error.code === "invalid_utf8") return "artifact_invalid_utf8";
  return error.code;
}
