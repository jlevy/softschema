/**
 * Repair, conform, then validate — the one operation an agent and a gate both run.
 *
 * Validation normally happens after the process that wrote the artifact has exited. By
 * then the session that could fix the document is gone, so a large, nearly-correct
 * artifact is discarded over a single field and the only recovery is regenerating the
 * whole thing from a cold prompt.
 *
 * This module closes that gap by letting the producer run the same check its judge will
 * run, before it finishes. The escalating pass is:
 *
 * 1. Read the document.
 * 2. Repair it, if it does not parse. Schema-free; see `repair.ts`.
 * 3. Conform its scalars to the types the contract declares. See `conform.ts`.
 * 4. Write once, if anything changed.
 * 5. Validate, and report both the verdict and what was changed.
 *
 * **One write, not two.** Repair hands its output to conform in memory rather than through
 * the filesystem. That is what makes idempotence and the minimal-diff property testable
 * rather than emergent, and it means a conform that has to back out cannot leave a
 * half-applied file behind.
 *
 * **`validateArtifact` stays read-only.** A function of that name must not rewrite the file
 * its caller passed, and library callers depend on that. Writing is this module's job, and
 * only when asked.
 *
 * Kept in step with the Python `softschema/pipeline.py`.
 */
import type { z } from "zod";
import { conformArtifact } from "./conform.js";
import { type Contract, parseSchemaMetadata, type SchemaMetadata } from "./models.js";
import { PortableInputError, parsePortableYaml, readUtf8, writeArtifactText } from "./portable.js";
import { type RepairResult, repairArtifact } from "./repair.js";
import {
  type ArtifactValidationResult,
  type ParsedDocument,
  parseFrontmatterText,
  parseYamlText,
  type RepairRecord,
  resolveBoundSchema,
  validateArtifact,
  YamlParseError,
} from "./validate.js";

export interface RepairAndValidateOptions {
  semanticModel?: z.ZodType;
  write?: boolean;
  /**
   * A repair the caller already performed. The CLI must repair before it can infer the
   * contract binding out of the frontmatter, so it hands the result in rather than making
   * the file be repaired twice.
   */
  repaired?: RepairResult;
}

/**
 * Repair and conform an artifact, then validate what results.
 *
 * `write: false` is the check mode: everything is computed and reported, and the file is
 * not touched. That is what a gate runs when it wants to know whether an artifact *would*
 * be repaired without mutating one under review.
 *
 * The returned result carries a `repairs` list describing every change. It is the field
 * that distinguishes "was already valid" from "was repaired into validity"; an exit code
 * cannot say which happened.
 *
 * A repaired document is written even when it still fails validation afterward. The repair
 * is independently correct — an unparsable file left on disk to preserve a failing verdict
 * helps nobody — and the verdict is reported honestly either way.
 */
export function repairAndValidateArtifact(
  docPath: string,
  contract: Contract,
  options: RepairAndValidateOptions = {},
): ArtifactValidationResult {
  const write = options.write ?? true;
  const profile = contract.profile;

  const repaired = options.repaired ?? repairArtifact(docPath, { profile, write: false });
  const records: RepairRecord[] = [...repaired.records];
  let text = repaired.text ?? undefined;

  const conformed = conformArtifact(docPath, {
    schema: loadSchema(contract, docPath, text),
    model: options.semanticModel ?? undefined,
    envelopeKey: contract.envelopeKey,
    profile,
    write: false,
    text,
  });
  if (conformed.changed) {
    records.push(...conformed.records);
    text = conformed.text ?? text;
  }

  if (records.length > 0 && write && text !== undefined) {
    writeArtifactText(docPath, text);
  }

  const document = text === undefined ? undefined : reparse(text, profile);
  const result = validateArtifact(docPath, contract, {
    semanticModel: options.semanticModel,
    document,
  });
  result.repairs = records;
  return result;
}

/**
 * The compiled schema in force, loaded once for the conform pass.
 *
 * Resolution goes through `resolveBoundSchema`, the same call validation makes, rather
 * than reading `contract.schemaPath` directly: for a self-describing artifact that field
 * is empty and the binding lives in the document's own `softschema.schema`. Taking the
 * shortcut makes conform a silent no-op for exactly the artifacts this feature exists to
 * serve.
 *
 * A schema that cannot be read is not this module's error to report: validation runs next
 * and produces the `schema_missing` or `schema_invalid` record for it.
 */
function loadSchema(
  contract: Contract,
  docPath: string,
  text: string | undefined,
): Record<string, unknown> | undefined {
  const resolved = resolveBoundSchema(contract, docPath, documentMetadata(text));
  if (resolved === null) return undefined;
  try {
    const schema = parsePortableYaml(readUtf8(resolved));
    return isMapping(schema) ? schema : undefined;
  } catch {
    return undefined;
  }
}

/**
 * The artifact's own `softschema:` block, for schema-binding resolution.
 *
 * Read from the post-repair text, because a document whose metadata block was itself
 * unparsable before the repair still binds a schema afterward.
 */
function documentMetadata(text: string | undefined): SchemaMetadata | null {
  if (text === undefined) return null;
  try {
    const parsed = parseFrontmatterText(text);
    const root = parsed.value ?? parseYamlText(text).value;
    if (!isMapping(root)) return null;
    return parseSchemaMetadata(root.softschema ?? null);
  } catch {
    // A malformed block is validation's to report; here it just means no binding.
    return null;
  }
}

function isMapping(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Parse the post-repair text the way validation would parse the file.
 *
 * Validation must judge what this pass produced, not what was on disk when it started.
 * Handing it the pre-repair parse would report failures that were just fixed — and under
 * `write: false` there is no repaired file to re-read, so the in-memory text is the only
 * correct source.
 *
 * Both branches go through the same readers validation uses, so there is no second parse
 * implementation here to drift from the first.
 */
function reparse(text: string, profile: Contract["profile"]): ParsedDocument | undefined {
  try {
    return profile === "pure-yaml" ? parseYamlText(text) : parseFrontmatterText(text);
  } catch (error) {
    // Only the failures the readers themselves throw mean "still unreadable after
    // repair"; those fall back to letting validation read the file and produce its own
    // diagnostic. Anything else is a programming error and must crash rather than be
    // quietly reclassified — mirroring Python's `except PortableInputError`.
    if (error instanceof PortableInputError || error instanceof YamlParseError) {
      return undefined;
    }
    throw error;
  }
}
