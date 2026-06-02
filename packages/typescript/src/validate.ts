/**
 * Artifact validation: read Markdown frontmatter (or pure YAML), resolve the envelope,
 * and run structural validation against the JSON Schema sidecar via ajv. The result
 * object serializes (via stableStringify) byte-identically to the Python CLI output.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { parse as yamlParse } from "yaml";
import type { z } from "zod";
import { compareStructuralRecords, normalizeAjvError, type StructuralErrorRecord } from "./errors.js";
import {
  type Contract,
  contractToOutput,
  metadataToOutput,
  parseSchemaMetadata,
  type SchemaMetadata,
  SchemaMetadataError,
  type SchemaWarning,
} from "./models.js";

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

/** Python `type(x).__name__` for the type names used in error messages. */
function pyTypeName(value: unknown): string {
  if (value === null || value === undefined) return "NoneType";
  if (Array.isArray(value)) return "list";
  if (typeof value === "string") return "str";
  if (typeof value === "boolean") return "bool";
  if (typeof value === "number") return Number.isInteger(value) ? "int" : "float";
  if (typeof value === "object") return "dict";
  return typeof value;
}

function isMapping(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

interface RawFrontmatter {
  hasFence: boolean;
  value: unknown;
}

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
  if (end === -1) return { hasFence: false, value: null };
  return { hasFence: true, value: yamlParse(lines.slice(1, end).join("\n")) ?? {} };
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

export function validateStructural(values: unknown, schemaObject: Record<string, unknown>): StructuralResult {
  const schema = { ...schemaObject };
  // $id is provenance, not a validation keyword; drop it to avoid URI-base handling.
  delete schema.$id;
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  const validateFn = ajv.compile(schema);
  const ok = validateFn(values);
  const errors: StructuralErrorRecord[] = ok
    ? []
    : (validateFn.errors ?? []).map((e) => normalizeAjvError(e, values));
  errors.sort(compareStructuralRecords);
  return { ok: errors.length === 0, errors, engine: "json_schema", skipped_reason: null };
}

/**
 * Semantic validation via Zod `safeParse` — the idiomatic mirror of the Python Pydantic
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
 * Validate a pre-extracted values mapping against a model, a schema, or both — the
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

function structuralForValues(
  contract: Contract,
  values: unknown,
  docPath: string,
): StructuralResult {
  if (contract.schemaPath !== null) {
    const resolved = resolveSchemaPath(contract.schemaPath, docPath);
    if (resolved === null) {
      return {
        ok: false,
        errors: [
          structuralError("schema_sidecar_missing", `schema sidecar not found: ${contract.schemaPath}`, {
            path: contract.schemaPath,
          }),
        ],
        engine: "json_schema",
        skipped_reason: null,
      };
    }
    return validateStructural(values, yamlParse(readFileSync(resolved, "utf8")) as Record<string, unknown>);
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
  const structural = structuralForValues(contract, values, docPath);
  const semantic: SemanticResult =
    semanticModel !== undefined
      ? validateSemantic(values, semanticModel)
      : { ok: true, errors: [], skipped_reason: "no_semantic_model" };
  return buildResult({ docPath, contract, metadata, values, structural, semantic, warnings });
}

/** Validate an artifact against a contract (frontmatter-md or pure-yaml). */
export function validateArtifact(
  docPath: string,
  contract: Contract,
  options: { semanticModel?: z.ZodType; metadataMode?: MetadataMode } = {},
): ArtifactValidationResult {
  const warnings: SchemaWarning[] = [];
  if (contract.profile === "pure-yaml") {
    const raw = yamlParse(readFileSync(docPath, "utf8")) as unknown;
    if (!isMapping(raw)) {
      return failure(
        docPath,
        contract,
        null,
        "yaml_not_mapping",
        `YAML root is ${pyTypeName(raw)}, expected mapping`,
      );
    }
    return validateExtracted(docPath, contract, raw, null, warnings, options.semanticModel);
  }

  const metadataMode = options.metadataMode ?? "enforced";
  const { hasFence, value: frontmatter } = readFrontmatter(docPath);
  if (!hasFence) {
    return failure(docPath, contract, null, "no_frontmatter", `no frontmatter in ${docPath}`);
  }
  if (!isMapping(frontmatter)) {
    return failure(docPath, contract, null, "frontmatter_not_mapping", "frontmatter is not a mapping");
  }

  let metadata: SchemaMetadata | null;
  try {
    metadata = parseSchemaMetadata(frontmatter.softschema ?? null);
  } catch (err) {
    if (err instanceof SchemaMetadataError) {
      return failure(docPath, contract, null, "document_softschema_invalid", err.message);
    }
    throw err;
  }

  if (metadata !== null && metadata.contractId !== contract.id) {
    const message = `document declares '${metadata.contractId}'; contract uses '${contract.id}'`;
    if (metadataMode === "advisory") {
      warnings.push(warning("document-contract-mismatch", message));
    } else {
      return failure(docPath, contract, metadata, "document_contract_mismatch", message, warnings);
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

  if (contract.envelopeKey !== null && !(contract.envelopeKey in frontmatter)) {
    return failure(
      docPath,
      contract,
      metadata,
      "envelope_mismatch",
      `contract '${contract.id}' expects '${contract.envelopeKey}'`,
      warnings,
    );
  }

  const values =
    contract.envelopeKey !== null
      ? frontmatter[contract.envelopeKey]
      : Object.fromEntries(Object.entries(frontmatter).filter(([k]) => k !== "softschema"));

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
