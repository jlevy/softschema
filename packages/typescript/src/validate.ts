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
import {
  compareStructuralRecords,
  normalizeAjvError,
  type StructuralErrorRecord,
} from "./errors.js";
import {
  type Contract,
  contractToOutput,
  metadataToOutput,
  parseSchemaMetadata,
  type SchemaMetadata,
  SchemaMetadataError,
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

interface Frontmatter {
  frontmatter: Record<string, unknown> | null;
}

function readFrontmatter(path: string): Frontmatter {
  const text = readFileSync(path, "utf8");
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== "---") {
    return { frontmatter: null };
  }
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i]?.trim() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) {
    return { frontmatter: null };
  }
  const parsed = yamlParse(lines.slice(1, end).join("\n")) as unknown;
  return { frontmatter: (parsed ?? {}) as Record<string, unknown> };
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
  if (result.success) {
    return { ok: true, errors: [], skipped_reason: null };
  }
  const errors = result.error.issues.map((issue) => ({
    code: issue.code,
    path: issue.path,
    message: issue.message,
  }));
  return { ok: false, errors, skipped_reason: null };
}

export interface ArtifactValidationResult {
  ok: boolean;
  output: Record<string, unknown>;
}

function buildResult(args: {
  docPath: string;
  contract: Contract;
  metadata: SchemaMetadata | null;
  values: Record<string, unknown> | null;
  structural: StructuralResult;
  semantic: SemanticResult;
  warnings: Record<string, unknown>[];
}): ArtifactValidationResult {
  const { contract, structural, semantic } = args;
  const ok = structural.ok && semantic.ok;
  const output: Record<string, unknown> = {
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
  };
  return { ok, output };
}

function failure(
  docPath: string,
  contract: Contract,
  metadata: SchemaMetadata | null,
  kind: string,
  message: string,
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
    warnings: [],
  });
}

/** Validate a frontmatter-md artifact against a contract (structural + optional semantic). */
export function validateArtifact(
  docPath: string,
  contract: Contract,
  options: { semanticModel?: z.ZodType } = {},
): ArtifactValidationResult {
  const { frontmatter } = readFrontmatter(docPath);
  if (frontmatter === null) {
    return failure(docPath, contract, null, "no_frontmatter", `no frontmatter in ${docPath}`);
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
    return failure(
      docPath,
      contract,
      metadata,
      "document_contract_mismatch",
      `document declares ${JSON.stringify(metadata.contractId)}; contract uses ${JSON.stringify(contract.id)}`,
    );
  }

  if (contract.envelopeKey !== null && !(contract.envelopeKey in frontmatter)) {
    return failure(
      docPath,
      contract,
      metadata,
      "envelope_mismatch",
      `contract ${JSON.stringify(contract.id)} expects ${JSON.stringify(contract.envelopeKey)}`,
    );
  }

  const values =
    contract.envelopeKey !== null
      ? frontmatter[contract.envelopeKey]
      : Object.fromEntries(Object.entries(frontmatter).filter(([k]) => k !== "softschema"));

  if (values === null || typeof values !== "object" || Array.isArray(values)) {
    return failure(
      docPath,
      contract,
      metadata,
      "envelope_not_mapping",
      `envelope value is ${Array.isArray(values) ? "list" : typeof values}, expected mapping`,
    );
  }

  let structural: StructuralResult;
  if (contract.schemaPath !== null) {
    const resolved = resolveSchemaPath(contract.schemaPath, docPath);
    if (resolved === null) {
      structural = {
        ok: false,
        errors: [
          structuralError("schema_sidecar_missing", `schema sidecar not found: ${contract.schemaPath}`, {
            path: contract.schemaPath,
          }),
        ],
        engine: "json_schema",
        skipped_reason: null,
      };
    } else {
      const schemaObject = yamlParse(readFileSync(resolved, "utf8")) as Record<string, unknown>;
      structural = validateStructural(values, schemaObject);
    }
  } else if (contract.model !== null) {
    structural = { ok: true, errors: [], engine: "json_schema", skipped_reason: "inferred_via_model" };
  } else {
    structural = { ok: true, errors: [], engine: "json_schema", skipped_reason: "no_schema" };
  }

  const semantic: SemanticResult =
    options.semanticModel !== undefined
      ? validateSemantic(values, options.semanticModel)
      : { ok: true, errors: [], skipped_reason: "no_semantic_model" };

  return buildResult({
    docPath,
    contract,
    metadata,
    values: values as Record<string, unknown>,
    structural,
    semantic,
    warnings: [],
  });
}

export { readFrontmatter };
