/**
 * Make an agent-authored document say the types its contract asks for.
 *
 * YAML plain scalars carry no type marker: `1850` is an integer because of how the
 * characters look, not because anyone said so. A program serializing a known value never
 * hits this, because every YAML emitter quotes a string that would otherwise resolve to
 * something else. An agent writing the document by hand has no serializer in the path, so
 * a brand genuinely named `1850` arrives as an integer and fails a `type: string`
 * contract.
 *
 * This module puts the missing serializer back, and it borrows both halves rather than
 * reimplementing either:
 *
 * - **The contract decides what is wrong.** The document is judged by the same validation
 *   that will judge it seconds later, and the only disagreement acted on is "a string
 *   belongs here and something else arrived". Everything else — a missing field, a wrong
 *   value, a shape mismatch — is reported under a different error and passes through
 *   untouched. There is no second opinion about the schema kept here to drift from the
 *   first.
 *
 * - **The document's own serializer decides how to write it.** The frontmatter is loaded
 *   round-trip, the offending scalars are replaced with their own source text as strings,
 *   and the document is written back through that same emitter.
 *
 * **Both validation layers are read, not one.** softschema runs structural and semantic
 * validation independently, and the same defect has a spelling in each: JSON Schema
 * reports `{validator: "type", validator_value: "string"}` and Zod reports an
 * `invalid_type` issue with `expected: "string"`. Which one is available depends entirely
 * on how the caller bound the contract, and neither covers the other's callers — the CLI
 * flow binds a compiled schema and has no model, while a host registering contracts as
 * Zod schemas with no `schemaPath` gets `skipped_reason: "no_schema"` from the structural
 * layer. Keying on one would silently do nothing for half the callers.
 *
 * Kept in step with the Python `softschema/conform.py`; the shared vectors check that the
 * structural half agrees, and each language's own tests cover its model half.
 */
import type { z } from "zod";
import { pyRepr } from "./errors.js";
import type { SchemaProfile } from "./models.js";
import {
  dumpRoundTrip,
  PortableInputError,
  parsePortableYaml,
  parseRoundTrip,
  readUtf8,
  splitFrontmatter,
  writeArtifactText,
} from "./portable.js";
// One-directional: this module reads validation, and the combined repair-and-validate
// entry point lives in `repairValidate.ts`, so neither of these two imports the other.
import { type RepairRecord, validateStructural } from "./validate.js";

/** A conform change, carrying the same record shape as a repair. */
export type ConformRecord = RepairRecord;

/** `kind` on every record this module emits, matching the repair pass's surface. */
export const CONFORM_KIND = "conform_applied";

/** `code` for the one correction this module performs. */
const SCALAR_CONFORMED = "scalar_conformed";

/**
 * A defect can hide another: correcting a type can newly satisfy an `if`/`then`, `anyOf`,
 * or `$ref` branch that did not previously apply, revealing errors the validator never
 * reached. Three rounds is far more nesting than a real contract has, and the loop exits
 * on the first round that changes nothing, so the common case costs one pass.
 */
const MAX_ROUNDS = 3;

/**
 * What one conform attempt did.
 *
 * `skipped_reason` is set when there was nothing to conform *against* — no schema and no
 * model — rather than nothing to conform. The distinction matters: a caller that cannot
 * tell the two apart reports a silent success for a pass that never ran.
 */
export interface ConformResult {
  changed: boolean;
  text: string | null;
  records: ConformRecord[];
  skipped_reason: string | null;
}

function outcome(partial: Partial<ConformResult>): ConformResult {
  return { changed: false, text: null, records: [], skipped_reason: null, ...partial };
}

function record(path: (string | number)[], before: string, after: string): ConformRecord {
  return {
    kind: CONFORM_KIND,
    code: SCALAR_CONFORMED,
    path,
    message: `conformed ${before} to the string ${after}`,
  };
}

