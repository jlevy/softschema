/**
 * Compile a Zod schema to a canonical JSON Schema YAML sidecar, mirroring the Python
 * `compile_model`. The schema_sha256 is computed over the canonical JSON (not the YAML
 * text), so it is the language-neutral fingerprint used for cross-implementation parity.
 *
 * NOTE: byte-identical sidecar *files* across languages additionally require matching the
 * Python side's YAML writer (frontmatter-format/ruamel) and the `generated_from`
 * provenance string; that reconciliation is Phase 2. The content hash is independent of
 * YAML formatting.
 */
import { writeFileSync } from "node:fs";
import { existsSync, readFileSync } from "node:fs";
import { stringify as yamlStringify } from "yaml";
import { z } from "zod";
import { canonicalizeJsonSchema } from "./canonicalize.js";
import { schemaSha256 } from "./settings.js";

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
  out["x-softschema"] = {
    contract: contractId,
    softschema_format_version: SOFTSCHEMA_FORMAT_VERSION,
  };
  return out;
}

function renderYaml(schema: Record<string, unknown>): string {
  return yamlStringify(schema, { sortMapEntries: true, lineWidth: 0 });
}

export function compileSchema(
  zodSchema: z.ZodType,
  outPath: string,
  options: CompileOptions = {},
): CompileResult {
  const contractId = options.contractId ?? null;
  const raw = z.toJSONSchema(zodSchema, {
    target: "draft-2020-12",
    io: "input",
    reused: "ref",
    unrepresentable: "throw",
  }) as Record<string, unknown>;
  const schema = canonicalizeJsonSchema(augmentSchema(raw, contractId));
  const sha = schemaSha256(schema);
  (schema["x-softschema"] as Record<string, unknown>).schema_sha256 = sha;
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
    const existing = readFileSync(outPath, "utf8");
    const drift = existing.trim() !== rendered.trim();
    return {
      outPath,
      schemaYaml: rendered,
      drift,
      driftDiff: drift ? `committed schema at ${outPath} differs from compile output` : null,
      schemaSha256: sha,
    };
  }

  writeFileSync(outPath, rendered, "utf8");
  return { outPath, schemaYaml: rendered, drift: false, driftDiff: null, schemaSha256: sha };
}
