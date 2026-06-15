/**
 * Artifact validation: read Markdown frontmatter (or pure YAML), resolve the envelope,
 * and run structural validation against the compiled JSON Schema via ajv. The result
 * object serializes (via stableStringify) byte-identically to the Python CLI output.
 */
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import type { ValidateFunction } from "ajv/dist/2020.js";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { parse as yamlParse } from "yaml";
import type { z } from "zod";
import { applyEnforcedExtras } from "./canonicalize.js";
import {
  collapseAdditionalProperties,
  compareStructuralRecords,
  normalizeAjvError,
  type StructuralErrorRecord,
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
} from "./models.js";

/** Module-level Ajv2020 instance, initialized once and reused for all validations. */
const sharedAjv = new Ajv2020({ allErrors: true, strict: false, verbose: true });
addFormats(sharedAjv);

/** Cache of compiled validators keyed by the stable JSON serialization of the final schema. */
const validatorCache = new Map<string, ValidateFunction>();

/** Deterministic JSON key for a schema object (sorts keys recursively). */
function stableCacheKey(obj: unknown): string {
  return JSON.stringify(obj, (_key, value) => {
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      const sorted: Record<string, unknown> = {};
      for (const k of Object.keys(value).sort()) {
        sorted[k] = value[k];
      }
      return sorted;
    }
    return value;
  });
}

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
  ok: boolean;
  output: Record<string, unknown>;
}

export type MetadataMode = "enforced" | "advisory";

export interface RawFrontmatter {
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
    return yamlParse(text);
  } catch (err) {
    throw new YamlParseError((err as Error).message);
  }
}

/**
 * Read the YAML inside a document's leading `---` frontmatter fence. Returns
 * `hasFence: false` with a null value when there is no fence or the fence is empty (the
 * caller then treats the file as pure YAML). Throws `YamlParseError` on an unterminated
 * fence or non-mapping frontmatter, byte-matching the Python `frontmatter_format` errors.
 */
function readFrontmatter(path: string): RawFrontmatter {
  const text = readFileSync(path, "utf8");
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
    throw new YamlParseError(`Delimiter \`---\` for end of frontmatter not found: \`${path}\``);
  }
  // Empty frontmatter (end-fence at line 1, zero content lines between fences):
  // Python's fmf_read returns metadata=None → no_frontmatter.
  if (end === 1) return { hasFence: false, value: null };
  const parsed = parseYaml(lines.slice(1, end).join("\n"));
  if (!isMapping(parsed)) {
    // frontmatter-format's fmf_read rejects non-mapping frontmatter: a whitespace-only
    // block (YAML `null`), a list, or a bare scalar. Match its message and Python class
    // names (`NoneType`, `list`, `str`, …) so the parse error is byte-identical to the
    // Python CLI across every entrypoint (ss-eero / ss-7cbb).
    throw new YamlParseError(
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

export function validateStructural(
  values: unknown,
  schemaObject: Record<string, unknown>,
  options: { strictExtras?: boolean } = {},
): StructuralResult {
  let schema = { ...schemaObject };
  // $id is provenance, not a validation keyword; drop it to avoid URI-base handling.
  delete schema.$id;
  if (options.strictExtras) {
    // The `status: enforced` overlay: object schemas that declare `properties` but
    // omit `additionalProperties` are validated as closed. See applyEnforcedExtras.
    schema = applyEnforcedExtras(schema) as Record<string, unknown>;
  }
  // Cache key is computed from the FINAL schema (post-$id deletion and post-overlay),
  // so two calls with the same base schema but different strictExtras won't collide.
  const cacheKey = stableCacheKey(schema);
  let validateFn = validatorCache.get(cacheKey);
  if (validateFn === undefined) {
    validateFn = sharedAjv.compile(schema);
    validatorCache.set(cacheKey, validateFn);
  }
  const ok = validateFn(values);
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
 * idiomatic mirror of Python `validate_values`. Throws if neither is supplied.
 */
export function validateValues(
  values: unknown,
  options: { model?: z.ZodType; schema?: Record<string, unknown> } = {},
): ValidationResult {
  if (options.model === undefined && options.schema === undefined) {
    throw new Error("validateValues() requires at least one of model or schema");
  }
  const structural = options.schema
    ? validateStructural(values, options.schema)
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

/** Load a resolved compiled-schema file and run structural validation against it. */
function structuralAgainstSchemaFile(
  resolved: string,
  values: unknown,
  strictExtras: boolean,
): StructuralResult {
  let compiledSchema: unknown;
  try {
    compiledSchema = parseYaml(readFileSync(resolved, "utf8"));
  } catch (err) {
    if (err instanceof YamlParseError) {
      return {
        ok: false,
        errors: [structuralError("schema_invalid", err.message)],
        engine: "json_schema",
        skipped_reason: null,
      };
    }
    throw err;
  }
  if (!isMapping(compiledSchema)) {
    return {
      ok: false,
      errors: [
        structuralError(
          "schema_invalid",
          `compiled schema root is ${pyTypeName(compiledSchema)}, expected mapping`,
        ),
      ],
      engine: "json_schema",
      skipped_reason: null,
    };
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

/** Validate an artifact against a contract (frontmatter-md or pure-yaml). */
export function validateArtifact(
  docPath: string,
  contract: Contract,
  options: {
    semanticModel?: z.ZodType;
    metadataMode?: MetadataMode;
    /**
     * An already-parsed frontmatter (from `readFrontmatter`); when supplied for a
     * frontmatter-md contract the document is not re-read. The CLI passes what it
     * parsed for binding inference so the file is read once.
     */
    preParsed?: RawFrontmatter;
  } = {},
): ArtifactValidationResult {
  const warnings: SchemaWarning[] = [];
  const metadataMode = options.metadataMode ?? "enforced";
  if (contract.profile === "pure-yaml") {
    let raw: unknown;
    try {
      raw = parseYaml(readFileSync(docPath, "utf8"));
    } catch (err) {
      if (err instanceof YamlParseError) {
        return failure(docPath, contract, null, "parse_error", err.message);
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
          "parse_error",
          (err as NodeJS.ErrnoException).message,
        );
      }
      throw err;
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

  let parsed: RawFrontmatter;
  if (options.preParsed !== undefined) {
    parsed = options.preParsed;
  } else {
    try {
      parsed = readFrontmatter(docPath);
    } catch (err) {
      if (err instanceof YamlParseError) {
        return failure(docPath, contract, null, "parse_error", err.message);
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
          "parse_error",
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

export { readFrontmatter };
