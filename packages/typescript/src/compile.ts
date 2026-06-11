/**
 * Compile a Zod schema to a canonical JSON Schema YAML sidecar, mirroring the Python
 * `compile_model`. The schema_sha256 is computed over the canonical JSON (not the YAML
 * text), so it is the language-neutral fingerprint used for cross-implementation parity.
 *
 * Sidecar *files* are content-identical across languages, not byte-identical: the YAML
 * writers differ in serialization style (indentation, quoting), so `--check` drift
 * compares parsed canonical content, and the schema_sha256 over the canonical JSON is
 * the cross-language fingerprint, independent of YAML formatting.
 */
import { existsSync, readFileSync } from "node:fs";
import { writeFileSync } from "atomically";
import { parse as yamlParse, stringify as yamlStringify } from "yaml";
import { z } from "zod";
import { canonicalizeJsonSchema } from "./canonicalize.js";
import { canonicalJson, schemaSha256 } from "./settings.js";

export const SOFTSCHEMA_FORMAT_VERSION = "0.1.0";
export const JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema";

export interface CompileResult {
  outPath: string;
  schemaYaml: string;
  drift: boolean;
  driftDiff: string | null;
  schemaSha256: string;
}

export interface CompileOptions {
  contractId?: string | null;
  checkOnly?: boolean;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function augmentSchema(
  schema: Record<string, unknown>,
  contractId: string | null,
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...schema };
  out.$schema ??= JSON_SCHEMA_DRAFT;
  if (contractId !== null) {
    out.$id ??= contractId;
  }
  // Language-neutral: no `generated_from` provenance (would leak the implementation).
  // Merge into an existing x-softschema mapping (Python uses setdefault+update semantics)
  // so custom fields from the raw schema are preserved.
  const existing = isPlainObject(out["x-softschema"])
    ? (out["x-softschema"] as Record<string, unknown>)
    : {};
  out["x-softschema"] = {
    ...existing,
    contract: contractId,
    softschema_format_version: SOFTSCHEMA_FORMAT_VERSION,
  };
  return out;
}

function renderYaml(schema: Record<string, unknown>): string {
  return yamlStringify(schema, { sortMapEntries: true, lineWidth: 0 });
}

/**
 * Build the canonical schema object (with schema_sha256 set), without serializing or
 * writing. Exposed so conformance tests can compare the content directly to the
 * committed reference, independent of YAML formatting.
 */
export function buildCanonicalSchema(
  zodSchema: z.ZodType,
  contractId: string | null = null,
): { schema: Record<string, unknown>; sha: string } {
  const raw = z.toJSONSchema(zodSchema, {
    target: "draft-2020-12",
    io: "input",
    // Only id-registered named objects (Address, Event) belong in $defs; primitives stay
    // inline. "inline" extracts by id, not by repetition, matching Pydantic's $defs shape.
    reused: "inline",
    unrepresentable: "throw",
  }) as Record<string, unknown>;
  const schema = canonicalizeJsonSchema(augmentSchema(raw, contractId));
  const sha = schemaSha256(schema);
  (schema["x-softschema"] as Record<string, unknown>).schema_sha256 = sha;
  return { schema, sha };
}

export function compileSchema(
  zodSchema: z.ZodType,
  outPath: string,
  options: CompileOptions = {},
): CompileResult {
  const { schema, sha } = buildCanonicalSchema(zodSchema, options.contractId ?? null);
  const rendered = renderYaml(schema);

  if (options.checkOnly) {
    if (!existsSync(outPath)) {
      return {
        outPath,
        schemaYaml: rendered,
        drift: true,
        driftDiff: `missing committed schema sidecar at ${outPath}`,
        schemaSha256: sha,
      };
    }
    // Compare parsed content, not raw bytes, so YAML formatting (a different writer than
    // Python's) is not treated as drift; only a genuine schema change is.
    const existing = yamlParse(readFileSync(outPath, "utf8")) as unknown;
    const drift = canonicalJson(existing) !== canonicalJson(schema);
    return {
      outPath,
      schemaYaml: rendered,
      drift,
      driftDiff: drift ? `committed schema at ${outPath} differs from compile output` : null,
      schemaSha256: sha,
    };
  }

  writeFileSync(outPath, rendered, { encoding: "utf8" });
  return { outPath, schemaYaml: rendered, drift: false, driftDiff: null, schemaSha256: sha };
}
