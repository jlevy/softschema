/**
 * Syntactic repair for YAML an agent wrote by hand.
 *
 * A program emitting YAML has a serializer in the path, and every serializer quotes a
 * value that would otherwise change meaning. An agent writing frontmatter by hand has no
 * such thing, so it produces a narrow, recognizable family of mistakes: an unquoted `: `
 * inside a note (`summary: Note: actually Q1`), or a value that opens with a quoted
 * phrase and then keeps going (`"near me" trends accelerated`). Both make the whole
 * document unparsable, which means nothing downstream can read any of it — a total loss
 * over one character.
 *
 * This module puts quotes back where the missing serializer would have, and nothing else.
 * It runs before any schema is consulted, because a document that does not parse has no
 * values to validate.
 *
 * **Scope.** This is for artifacts an agent just emitted. Running it over human-authored
 * or program-generated YAML hides a real bug: if your code writes invalid YAML, fix the
 * writer.
 *
 * **Why the self-check uses softschema's own reader.** The obvious implementation checks
 * its work with a plain YAML parse. That is not enough here, because `parsePortableYaml`
 * enforces rules an ordinary parser does not — aliases and anchors rejected, merge keys,
 * explicit tags, non-string mapping keys, a depth bound, the safe-integer range. A repair
 * judged by the looser parser would report success and then fail validation seconds
 * later, which is the exact failure this module exists to prevent, moved one layer up.
 *
 * **What is deliberately not repaired.** Several portable violations look like parse
 * failures and are not typos: an alias, a merge key, an explicit tag. Each is something
 * the author meant, and quoting cannot fix any of them. They pass through with their
 * original error code so the caller reports the real problem instead of a failed repair.
 *
 * Kept line for line with the Python `softschema/repair.py`; the shared vectors check
 * that the two agree.
 */
import type { SchemaProfile } from "./models.js";
import {
  PortableInputError,
  parsePortableYaml,
  readUtf8,
  splitFrontmatter,
  writeArtifactText,
} from "./portable.js";
import type { RepairRecord } from "./validate.js";

export type { RepairRecord };

/**
 * `kind` on every record this module emits.
 *
 * Repairs are reported with the same `kind`/`code`/`path` surface as errors, so a caller
 * matches what was fixed the way it matches what failed. See the spec, "Matching on
 * structural error records".
 */
export const REPAIR_KIND = "repair_applied";

/** `code` for the one repair this module performs. */
const YAML_QUOTED_SCALAR = "yaml_quoted_scalar";

/**
 * Portable violations that are not authoring slips. Quoting a scalar cannot fix any of
 * them, and attempting a repair would replace a precise diagnostic with a vague one.
 */
const NOT_REPAIRABLE = new Set([
  "yaml_alias",
  "yaml_merge_key",
  "yaml_custom_tag",
  "yaml_non_string_key",
  "yaml_duplicate_key",
  "yaml_limit",
  "yaml_unsupported_scalar",
  "number_out_of_range",
  "number_negative_zero",
  "invalid_utf8",
]);

/**
 * A mapping line: indent, key, `: `, then the value.
 *
 * The indent is optional, unlike the upstream version this is ported from, which required
 * it. Every payload there sits under an envelope so its keys are always indented; here the
 * frontmatter root and the whole pure-yaml profile put keys at column 0.
 *
 * The character class is spelled out rather than using `\w`, which is ASCII-only in
 * JavaScript and Unicode-aware in Python. Both implementations pin this same conservative
 * ASCII set, so a non-ASCII key is left unrepaired identically on both sides; the shared
 * vectors lock this in.
 */
const MAPPING_LINE = /^(?<indent>[ \t]*)(?<key>[A-Za-z0-9_.-]+): (?<value>.+)$/;

/**
 * What one repair attempt did.
 *
 * `ok` says the document parses now — which it may have done all along. `changed` says
 * this pass rewrote something. The two are independent: an untouched valid document is
 * `ok` and unchanged, and a document too broken to fix is neither.
 */
export interface RepairResult {
  ok: boolean;
  changed: boolean;
  text: string | null;
  records: RepairRecord[];
  errorCode: string | null;
  errorMessage: string | null;
}

function result(partial: Partial<RepairResult>): RepairResult {
  return {
    ok: false,
    changed: false,
    text: null,
    records: [],
    errorCode: null,
    errorMessage: null,
    ...partial,
  };
}

function record(path: (string | number)[], message: string): RepairRecord {
  return { kind: REPAIR_KIND, code: YAML_QUOTED_SCALAR, path, message };
}

/**
 * Whether a plain scalar carries something YAML will read as structure.
 *
 * Two shapes matter. A second `: ` makes the parser look for a nested mapping where the
 * author meant prose. A leading quote that never closes makes it try to read a quoted
 * scalar and run off the end of the value.
 */
function valueNeedsQuoting(value: string): boolean {
  const stripped = value.trim();
  if (
    (stripped.startsWith('"') && stripped.endsWith('"')) ||
    (stripped.startsWith("'") && stripped.endsWith("'"))
  ) {
    return false;
  }
  if (["null", "true", "false", "~", ""].includes(stripped)) return false;
  const comment = /\s+#\s/.exec(stripped);
  const valuePart = comment ? stripped.slice(0, comment.index) : stripped;
  if (valuePart.includes(": ")) return true;
  return startsWithUnbalancedQuotedPhrase(valuePart);
}

/**
 * True for a scalar like `"foo" bar`.
 *
 * The value as a whole is not a quoted scalar, but its leading quote makes the parser try
 * to read one. Quoting the whole thing and escaping the inner quotes is the least invasive
 * fix.
 */
function startsWithUnbalancedQuotedPhrase(value: string): boolean {
  const first = value[0];
  if (value.length < 2 || (first !== '"' && first !== "'")) return false;
  return !value.endsWith(first) && value.slice(1).includes(first);
}