/** Whether a JSON Schema `type` keyword asks for a string. */
function admitsString(validatorValue: unknown): boolean {
  if (typeof validatorValue === "string") return validatorValue === "string";
  if (Array.isArray(validatorValue)) return validatorValue.includes("string");
  return false;
}

/** Where the compiled schema wanted a string and got something else. */
function structuralLocations(
  values: unknown,
  schema: Record<string, unknown>,
): (string | number)[][] {
  const result = validateStructural(values, schema);
  return result.errors
    .filter((error) => error.validator === "type" && admitsString(error.validator_value))
    .map((error) => (error.path ?? []) as (string | number)[]);
}

/**
 * Where the model wanted a string and got something else.
 *
 * Everything the model reports under any other issue is a real disagreement with the
 * contract and is left alone to fail.
 */
function semanticLocations(model: z.ZodType, values: unknown): (string | number)[][] {
  let parsed: ReturnType<z.ZodType["safeParse"]>;
  try {
    parsed = model.safeParse(values);
  } catch {
    // A contract model is downstream code and a refinement of its own can throw anything.
    // This pass is an optimization on the way to validation, which runs next and owns
    // reporting the failure, so a model that will not run turns the pass off for this
    // artifact rather than taking the step down.
    return [];
  }
  if (parsed.success) return [];
  return parsed.error.issues
    .filter(
      (issue) =>
        issue.code === "invalid_type" && (issue as { expected?: unknown }).expected === "string",
    )
    .map((issue) => issue.path as (string | number)[]);
}

