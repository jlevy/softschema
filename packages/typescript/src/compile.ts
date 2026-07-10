/**
 * Compile a Zod schema to a canonical JSON Schema YAML file, mirroring the Python
 * `compile_model`. The schema_sha256 is computed over the canonical JSON (not the YAML
 * text), so it is the language-neutral fingerprint used for cross-implementation parity.
 *
 * Compiled schema *files* are content-identical across languages, not byte-identical: the YAML
 * writers differ in serialization style (indentation, quoting), so `--check` drift
 * compares parsed canonical content, and the schema_sha256 over the canonical JSON is
 * the cross-language fingerprint, independent of YAML formatting.
 */
import { statSync } from "node:fs";
import { writeFileSync } from "atomically";
import { stringify as yamlStringify } from "yaml";
import { z } from "zod";
import { readBoundedBytes } from "./bounded-file.js";
import { canonicalizeJsonSchema } from "./canonicalize.js";
import {
  DEFAULT_VALIDATION_LIMITS,
  normalizePortableValue,
  PortableValueError,
} from "./core/value-domain.js";
import { isMapping } from "./guards.js";
import { validateContractId, validateSchemaId } from "./models.js";
import { isFileSystemError } from "./node-errors.js";
import { canonicalJson, schemaSha256 } from "./settings.js";
import { parsePortableYaml } from "./yaml-value-domain.js";

export const SOFTSCHEMA_FORMAT_VERSION = "0.1.0";
export const JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema";
export const ROOT_COMPILER_METADATA_RESERVED_MESSAGE =
  "model schema root must not define reserved x-softschema metadata";

export interface CompileResult {
  outPath: string;
  schemaYaml: string;
  drift: boolean;
  driftDiff: string | null;
  schemaSha256: string;
}

export interface CompileOptions {
  contractId: string;
  schemaId?: string | null;
  checkOnly?: boolean;
}

function augmentSchema(
  schema: Record<string, unknown>,
  contractId: string,
  schemaId: string | null,
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...schema };
  out.$schema ??= JSON_SCHEMA_DRAFT;
  // Only the explicit schemaId option controls JSON Schema resource identity.
  delete out.$id;
  if (schemaId !== null) out.$id = schemaId;
  // Language-neutral: no `generated_from` provenance (would leak the implementation).
  // The root block is reserved compiler output. Reject rather than silently merge or
  // discard model metadata, which could violate the public compiled-schema profile.
  if (Object.hasOwn(out, "x-softschema")) {
    throw new Error(ROOT_COMPILER_METADATA_RESERVED_MESSAGE);
  }
  out["x-softschema"] = {
    contract: contractId,
    softschema_format_version: SOFTSCHEMA_FORMAT_VERSION,
  };
  return out;
}

function renderYaml(schema: Record<string, unknown>): string {
  return yamlStringify(schema, { sortMapEntries: true, lineWidth: 0 });
}

/** @internal Render a sidecar that every runtime accepts and bounded readers can reopen. */
export function renderSchemaWithinLimit(schema: Record<string, unknown>): string {
  const canonical = canonicalJson(schema);
  const limit = DEFAULT_VALIDATION_LIMITS.maxResourceBytes;
  if (Buffer.byteLength(canonical, "utf8") > limit) {
    throw new PortableValueError("maximum resource size exceeded");
  }
  const rendered = renderYaml(schema);
  // JSON is valid YAML 1.2 and is already the shared canonical byte form. Near the
  // resource boundary, use it when a runtime YAML writer's formatting overhead would
  // otherwise make compiler acceptance implementation-specific.
  return Buffer.byteLength(rendered, "utf8") <= limit ? rendered : canonical;
}

/**
 * Build the canonical schema object (with schema_sha256 set), without serializing or
 * writing. Exposed so conformance tests can compare the content directly to the
 * committed reference, independent of YAML formatting.
 */
export function buildCanonicalSchema(
  zodSchema: z.ZodType,
  contractId: string,
  schemaId: string | null = null,
): { schema: Record<string, unknown>; sha: string } {
  if (contractId === null || contractId === undefined) {
    throw new Error("softschema compilation requires a contract ID");
  }
  const checkedContractId = validateContractId(contractId);
  const checkedSchemaId = schemaId === null ? null : validateSchemaId(schemaId);
  const raw = z.toJSONSchema(zodSchema, {
    target: "draft-2020-12",
    io: "input",
    // Only id-registered named objects (Address, Event) belong in $defs; primitives stay
    // inline. "inline" extracts by id, not by repetition, matching Pydantic's $defs shape.
    reused: "inline",
    unrepresentable: "throw",
  }) as Record<string, unknown>;
  const canonicalSchema = canonicalizeJsonSchema(
    augmentSchema(raw, checkedContractId, checkedSchemaId),
  );
  // Python distinguishes integral floats from integers while JavaScript has one
  // Number type. Normalize the complete compiled value before hashing and rendering
  // so JSON-equivalent bounds such as 10.0 and 10 have one portable representation.
  // The same boundary rejects non-finite and unsafe integer values that cannot retain
  // an exact language-neutral JSON meaning.
  const normalizedSchema = normalizePortableValue(canonicalSchema).value;
  if (!isMapping(normalizedSchema)) {
    throw new TypeError("compiled schema root must be a mapping");
  }
  const schema = normalizedSchema;
  const sha = schemaSha256(schema);
  (schema["x-softschema"] as Record<string, unknown>).schema_sha256 = sha;
  // Charge the emitted digest field against portable node/scalar budgets too. The
  // digest cannot be included in its own preimage, but it is part of the sidecar that
  // SchemaView must be able to reopen.
  const finalSchema = normalizePortableValue(schema).value;
  if (!isMapping(finalSchema)) {
    throw new TypeError("compiled schema root must be a mapping");
  }
  return { schema: finalSchema, sha };
}

export function compileSchema(
  zodSchema: z.ZodType,
  outPath: string,
  options: CompileOptions,
): CompileResult {
  if (options?.contractId === null || options?.contractId === undefined) {
    throw new Error("softschema compilation requires a contract ID");
  }
  const { schema, sha } = buildCanonicalSchema(
    zodSchema,
    options.contractId,
    options.schemaId ?? null,
  );
  const rendered = renderSchemaWithinLimit(schema);

  if (options.checkOnly) {
    const missingResult = (): CompileResult => ({
      outPath,
      schemaYaml: rendered,
      drift: true,
      driftDiff: `missing committed compiled schema at ${outPath}`,
      schemaSha256: sha,
    });
    let encoded: Uint8Array;
    try {
      if (!statSync(outPath).isFile()) return missingResult();
      // Compare parsed content, not raw bytes, so YAML formatting (a different writer than
      // Python's) is not treated as drift; only a genuine schema change is.
      encoded = readBoundedBytes(outPath, DEFAULT_VALIDATION_LIMITS.maxResourceBytes);
    } catch (error) {
      if (isFileSystemError(error) && (error.code === "ENOENT" || error.code === "ENOTDIR")) {
        return missingResult();
      }
      throw error;
    }
    const existing = parsePortableYaml(
      new TextDecoder("utf-8", { fatal: true }).decode(encoded),
      DEFAULT_VALIDATION_LIMITS,
      { encodedSize: encoded.byteLength },
    );
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
