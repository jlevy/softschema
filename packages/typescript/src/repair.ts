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
  findNonPortableCharacter,
  PortableInputError,
  parsePortableYaml,
  portableEscape,
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
/** `code` for a plain scalar quoted because YAML read structure in it. */
const YAML_QUOTED_SCALAR = "yaml_quoted_scalar";

/**
 * `code` for a value rewritten as a double-quoted scalar to escape a rejected character.
 *
 * The portable preflight refuses a raw U+0085, U+2028, U+2029, control character or lone
 * carriage return anywhere in the YAML text. Inside a single-line value the fix is
 * mechanical and meaning-preserving: a serializer would have written the escape, and the
 * decoded value is exactly what YAML 1.2 gives the raw text. The character itself is never
 * replaced by a guess at what was meant (a mis-decoded ellipsis stays a U+0085, now visible
 * in the record); and a rejected character in a key, a comment or a block scalar has no
 * such rewrite, so those stay parse errors.
 */
const YAML_ESCAPED_CHARACTER = "yaml_escaped_character";

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
// `[^\n]` rather than `.`: in JavaScript `.` also stops at U+2028, U+2029 and `\r`, which
// Python's `.` does not, and a line holding one of those is exactly what the escaping rule
// below must be able to see.
const MAPPING_LINE = /^(?<indent>[ \t]*)(?<key>[A-Za-z0-9_.-]+): (?<value>[^\n]+)$/;

/**
 * A line that opens a block scalar (`key: |`, `key: >-`, `- |2`, with an optional comment):
 * its content is every following line indented deeper than the opener, and the escaping
 * rule must not touch those lines even when one happens to look like `key: value`.
 */
const BLOCK_SCALAR_OPENER =
  /^(?<indent>[ \t]*)(?:[A-Za-z0-9_.-]+:|-)[ \t]+[|>][-+0-9]*[ \t]*(?:#[^\n]*)?$/;
const TRAILING_COMMENT = /^[ \t]*(?:#[^\n]*)?$/;

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

function record(
  path: (string | number)[],
  message: string,
  code: string = YAML_QUOTED_SCALAR,
): RepairRecord {
  return { kind: REPAIR_KIND, code, path, message };
}

function indentOf(line: string): number {
  return line.length - line.replace(/^[ \t]+/u, "").length;
}

/**
 * Index of the quote that closes the scalar opened at `text[0]`, or null.
 *
 * Inside double quotes a backslash escapes the next character; inside single quotes the
 * only escape is a doubled quote.
 */
function closingQuote(text: string, quote: string): number | null {
  let index = 1;
  while (index < text.length) {
    const char = text[index];
    if (quote === '"' && char === "\\") {
      index += 2;
      continue;
    }
    if (char === quote) {
      if (quote === "'" && text[index + 1] === "'") {
        index += 2;
        continue;
      }
      return index;
    }
    index += 1;
  }
  return null;
}

function isRejected(char: string): boolean {
  return findNonPortableCharacter(char) !== null;
}

function escapeCharacters(text: string): string {
  return [...text].map((char) => (isRejected(char) ? portableEscape(char) : char)).join("");
}

/**
 * Rewrite a single-line value holding a rejected character as a double-quoted scalar.
 *
 * Returns the new value text and the characters escaped, or null when the value has nothing
 * to escape or is not one of the three shapes this rule can rewrite exactly: a plain
 * scalar, a complete single-quoted scalar, or a complete double-quoted scalar, each
 * optionally followed by a comment. Whitespace before a comment is kept as written. The
 * decoded value is unchanged in every case: the plain and single-quoted forms are
 * re-expressed with the same content, and in the double-quoted form only the raw
 * characters are replaced, so escapes the author already wrote stay as they are.
 */
function escapeValue(value: string): { text: string; escaped: string[] } | null {
  if (findNonPortableCharacter(value) === null) return null;
  // Only ASCII blanks are trimmed, the same set Python's `strip(" \t")` takes.
  const stripped = value.replace(/^[ \t]+/u, "").replace(/[ \t]+$/u, "");
  let body: string;
  let rest: string;
  const quote = stripped[0];
  if (quote === '"' || quote === "'") {
    const end = closingQuote(stripped, quote);
    if (end === null || !TRAILING_COMMENT.test(stripped.slice(end + 1))) return null;
    body = stripped.slice(1, end);
    rest = stripped.slice(end + 1);
    if (quote === "'") {
      body = body.replaceAll("''", "'").replaceAll("\\", "\\\\").replaceAll('"', '\\"');
    }
  } else {
    const comment = /([ \t]+#[^\n]*)$/u.exec(stripped);
    body = comment ? stripped.slice(0, comment.index) : stripped;
    rest = comment ? (comment[1] as string) : "";
    body = body.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
  }
  const escaped = [...new Set([...body].filter(isRejected))].sort(
    (a, b) => (a.codePointAt(0) ?? 0) - (b.codePointAt(0) ?? 0),
  );
  if (escaped.length === 0) return null; // the rejected character sits in the comment
  return { text: `"${escapeCharacters(body)}"${rest}`, escaped };
}

function escapeDetail(key: string, escaped: string[]): string {
  const listed = escaped
    .map(
      (char) =>
        `#x${(char.codePointAt(0) ?? 0).toString(16).padStart(4, "0")} as "${portableEscape(char)}"`,
    )
    .join(", ");
  return `escaped ${listed} in the value of '${key}'`;
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
  let blockIndent: number | null = null;
  for (const line of text.split("\n")) {
    if (blockIndent !== null) {
      // Inside a block scalar: content runs while lines are blank or indented deeper than
      // the opener. The escaping rule leaves it alone, whatever it looks like.
      if (line.replace(/[ \t]+/gu, "") === "" || indentOf(line) > blockIndent) {
        repairedLines.push(line);
        continue;
      }
      blockIndent = null;
    }
    if (BLOCK_SCALAR_OPENER.test(line)) {
      blockIndent = indentOf(line);
      repairedLines.push(line);
      continue;
    }
    const match = MAPPING_LINE.exec(line);
    const groups = match?.groups;
    if (groups) {
      const key = groups.key as string;
      const value = groups.value as string;
      const escaped = escapeValue(value);
      if (escaped !== null) {
        repairedLines.push(`${groups.indent}${key}: ${escaped.text}`);
        records.push(record([key], escapeDetail(key, escaped.escaped), YAML_ESCAPED_CHARACTER));
        continue;
      }
      if (valueNeedsQuoting(value)) {
        repairedLines.push(`${groups.indent}${key}: ${quoteValue(value)}`);
        records.push(record([key], `quoted the value of '${key}'`));
        continue;
      }
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
 * `repair --dry-run` and `repair --check` run on.
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