/** The container and key holding the value at `path`, or null if unreachable. */
function nodeAt(
  root: unknown,
  path: (string | number)[],
): { container: Record<string, unknown> | unknown[]; key: string | number } | null {
  if (path.length === 0) return null;
  let node: unknown = root;
  for (const step of path.slice(0, -1)) {
    if (isPlainObject(node) && step in node) node = node[step as string];
    else if (Array.isArray(node) && typeof step === "number" && step >= 0 && step < node.length)
      node = node[step];
    else return null;
  }
  const key = path[path.length - 1] as string | number;
  if (isPlainObject(node) && key in node) return { container: node, key };
  if (Array.isArray(node) && typeof key === "number" && key >= 0 && key < node.length) {
    return { container: node, key };
  }
  return null;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Scalar kinds that have a faithful written form.
 *
 * `null` is absent deliberately: a null is an absent value, not a notation accident, and
 * stringifying one would invent data. Dates are absent for a reason specific to
 * softschema: `parsePortableYaml` maps an implicit timestamp to a *string* already and
 * rejects a host-native date outright, so conforming one would write back a value the
 * portable reader then refuses.
 */
function isCoercible(value: unknown): value is boolean | number {
  return typeof value === "boolean" || typeof value === "number";
}

export interface ConformOptions {
  schema?: Record<string, unknown>;
  model?: z.ZodType;
  envelopeKey?: string | null;
  profile?: SchemaProfile;
  write?: boolean;
  text?: string;
}

/**
 * Conform one artifact's scalars to the string type its contract declares.
 *
 * `schema` and `model` are the two sources of truth; supply either or both. With neither
 * there is nothing to conform against, and the result says so through `skipped_reason`
 * rather than reporting an untouched document as a success.
 *
 * `text` lets a caller that already has the document (a repair pass, for instance) hand it
 * over instead of paying for a second read — which is also what keeps the two passes to a
 * single write.
 */
export function conformArtifact(path: string, options: ConformOptions = {}): ConformResult {
  const { schema, model, envelopeKey = null, profile = "frontmatter-md", write = true } = options;
  if (schema === undefined && model === undefined) {
    return outcome({ text: options.text ?? null, skipped_reason: "no_contract_binding" });
  }

  let text: string;
  if (options.text !== undefined) {
    text = options.text;
  } else {
    try {
      text = readUtf8(path);
    } catch {
      return outcome({ skipped_reason: "artifact_unreadable" });
    }
  }

  const crlf = text.includes("\r\n");
  const normalized = crlf ? text.replaceAll("\r\n", "\n") : text;

  let region: string;
  let prefix = "";
  let suffix = "";
  if (profile === "pure-yaml") {
    region = normalized;
  } else {
    const split = splitFrontmatter(normalized);
    if (split === null) return outcome({ text, skipped_reason: "no_frontmatter" });
    region = split.metadataText;
    prefix = normalized.slice(0, split.metadataOffset);
    suffix = normalized.slice(split.metadataEnd);
  }

  const document = parseRoundTrip(region);
  if (document.errors.length > 0) {
    // A document that does not parse is the repair pass's problem, not this one's.
    return outcome({ text, skipped_reason: "unparsable" });
  }
  const root = document.toJS() as unknown;
  if (!isPlainObject(root)) return outcome({ text, skipped_reason: "not_a_mapping" });

  const values = envelopeKey === null ? root : root[envelopeKey];
  if (!isPlainObject(values)) {
    // A missing or non-mapping envelope is a real disagreement for validation to report,
    // not licence to apply the envelope's contract to the document root.
    return outcome({ text, skipped_reason: "no_envelope" });
  }

  const records: ConformRecord[] = [];
  for (let round = 0; round < MAX_ROUNDS; round++) {
    const locations: (string | number)[][] = [];
    if (schema !== undefined) locations.push(...structuralLocations(values, schema));
    if (model !== undefined) locations.push(...semanticLocations(model, values));
    if (locations.length === 0) break;
    let changedThisRound = false;
    for (const location of locations) {
      const found = nodeAt(values, location);
      if (found === null) continue;
      const current = (found.container as Record<string | number, unknown>)[found.key];
      if (!isCoercible(current)) continue;
      // Ask the document for the scalar's own source text, so `1.10` stays `1.10` and
      // `007` stays `007`; `String()` collapses both.
      const scalarPath = envelopeKey === null ? location : [envelopeKey, ...location];
      const source = scalarSourceText(document, scalarPath, current);
      (found.container as Record<string | number, unknown>)[found.key] = source;
      document.setIn(scalarPath, source);
      records.push(record(location, pyRepr(current), pyRepr(source)));
      changedThisRound = true;
    }
    if (!changedThisRound) break;
  }

  if (records.length === 0) return outcome({ text });

  let conformed = prefix + dumpRoundTrip(document) + suffix;
  if (crlf) conformed = conformed.replaceAll("\n", "\r\n");

  // The portable round-trip guard: never write a value the reader would then reject. A
  // conform that cannot survive its own reader is worse than no conform, because it turns
  // a document that failed one field into a document that fails to parse.
  if (!stillPortable(conformed, profile)) {
    return outcome({ text, skipped_reason: "not_portable" });
  }

  if (write) writeArtifactText(path, conformed);
  return outcome({ changed: true, text: conformed, records });
}

/**
 * The scalar's own source text, taken from the round-trip node rather than from the
 * parsed value, so a notation the author chose survives being retyped.
 */
function scalarSourceText(
  document: ReturnType<typeof parseRoundTrip>,
  path: (string | number)[],
  fallback: boolean | number,
): string {
  const node = document.getIn(path, true) as { source?: string } | undefined;
  return typeof node?.source === "string" ? node.source : String(fallback);
}

/** Whether the conformed document still reads under the portable rules. */
function stillPortable(text: string, profile: SchemaProfile): boolean {
  let region: string | null;
  if (profile === "pure-yaml") {
    region = text;
  } else {
    const split = splitFrontmatter(text.replaceAll("\r\n", "\n"));
    region = split === null ? null : split.metadataText;
  }
  if (region === null) return false;
  try {
    parsePortableYaml(region);
  } catch (error) {
    if (error instanceof PortableInputError) return false;
    throw error;
  }
  return true;
}