/**
 * Wrap a value in double quotes, leaving any trailing comment outside them.
 *
 * The whitespace before a comment is carried over exactly rather than normalized to one
 * space. Collapsing it is a restyling change on a line this pass was only asked to quote,
 * and a fix that quietly reformats what it touches is how a one-scalar diff becomes a
 * reviewable-looking whole-file one.
 */
function quoteValue(value: string): string {
  const stripped = value.trim();
  const comment = /(\s+#\s.*)$/.exec(stripped);
  const valuePart = comment ? stripped.slice(0, comment.index) : stripped;
  const commentPart = comment ? (comment[1] as string) : "";
  const escaped = valuePart.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  return `"${escaped}"${commentPart}`;
}

/**
 * Repair one YAML region: the frontmatter block, or a whole pure-yaml document.
 *
 * Parses first and returns unchanged when the text is already portable, so a valid
 * document is never rewritten. When the parse fails for a reason quoting could plausibly
 * address, quotes the offending scalars and re-parses. A repair that does not produce a
 * portable document is discarded, and the original failure is what the caller reports.
 */
export function repairYamlText(text: string): RepairResult {
  let originalCode: string;
  let originalMessage: string;
  try {
    parsePortableYaml(text);
    return result({ ok: true, text });
  } catch (error) {
    if (!(error instanceof PortableInputError)) throw error;
    if (NOT_REPAIRABLE.has(error.code)) {
      return result({ errorCode: error.code, errorMessage: error.message });
    }
    originalCode = error.code;
    originalMessage = error.message;
  }

  const repairedLines: string[] = [];
  const records: RepairRecord[] = [];
  for (const line of text.split("\n")) {
    const match = MAPPING_LINE.exec(line);
    const groups = match?.groups;
    if (groups && valueNeedsQuoting(groups.value as string)) {
      repairedLines.push(`${groups.indent}${groups.key}: ${quoteValue(groups.value as string)}`);
      records.push(record([groups.key as string], `quoted the value of '${groups.key}'`));
      continue;
    }
    repairedLines.push(line);
  }

  if (records.length === 0) {
    return result({ errorCode: originalCode, errorMessage: originalMessage });
  }

  const repaired = repairedLines.join("\n");
  try {
    parsePortableYaml(repaired);
  } catch {
    // Quoting did not make the document portable. Report what was actually wrong rather
    // than the residue of a failed guess.
    return result({ errorCode: originalCode, errorMessage: originalMessage });
  }
  return result({ ok: true, changed: true, text: repaired, records });
}

/**
 * Repair one artifact on disk.
 *
 * For `frontmatter-md` only the fenced block is touched and the body is spliced back by
 * offset, so it survives byte-for-byte. For `pure-yaml` the whole document is the region.
 *
 * `write: false` reports what would change without touching the file, which is what
 * `--check-repair` runs on.
 *
 * `text` on the result is the full document, repaired or not, so a caller that is about to
 * conform and validate does not read the file a second time.
 */
export function repairArtifact(
  path: string,
  options: { profile?: SchemaProfile; write?: boolean } = {},
): RepairResult {
  const profile = options.profile ?? "frontmatter-md";
  const write = options.write ?? true;

  let content: string;
  try {
    content = readUtf8(path);
  } catch (error) {
    if (error instanceof PortableInputError) {
      return result({ errorCode: error.code, errorMessage: error.message });
    }
    // A filesystem failure (missing file, permissions) carries an errno code; that is the
    // `artifact_unreadable` class, mirroring Python's `except OSError`. Anything else is
    // a programming error and must crash rather than be reclassified as a bad artifact.
    if (isErrnoException(error)) {
      return result({ errorCode: "artifact_unreadable", errorMessage: error.message });
    }
    throw error;
  }

  // The line scan below works in `\n`; a CRLF document is normalized for the duration and
  // restored on the way out, so repairing one scalar does not silently convert every line
  // ending in the file.
  const crlf = content.includes("\r\n");
  const normalized = crlf ? content.replaceAll("\r\n", "\n") : content;

  let inner: RepairResult;
  let repairedDocument: string | null;
  if (profile === "pure-yaml") {
    inner = repairYamlText(normalized);
    repairedDocument = inner.text;
  } else {
    const split = splitFrontmatter(normalized);
    if (split === null) {
      // No frontmatter is not a repair failure; it is a validation verdict, and
      // validation owns reporting it.
      return result({ ok: true, text: content });
    }
    inner = repairYamlText(split.metadataText);
    // Splice by offset: everything outside the metadata region — the opening fence, the
    // closing fence, and the whole body — comes back verbatim rather than re-synthesized,
    // so a repair cannot restyle anything it did not fix.
    repairedDocument =
      inner.text === null
        ? null
        : normalized.slice(0, split.metadataOffset) +
          inner.text +
          normalized.slice(split.metadataEnd, split.bodyOffset) +
          normalized.slice(split.bodyOffset);
  }

  if (repairedDocument !== null && crlf) {
    repairedDocument = repairedDocument.replaceAll("\n", "\r\n");
  }

  if (!inner.changed) {
    return result({
      ok: inner.ok,
      text: inner.ok ? repairedDocument : content,
      errorCode: inner.errorCode,
      errorMessage: inner.errorMessage,
    });
  }

  if (write && repairedDocument !== null) {
    writeArtifactText(path, repairedDocument);
  }
  return result({ ok: true, changed: true, text: repairedDocument, records: inner.records });
}

/** A Node filesystem error: an `Error` carrying a string `code` like ENOENT or EACCES. */
function isErrnoException(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && typeof (error as NodeJS.ErrnoException).code === "string";
}
