/** Portable YAML input shared by artifact and schema reads.
 *
 * The input, node, and scalar ceilings were removed. They only answered whether a
 * hostile document could exhaust the parser, and softschema reads artifacts its own
 * callers just wrote. The portable-value rules here stay, because they are what makes a
 * document mean the same thing in both runtimes.
 */
import { readFileSync } from "node:fs";
import { writeFileSync } from "atomically";
import {
  isAlias,
  isCollection,
  isMap,
  isPair,
  isScalar,
  Parser,
  parseDocument,
  Scalar,
  visit,
} from "yaml";

/** Largest integer that survives a round trip through a JS number. */
const MAX_SAFE_INTEGER = 9_007_199_254_740_991;

/** Simultaneously open collections, including the root.
 *
 * A portability rule rather than a resource guard, and the reason it outlived the three
 * ceilings above. Left to the host, V8 parses past depth 10,000 while CPython's default
 * recursion limit stops the Python constructor around 491, so any document between those
 * bounds would be valid here and a crash there. Keep this value identical to `MAX_DEPTH`
 * in the Python `_portable` module; the shared depth vectors check that they agree.
 */
const MAX_DEPTH = 64;

export class PortableInputError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

/** A leading byte order mark, which decoding removes rather than keeps as a character. */
const BOM = "\uFEFF";

/**
 * Read one UTF-8 artifact, dropping a leading byte order mark.
 *
 * The BOM has to go, and it has to go here, because this is the one function both runtimes
 * route every artifact and schema read through. `TextDecoder`'s default `ignoreBOM: false`
 * already strips it, so the explicit check below is a no-op today; it is written out
 * anyway, the same way Python's `read_utf8` writes it out, because that default is the
 * only thing holding the two runtimes together and it is invisible at the call site.
 * Swapping in `readFileSync(path, "utf8")` — which keeps the mark — would silently
 * reintroduce the divergence this replaced.
 *
 * That divergence was real: the fence scan and the reader both compare a first line
 * against `---`, and `"\uFEFF---"` is not `"---"`, so Python called a BOM-prefixed
 * artifact fenceless while TypeScript read it without complaint. Reporting that document
 * as having no frontmatter is the diagnostic this codebase exists to avoid — the block is
 * plainly there. Only position zero is examined; a U+FEFF anywhere else is a real
 * character and survives.
 */
export function readUtf8(path: string): string {
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(readFileSync(path));
  } catch (error) {
    if (error instanceof TypeError) {
      throw new PortableInputError(
        "invalid_utf8",
        `${documentLabel(path)}: input is not valid UTF-8`,
      );
    }
    throw error;
  }
  return text.startsWith(BOM) ? text.slice(1) : text;
}

/**
 * `error` from parsing the text of `path`, with the file named first.
 *
 * `readUtf8` names the file in a decoding failure itself, and the parser, which sees only
 * text, names nothing. A caller that reads a file by path labels a parse failure here and
 * reports either error's message as it stands, so the name appears exactly once. Mirrors
 * Python's `named_parse_error`.
 */
export function namedParseError(path: string, error: PortableInputError): PortableInputError {
  return new PortableInputError(error.code, `${documentLabel(path)}: ${error.message}`);
}

/** Read and parse one YAML file, naming the file once in any failure. */
export function readYamlFile(path: string): unknown {
  const text = readUtf8(path);
  try {
    return parsePortableYaml(text);
  } catch (error) {
    if (error instanceof PortableInputError) throw namedParseError(path, error);
    throw error;
  }
}

// biome-ignore lint/suspicious/noControlCharactersInRegex: the control characters are the subject
const CONTROL_CHARACTER = /[\x00-\x1f\x7f-\x9f]/gu;

/**
 * The backticked document name every message that names a document begins with.
 *
 * C0 and C1 control characters and DEL in the name are written as `#xHHHH`, the notation
 * the preflight uses for a rejected character. A path is untrusted input like the artifact
 * it names: a filename carrying an escape sequence would otherwise reach stderr raw, where
 * a terminal acts on it (an OSC title or clipboard write, a line cleared and overwritten, a
 * forged second diagnostic line). JSON output escapes the string on its own, so only the
 * human-readable channel needed this. Keep the rule identical to `document_label` in
 * `_portable.py`.
 */
export function documentLabel(path: string): string {
  const name = path.replace(
    CONTROL_CHARACTER,
    (char) => `#x${char.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );
  return `\`${name}\``;
}

/**
 * A raw character the two YAML engines read differently.
 *
 * The class is YAML 1.2 `c-printable` with the three Unicode line separators taken out,
 * plus a carriage return that does not begin a `\r\n` sequence. ruamel rejects everything
 * outside `c-printable` (its `Reader.NON_PRINTABLE`) and the `yaml` package reads it as
 * content; for U+0085, U+2028 and U+2029 ruamel follows YAML 1.1 and treats them as line
 * breaks, folding a NEL in a flow scalar to a space and breaking a block scalar or a
 * comment into a parse error, while the `yaml` package again reads them as content. A lone
 * carriage return is the same shape: a YAML line break for ruamel, so a CR-only document
 * is many lines and a CR inside a flow scalar folds to a space, while the `yaml` package
 * reads it as content and sees one long line. Neither reading can be reproduced in the
 * other engine, so the portable rule is to accept none of them raw. Every one of them can
 * be written as a double-quoted escape (`"\f"`, `"\x7f"`, `"\N"`, `"\L"`, `"\P"`,
 * `"\r"`), which both engines decode identically. Keep this class identical to
 * `_NON_PORTABLE_CHARACTER` in `_portable.py`.
 */
const NON_PORTABLE_CHARACTER =
  /[^\t\n\r\x20-\x7e\xa0-\u2027\u202a-\ud7ff\ue000-\ufffd\u{10000}-\u{10ffff}]|\r(?!\n)/u;

const NAMED_ESCAPES = new Map<number, string>([
  [0x00, "\\0"],
  [0x07, "\\a"],
  [0x08, "\\b"],
  [0x0b, "\\v"],
  [0x0c, "\\f"],
  [0x0d, "\\r"],
  [0x1b, "\\e"],
  [0x85, "\\N"],
  [0x2028, "\\L"],
  [0x2029, "\\P"],
]);

/**
 * The double-quoted YAML escape for one character, as both engines decode it.
 *
 * YAML 1.2 names the common controls and the three line separators; everything else takes
 * the fixed-width `\xHH`, `\uHHHH` or `\UHHHHHHHH` form. Used in the preflight message and
 * by `repair` when it rewrites a rejected character. Mirrors the Python `portable_escape`.
 */
export function portableEscape(char: string): string {
  const code = char.codePointAt(0) ?? 0;
  const named = NAMED_ESCAPES.get(code);
  if (named !== undefined) return named;
  if (code <= 0xff) return `\\x${code.toString(16).padStart(2, "0")}`;
  if (code <= 0xffff) return `\\u${code.toString(16).padStart(4, "0")}`;
  return `\\U${code.toString(16).padStart(8, "0")}`;
}

/** The first raw character in `text` that `checkPortableText` rejects, with its index. */
export function findNonPortableCharacter(text: string): { char: string; index: number } | null {
  const match = NON_PORTABLE_CHARACTER.exec(text);
  return match === null ? null : { char: match[0], index: match.index };
}

const EVERY_NON_PORTABLE_CHARACTER = new RegExp(NON_PORTABLE_CHARACTER.source, "gu");

/**
 * Replace every raw character the preflight rejects with its double-quoted escape.
 *
 * Only correct for text in which each such character sits inside a double-quoted scalar;
 * the schema writer arranges that before calling this. The Python writer needs no
 * counterpart, because ruamel escapes these characters itself once the style is `"`.
 */
export function escapeNonPortableCharacters(text: string): string {
  return findNonPortableCharacter(text) === null
    ? text
    : text.replace(EVERY_NON_PORTABLE_CHARACTER, (char) => portableEscape(char));
}

/**
 * Reject the first raw character in `text` that the engines would read differently.
 *
 * Runs before the engine sees the text, on the whole YAML text the reader was handed: the
 * frontmatter block or the entire pure-yaml document, comments and keys included. The line
 * and column are counted within that text, in code points, as the engines count them; the
 * frontmatter reader adds the fence offset so the message names a line of the file.
 * Raising here, with one message in both runtimes, is what keeps a mis-decoded cp1252
 * ellipsis (which arrives as U+0085) from silently becoming a space in one runtime and
 * staying a character in the other. Mirrors the Python `check_portable_text`.
 *
 * The position is counted with index loops rather than `match`/spread: on the error path
 * those would materialize every newline and every code point of the offending line, a
 * several-fold memory amplification on a large single-line input that a library host
 * validating untrusted uploads would pay at the worst moment.
 */
export function checkPortableText(text: string): void {
  const match = NON_PORTABLE_CHARACTER.exec(text);
  if (match === null) return;
  const { line, column } = textPosition(text, match.index);
  const char = match[0];
  const codePoint = (char.codePointAt(0) ?? 0).toString(16).padStart(4, "0");
  const advice =
    char === "\r"
      ? 'end lines with "\\n", or write it as "\\r" inside a double-quoted scalar'
      : `write it as "${portableEscape(char)}" inside a double-quoted scalar`;
  throw new PortableInputError(
    "yaml_parse_error",
    `unacceptable character #x${codePoint} at line ${line}, column ${column}: ` +
      `non-printable and line separator characters are not allowed as raw text; ${advice}`,
  );
}

/** The one-based line and code-point column of `index` in `text`, without allocating. */
function textPosition(text: string, index: number): { line: number; column: number } {
  let line = 1;
  let lineStart = 0;
  for (let at = text.indexOf("\n"); at !== -1 && at < index; at = text.indexOf("\n", at + 1)) {
    line += 1;
    lineStart = at + 1;
  }
  let column = 1;
  for (let at = lineStart; at < index; at += 1) {
    const unit = text.charCodeAt(at);
    if (unit >= 0xd800 && unit <= 0xdbff) at += 1;
    column += 1;
  }
  return { line, column };
}

/**
 * Token types whose own source may hold a raw tab in both engines. A quoted scalar's `end`
 * (the spacing and comment after its closing quote) is still walked.
 */
const TAB_TOLERANT_TOKENS = new Set(["double-quoted-scalar", "single-quoted-scalar", "comment"]);

/** The tokens that close a flow collection, after which block context resumes. */
const FLOW_END_TOKENS = new Set(["flow-seq-end", "flow-map-end"]);

/**
 * Reject a raw tab where ruamel rejects one: in a plain scalar, or as spacing in block
 * context (after a key's colon, before a comment, at the end of a value, on a blank line,
 * after a sequence dash, after a block scalar header, after a quoted scalar's closing
 * quote or a flow collection's closing bracket). YAML 1.2 allows every one of these and the `yaml` package reads them, but
 * ruamel's scanner refuses them all ("found character '\t' that cannot start any token",
 * or "expected a comment or a line break" after a block scalar header), so a tab in those
 * places read in one runtime and failed in the other. A tab inside a quoted scalar, a block
 * scalar's content, or a comment, and a tab as spacing inside a flow collection (between
 * its brackets), is fine for both and is left alone. The check walks the `yaml` CST, which
 * keeps the exact source of every token, and runs after the engine parse so an engine error
 * is reported first, as it would be in Python. Tab indentation is already an engine error in
 * both.
 */
function checkPlainTabs(text: string): void {
  if (!text.includes("\t")) return;
  let offender = -1;
  const walk = (node: unknown, inFlow: boolean): void => {
    if (node === null || typeof node !== "object") return;
    if (Array.isArray(node)) {
      for (const item of node) walk(item, inFlow);
      return;
    }
    const token = node as { type?: unknown; offset?: unknown; source?: unknown };
    const record = node as Record<string, unknown>;
    if (token.type === "block-scalar") {
      // The content may hold tabs; the header line (`|`, its indicators, the spacing and
      // comment after them, kept in `props`) is block-context spacing like any other.
      walk(record.props, inFlow);
      return;
    }
    if (token.type === "flow-collection") {
      // Only the tokens between the brackets are flow spacing. `end` holds the closing
      // bracket and then whatever follows it on the line, which is back in the enclosing
      // context: block context unless this collection sits inside another one.
      walk(record.start, true);
      walk(record.items, true);
      let closed = false;
      for (const part of Array.isArray(record.end) ? record.end : []) {
        walk(part, inFlow || !closed);
        const type = (part as { type?: unknown } | null)?.type;
        if (typeof type === "string" && FLOW_END_TOKENS.has(type)) closed = true;
      }
      return;
    }
    if (
      typeof token.source === "string" &&
      typeof token.offset === "number" &&
      !(typeof token.type === "string" && TAB_TOLERANT_TOKENS.has(token.type)) &&
      !(token.type === "space" && inFlow)
    ) {
      const at = token.source.indexOf("\t");
      if (at !== -1 && (offender === -1 || token.offset + at < offender)) {
        offender = token.offset + at;
      }
    }
    for (const part of ["start", "key", "sep", "value", "end", "items", "props"]) {
      if (part in record) walk(record[part], inFlow);
    }
  };
  for (const document of new Parser().parse(text)) walk(document, false);
  if (offender === -1) return;
  const { line, column } = textPosition(text, offender);
  throw new PortableInputError(
    "yaml_parse_error",
    `unacceptable tab character at line ${line}, column ${column}: ` +
      "a raw tab in a plain scalar or as block-context spacing is read by only one YAML engine; " +
      'write the value as a quoted scalar ("\\t")',
  );
}

/**
 * The plain scalars ruamel's YAML 1.2 resolver reads as a float or an int. It still accepts
 * YAML 1.1 spellings: `_` separators, `0b` binary, signed `0x` and `0o`, and an exponent
 * after a bare `.5` only when it is signed. Mirrors Python's `_RUAMEL_NUMBER`.
 */
const RUAMEL_NUMBER = new RegExp(
  "^(?:" +
    [
      "[-+]?[0-9][0-9_]*\\.[0-9_]*(?:[eE][-+]?[0-9]+)?",
      "[-+]?[0-9][0-9_]*[eE][-+]?[0-9]+",
      "[-+]?\\.[0-9_]+(?:[eE][-+][0-9]+)?",
      "[-+]?\\.(?:inf|Inf|INF)",
      "\\.(?:nan|NaN|NAN)",
      "[-+]?0b[0-1_]+",
      "[-+]?0o?[0-7_]+",
      "[-+][0-9_]+",
      "[0-9][0-9_]*",
      "[-+]?0x[0-9a-fA-F_]+",
    ].join("|") +
    ")$",
  "u",
);

/** The plain scalars the YAML 1.2 core schema, and so the `yaml` package, reads as numbers. */
const CORE_NUMBER = new RegExp(
  "^(?:" +
    [
      "[-+]?(?:\\.[0-9]+|[0-9]+(?:\\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?",
      "[-+]?\\.(?:inf|Inf|INF)",
      "\\.(?:nan|NaN|NAN)",
      "0o[0-7]+",
      "0x[0-9a-fA-F]+",
    ].join("|") +
    ")$",
  "u",
);

/**
 * Reject a plain scalar that one engine reads as a number and the other as a string.
 *
 * `1_000`, `0b101`, `-0x10` and `1_0.5` are numbers to ruamel and strings here; `.5e3` is
 * the reverse. Both runtimes would accept the document with different values, and neither
 * reading can be reproduced in the other engine, so neither is portable. Mirrors Python's
 * `_check_number_form`.
 */
function checkNumberForm(text: string, source: string, offset: number): void {
  if (!/^[-+.0-9]/u.test(source)) return;
  if (RUAMEL_NUMBER.test(source) === CORE_NUMBER.test(source)) return;
  const { line, column } = textPosition(text, offset);
  throw new PortableInputError(
    "yaml_unsupported_scalar",
    `plain scalar \`${source}\` at line ${line}, column ${column} is a number to one YAML ` +
      "engine and a string to the other; write the number in YAML 1.2 core form " +
      "(such as 1000, 0x10, 0o17, 1.5e3) or quote it to keep it a string",
  );
}

/**
 * Reject a `%YAML` directive other than `%YAML 1.2`, and any directive but `%TAG`.
 *
 * Under `%YAML 1.1` both engines switch to a YAML 1.1 schema, and the two schemas differ:
 * `08` is a string to ruamel and the number 8 here, and a date is a string there and a
 * host `Date` here. ruamel fails on `%YAML 1.0` and `1.3`, and it ignores an unknown
 * directive this engine refuses. Runs before the parse, so the verdict does not depend on
 * which engine's complaint would come first. Mirrors Python's `_check_directives`.
 */
function checkDirectives(text: string): void {
  if (!/(?:^|[\r\n])%/u.test(text)) return;
  for (const token of new Parser().parse(text)) {
    if (token.type !== "directive") continue;
    const [name = "", version = ""] = token.source.slice(1).split(/[ \t]+/u);
    const parts = /^([0-9]+)\.([0-9]+)$/u.exec(version);
    if (
      name === "TAG" ||
      (name === "YAML" && parts && Number(parts[1]) === 1 && Number(parts[2]) === 2)
    ) {
      continue;
    }
    const { line, column } = textPosition(text, token.offset);
    const where = `line ${line}, column ${column}`;
    throw new PortableInputError(
      "yaml_parse_error",
      name === "YAML"
        ? `unsupported directive \`%YAML ${version}\` at ${where}: softschema reads YAML 1.2, ` +
            "and the two YAML engines read a document under another version differently; " +
            "remove the directive or write `%YAML 1.2`"
        : `unknown directive \`%${name}\` at ${where}: one YAML engine ignores it and the ` +
            "other refuses it; remove it",
    );
  }
}

/** Every object node of a CST, visited without recursion (a CST can be deeper than the stack). */
function forEachCstRecord(
  tokens: Iterable<unknown>,
  visitor: (record: Record<string, unknown>, parentType: unknown) => void,
): void {
  const stack: Array<[unknown, unknown]> = [];
  for (const token of tokens) stack.push([token, undefined]);
  while (stack.length > 0) {
    const [node, parentType] = stack.pop() as [unknown, unknown];
    if (node === null || typeof node !== "object") continue;
    if (Array.isArray(node)) {
      for (const item of node) stack.push([item, parentType]);
      continue;
    }
    const record = node as Record<string, unknown>;
    visitor(record, parentType);
    for (const part of ["start", "key", "sep", "value", "end", "items", "props"]) {
      if (part in record) stack.push([record[part], record.type]);
    }
  }
}

/**
 * Whether the flow-collection entry whose key starts at an offset is an explicit `? key`,
 * from one CST parse of the document made the first time a key asks.
 *
 * Only a key about to be refused asks, so a document that passes pays nothing; and the
 * parse is made once per document, not once per key, so a flow mapping of many explicit
 * keys is still linear.
 */
function explicitKeyIndex(text: string): (offset: number) => boolean {
  let offsets: Set<number> | null = null;
  return (offset) => {
    if (offsets === null) {
      const found = new Set<number>();
      forEachCstRecord(new Parser().parse(text), (record) => {
        const key = record.key as { offset?: unknown } | null | undefined;
        if (
          typeof key?.offset === "number" &&
          Array.isArray(record.start) &&
          record.start.some((token) => (token as { type?: unknown }).type === "explicit-key-ind")
        ) {
          found.add(key.offset);
        }
      });
      offsets = found;
    }
    return offsets.has(offset);
  };
}

/** Where text may sit that the `yaml` package composes into no value (see below). */
const MAYBE_DROPPED = /[!&]|(?:^|[\s[{,])\?(?=\s|$)/mu;

/**
 * Reject content the `yaml` package parses and then leaves out of the document.
 *
 * A mapping entry whose properties (`!`, `&`) or value come with no `:` indicator, as in
 * `{"a" : b , ""!}` or `- ? k` followed by an indented `- x`, composes to a document with
 * that text gone and no error, where ruamel refuses it. Both now refuse it. Only a text
 * holding `!`, `&` or an explicit-key `?` can have such an entry, so others skip the extra
 * CST pass.
 */
function checkDroppedContent(text: string): void {
  if (!MAYBE_DROPPED.test(text)) return;
  let dropped = -1;
  forEachCstRecord(new Parser().parse(text), (record, parentType) => {
    if (dropped !== -1 || (parentType !== "block-map" && parentType !== "flow-collection")) return;
    if (!("key" in record) && !("explicitKey" in record)) return;
    const sep = Array.isArray(record.sep)
      ? (record.sep as Array<{ type?: unknown; offset?: unknown }>)
      : [];
    if (sep.some((token) => token.type === "map-value-ind")) return;
    const value = record.value as { offset?: unknown } | null | undefined;
    const property = sep.find((token) => token.type === "tag" || token.type === "anchor");
    const at = typeof value?.offset === "number" ? value.offset : property?.offset;
    if (typeof at === "number") dropped = at;
  });
  if (dropped === -1) return;
  const { line, column } = textPosition(text, dropped);
  throw new PortableInputError(
    "yaml_parse_error",
    `content at line ${line}, column ${column} belongs to no value: a mapping entry has ` +
      "properties or a value but no ':' before them, which one YAML engine drops and the " +
      "other refuses",
  );
}

/**
 * Where the first collection that would make more than `MAX_DEPTH` open at once starts, or
 * null. Counts as Python's event pass does, so an empty `[]` that is the 65th one open is
 * over the limit in both runtimes.
 *
 * Iterative, in document order, and never deeper than the limit, so a document the engine
 * gave up on thousands of levels down costs no more than one at the limit.
 */
function firstTooDeep(document: ReturnType<typeof parseDocument>): number | null {
  // Each entry is a node, how many collections hold it, and where its parent starts.
  const stack: Array<[unknown, number, number]> = [[document.contents, 0, 0]];
  while (stack.length > 0) {
    const [node, depth, fallback] = stack.pop() as [unknown, number, number];
    if (node === null || typeof node !== "object") continue;
    const start = (node as { range?: readonly number[] | null }).range?.[0] ?? fallback;
    if (isPair(node)) {
      stack.push([node.value, depth, start], [node.key, depth, start]);
    } else if (isCollection(node)) {
      if (depth >= MAX_DEPTH) return start;
      for (let index = node.items.length - 1; index >= 0; index -= 1) {
        stack.push([node.items[index], depth + 1, start]);
      }
    }
  }
  return null;
}

/** Errors the `yaml` package reports about a block mapping key before checking it is unique. */
const KEY_STAGE_ERRORS = new Set<string>([
  "BAD_INDENT",
  "BLOCK_AS_IMPLICIT_KEY",
  "MULTILINE_IMPLICIT_KEY",
]);

/**
 * The duplicate key the `yaml` package would have reported first, or null.
 *
 * One pass with a set per mapping; the package's own check (`uniqueKeys: true`) compares
 * every key with every earlier one, which is quadratic in a mapping's width. Keys are
 * compared as it compares them: two scalars with the same value. `at` is where it reports
 * the duplicate (the key); `emitted` is where in its composition order it reports it,
 * which decides whether a parse error elsewhere comes first: a block mapping checks a key
 * before composing its value, a flow mapping after.
 */
function firstDuplicateKey(
  document: ReturnType<typeof parseDocument>,
): { at: number; emitted: number; block: boolean } | null {
  let first: { at: number; emitted: number; block: boolean } | null = null;
  // Iterative, and never past the depth limit: anything deeper starts after an engine
  // error that is reported instead (or the limit would have been), and a document the
  // engine gave up on can be thousands of levels deep.
  const stack: Array<[unknown, number]> = [[document.contents, 0]];
  while (stack.length > 0) {
    const [node, depth] = stack.pop() as [unknown, number];
    if (isPair(node)) {
      stack.push([node.key, depth], [node.value, depth]);
      continue;
    }
    if (!isCollection(node) || depth >= MAX_DEPTH) continue;
    if (isMap(node)) {
      const seen = new Set<unknown>();
      for (const pair of node.items) {
        if (!isScalar(pair.key)) continue;
        const value = pair.key.value;
        // The package compares with `===`, so two `.nan` keys are not duplicates.
        if (typeof value === "number" && Number.isNaN(value)) continue;
        const at = pair.key.range?.[0];
        if (seen.has(value) && typeof at === "number") {
          const item = pair.value as { range?: readonly number[] | null } | null;
          const emitted = node.flow === true ? (item?.range?.[2] ?? pair.key.range?.[2] ?? at) : at;
          if (first === null || emitted < first.emitted) first = { at, emitted, block: !node.flow };
        }
        seen.add(value);
      }
    }
    for (const item of node.items) stack.push([item, depth + 1]);
  }
  return first;
}

/**
 * `message` with the position and source excerpt the `yaml` package appends to its own
 * errors (`prettifyError`), so a duplicate key reads exactly as it did when that package
 * found it.
 */
function describeAt(text: string, offset: number, message: string): string {
  const lineStarts = [0];
  for (let at = text.indexOf("\n"); at !== -1; at = text.indexOf("\n", at + 1)) {
    lineStarts.push(at + 1);
  }
  const position = (target: number): { line: number; col: number } => {
    let low = 0;
    let high = lineStarts.length;
    while (low < high) {
      const mid = (low + high) >> 1;
      if ((lineStarts[mid] as number) < target) low = mid + 1;
      else high = mid;
    }
    if (lineStarts[low] === target) return { line: low + 1, col: 1 };
    return { line: low, col: target - (lineStarts[low - 1] as number) + 1 };
  };
  const { line, col } = position(offset);
  const end = position(offset + 1);
  let described = `${message} at line ${line}, column ${col}`;
  let ci = col - 1;
  let lineStr = text
    .substring(lineStarts[line - 1] as number, lineStarts[line])
    .replace(/[\n\r]+$/u, "");
  if (ci >= 60 && lineStr.length > 80) {
    const trimStart = Math.min(ci - 39, lineStr.length - 79);
    lineStr = `…${lineStr.substring(trimStart)}`;
    ci -= trimStart - 1;
  }
  if (lineStr.length > 80) lineStr = `${lineStr.substring(0, 79)}…`;
  if (line > 1 && /^ *$/u.test(lineStr.substring(0, ci))) {
    let previous = text.substring(lineStarts[line - 2] as number, lineStarts[line - 1]);
    if (previous.length > 80) previous = `${previous.substring(0, 79)}…\n`;
    lineStr = previous + lineStr;
  }
  if (/[^ ]/u.test(lineStr)) {
    let count = 1;
    if (end.line === line && end.col > col) count = Math.max(1, Math.min(end.col - col, 80 - ci));
    described += `:\n\n${lineStr}\n${" ".repeat(ci)}${"^".repeat(count)}\n`;
  }
  return described;
}

/** Column of the innermost block collection holding a node, or 0 at the root. */
function blockColumn(text: string, path: readonly unknown[]): number {
  for (let index = path.length - 1; index >= 0; index -= 1) {
    const ancestor = path[index];
    if (isCollection(ancestor) && ancestor.flow !== true) {
      const start = ancestor.range?.[0];
      if (start === undefined) return 0;
      return start - (text.lastIndexOf("\n", start - 1) + 1);
    }
  }
  return 0;
}

/**
 * Reject a line of only spaces wider than an explicit block scalar indentation.
 *
 * With an indentation indicator the content is indented `parent + indicator` spaces, and
 * YAML 1.2 makes any further spaces on a line of only spaces content: `key: >1` followed by
 * a line of four spaces is `"   \n"` to ruamel, as the spec reads it, and `""` here.
 * Neither reading can be reproduced in the other engine, so the line is refused. The
 * scalar runs while lines are blank or indented to its content. Mirrors Python's
 * `_check_block_scalar_spaces`.
 */
function checkBlockScalarSpaces(text: string, offset: number, parent: number): void {
  const header = /[|>][-+]?([1-9])/uy;
  header.lastIndex = offset;
  const match = header.exec(text);
  if (match === null) return;
  const indent = parent + Number(match[1]);
  let lineStart = text.indexOf("\n", offset) + 1;
  while (lineStart > 0 && lineStart < text.length) {
    const next = text.indexOf("\n", lineStart);
    const lineEnd = next === -1 ? text.length : next;
    const line = text.slice(lineStart, lineEnd).replace(/\r$/u, "");
    if (/^ *$/u.test(line)) {
      if (line.length > indent) {
        const { line: number } = textPosition(text, lineStart);
        throw new PortableInputError(
          "yaml_parse_error",
          `line ${number} of only spaces is wider than the block scalar's explicit ` +
            `indentation (${indent}); the two YAML engines read its extra spaces ` +
            "differently; trim the line or drop the indentation indicator",
        );
      }
    } else if (line.length - line.trimStart().length < indent) {
      return;
    }
    lineStart = lineEnd + 1;
  }
}

/**
 * Reject a plain scalar in a flow collection that starts with `?` or `:`, or is a bare `-`.
 *
 * YAML 1.2, and this engine, make `?a` and `:a` plain scalars there; ruamel reads a `?`
 * glued to the entry as an explicit key (`[?a]` is `[{a: null}]` in Python and `['?a']`
 * here), and its reading of a leading `:` in a flow mapping depends on its scanner state. A bare `-` is a string to ruamel and an error here in a
 * sequence but a key in a mapping. Neither reading is portable. Mirrors Python's
 * `_check_flow_scalar`, which also refuses a flow plain scalar ending in `:`; this engine
 * reads that colon as a key indicator, which `checkFlowMappingKey` refuses.
 */
function checkFlowPlainScalar(
  text: string,
  source: string,
  offset: number,
  inMapping: boolean,
): void {
  const first = source.charAt(0);
  // A leading `:` reads the same (`[:a]` is `[':a']`) as a flow-sequence entry; as a key
  // or value of a flow mapping, ruamel's reading depends on its scanner state.
  if (!(first === "?" || (first === ":" && inMapping) || source === "-")) return;
  const { line, column } = textPosition(text, offset);
  throw new PortableInputError(
    "yaml_parse_error",
    `plain scalar \`${source}\` at line ${line}, column ${column} inside a flow collection ` +
      "starts with an indicator the two YAML engines read differently; quote it",
  );
}

/** The longest implicit key YAML allows, from the key's first character to its `:`. */
const IMPLICIT_KEY_LIMIT = 1024;

/**
 * Reject an implicit flow-mapping key that ruamel cannot read: one whose `:` is on a later
 * line than the key starts, or more than 1,024 characters after it. ruamel applies YAML's
 * implicit-key rule (one line, at most 1,024 characters) in flow mappings too and reports a
 * parse error; the `yaml` package applies it only in block mappings and flow-sequence
 * pairs, as YAML 1.2 does, and read such a key. So `{"<1,100 characters>": 1}` and
 * `{"a"\n: 1}` passed in one runtime and failed in the other. An explicit key (`? key`) has
 * no limit in either engine and is left alone. The distance is counted in code points, as
 * ruamel counts it.
 */
function checkFlowMappingKey(
  text: string,
  key: { range?: readonly number[] | null; type?: unknown },
  mapStart: number | undefined,
  explicitKeys: (offset: number) => boolean,
): void {
  const start = key.range?.[0];
  const end = key.range?.[1];
  if (start === undefined || end === undefined) return;
  let before = start - 1;
  while (before >= 0 && " \t\r\n".includes(text.charAt(before))) before -= 1;
  const explicit = text.charAt(before) === "?";
  // Only spacing, line breaks, and comments can sit between a key and its `:`.
  let colon = end;
  let lineBreak = false;
  while (colon < text.length) {
    const char = text.charAt(colon);
    if (char === " " || char === "\t") {
      colon += 1;
    } else if (char === "\n" || char === "\r") {
      lineBreak = true;
      colon += 1;
    } else if (char === "#") {
      while (colon < text.length && text.charAt(colon) !== "\n") colon += 1;
    } else {
      break;
    }
  }
  if (text.charAt(colon) !== ":") return;
  // A `:` with no space after it is part of a plain scalar to ruamel, and in a flow
  // sequence's implicit pair it is not a value indicator at all, so `[a:, b]` and `{a:, b}`
  // read differently there and `["a":1]` fails; only a `{…}` key that is not plain, as in
  // JSON's `{"a":1}`, reads the same in both.
  const after = text.charAt(colon + 1);
  if (
    after !== "" &&
    !" \t\r\n".includes(after) &&
    (key.type === Scalar.PLAIN || text.charAt(mapStart ?? -1) !== "{")
  ) {
    const { line, column } = textPosition(text, colon);
    throw new PortableInputError(
      "yaml_parse_error",
      `':' at line ${line}, column ${column} has no space after it inside a flow collection, ` +
        "which one YAML engine reads as a key indicator and the other as part of the scalar " +
        "or an error; quote the value, or write a space and a value after the colon",
    );
  }
  // An explicit key (`? key`) has no length or line limit in either engine.
  if (explicit) return;
  for (let at = start; at < end && !lineBreak; at += 1) {
    const unit = text.charCodeAt(at);
    if (unit === 0x0a || unit === 0x0d) lineBreak = true;
  }
  if (!lineBreak && colon - start <= IMPLICIT_KEY_LIMIT) return;
  let codePoints = 0;
  for (let at = start; at < colon; at += 1) {
    const unit = text.charCodeAt(at);
    if (unit < 0xdc00 || unit > 0xdfff) codePoints += 1;
  }
  if (!lineBreak && codePoints <= IMPLICIT_KEY_LIMIT) return;
  // The backward scan above misses a `?` with a comment after it; the CST does not.
  if (explicitKeys(start)) return;
  const { line, column } = textPosition(text, start);
  throw new PortableInputError(
    "yaml_parse_error",
    `implicit flow mapping key at line ${line}, column ${column}: ` +
      "its ':' must be on the line where the key starts and at most 1024 characters after " +
      "it, or one YAML engine cannot read it; shorten the key or keep it on one line",
  );
}

export function parsePortableYaml(input: string): unknown {
  checkPortableText(input);
  // A last line without a line break is still a line, and the engines read a block scalar
  // that ends the text without one differently: ruamel clips its final break and this
  // engine keeps it. Both readers parse the text with the break supplied, so `body: |` as
  // the last key reads `"…\n"` in both. Mirrors Python's `parse_yaml`.
  const text = input.length > 0 && !input.endsWith("\n") ? `${input}\n` : input;
  checkDirectives(text);
  let document: ReturnType<typeof parseDocument>;
  try {
    // `uniqueKeys: true` compares each key with every earlier key of its mapping, which is
    // quadratic in a mapping's width; duplicates are found below in one pass instead.
    document = parseDocument(text, { uniqueKeys: false });
  } catch (error) {
    if (error instanceof RangeError || String(error).includes("Maximum call stack size exceeded")) {
      throw new PortableInputError("yaml_limit", "YAML exceeds the depth limit");
    }
    throw error;
  }
  const firstError = document.errors[0];
  // Python's event pass stops at the first collection past the limit, before it looks for
  // duplicate keys and before any parse error later in the text; so does this. It also
  // keeps the walks below off a document nested thousands deep.
  const tooDeep = firstTooDeep(document);
  if (tooDeep !== null && (firstError === undefined || tooDeep < firstError.pos[0])) {
    throw new PortableInputError("yaml_limit", "YAML exceeds the depth limit");
  }
  const duplicate = firstDuplicateKey(document);
  if (
    duplicate !== null &&
    (firstError === undefined ||
      duplicate.emitted < firstError.pos[0] ||
      // A block mapping checks a key after the errors about the key itself and before
      // those about its value, all at the key's offset.
      (duplicate.block &&
        duplicate.emitted === firstError.pos[0] &&
        !KEY_STAGE_ERRORS.has(firstError.code)))
  ) {
    throw new PortableInputError(
      "yaml_duplicate_key",
      describeAt(text, duplicate.at, "Map keys must be unique"),
    );
  }
  if (firstError !== undefined) {
    const message = firstError.message;
    if (message.includes("Maximum call stack size exceeded")) {
      throw new PortableInputError("yaml_limit", "YAML exceeds the depth limit");
    }
    throw new PortableInputError("yaml_parse_error", message);
  }
  checkDroppedContent(text);
  if (document.warnings.length > 0) {
    throw new PortableInputError(
      "yaml_custom_tag",
      document.warnings[0]?.message ?? "unsupported tag",
    );
  }
  checkPlainTabs(text);
  const explicitKeys = explicitKeyIndex(text);

  let hasAlias = false;
  // `path` is bounded by MAX_DEPTH: `firstTooDeep` refused anything deeper above.
  visit(document, (_key, node, path) => {
    if (isPair(node)) {
      // A key the two engines type differently is reported as that, not as a non-string
      // key, which is what Python reports for `.5e3: x` (a string key to ruamel).
      if (
        isScalar(node.key) &&
        node.key.type === Scalar.PLAIN &&
        typeof node.key.source === "string" &&
        node.key.range
      ) {
        checkNumberForm(text, node.key.source, node.key.range[0]);
      }
      if (!isScalar(node.key) || typeof node.key.value !== "string") {
        throw new PortableInputError("yaml_non_string_key", "mapping keys must be strings");
      }
      if (node.key.value === "<<") {
        throw new PortableInputError("yaml_merge_key", "YAML merge keys are not supported");
      }
      const parent = path[path.length - 1];
      if (isMap(parent) && parent.flow === true) {
        checkFlowMappingKey(text, node.key, parent.range?.[0], explicitKeys);
      }
      return;
    }
    if (
      isAlias(node) ||
      (typeof node === "object" &&
        node !== null &&
        "anchor" in node &&
        typeof node.anchor === "string")
    ) {
      hasAlias = true;
    }
    if (isScalar(node) && node.tag !== undefined) {
      throw new PortableInputError("yaml_custom_tag", "explicit YAML tags are not supported");
    }
    if (
      isScalar(node) &&
      (node.type === Scalar.BLOCK_LITERAL || node.type === Scalar.BLOCK_FOLDED) &&
      node.range
    ) {
      checkBlockScalarSpaces(text, node.range[0], blockColumn(text, path));
    }
    if (
      isScalar(node) &&
      node.type === Scalar.PLAIN &&
      typeof node.source === "string" &&
      node.range
    ) {
      checkNumberForm(text, node.source, node.range[0]);
      if (path.some((ancestor) => isCollection(ancestor) && ancestor.flow === true)) {
        const owner = path[path.length - (isPair(path[path.length - 1]) ? 2 : 1)];
        const inMapping = isMap(owner) && owner.flow === true;
        checkFlowPlainScalar(text, node.source, node.range[0], inMapping);
      }
    }
    if (
      isScalar(node) &&
      typeof node.value === "number" &&
      Number.isInteger(node.value) &&
      Math.abs(node.value) > MAX_SAFE_INTEGER &&
      typeof node.source === "string" &&
      !/[.eE]/u.test(node.source)
    ) {
      throw new PortableInputError("number_out_of_range", "integer exceeds the safe range");
    }
  });
  if (hasAlias) {
    throw new PortableInputError("yaml_alias", "YAML aliases and anchors are not supported");
  }

  const value = document.toJS();
  checkPortableValue(value);
  return value;
}

export function checkPortableValue(root: unknown): void {
  const stack: unknown[] = [root];
  while (stack.length > 0) {
    const value = stack.pop();
    if (value === null || typeof value === "boolean") continue;
    if (typeof value === "string") {
      for (let index = 0; index < value.length; index += 1) {
        const code = value.charCodeAt(index);
        const next = value.charCodeAt(index + 1);
        if (code >= 0xd800 && code <= 0xdbff && next >= 0xdc00 && next <= 0xdfff) {
          index += 1;
        } else if (code >= 0xd800 && code <= 0xdfff) {
          throw new PortableInputError(
            "yaml_unsupported_scalar",
            "lone surrogate is not supported",
          );
        }
      }
      continue;
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) {
        throw new PortableInputError("number_out_of_range", "number must be finite");
      }
      if (Object.is(value, -0)) {
        throw new PortableInputError("number_negative_zero", "negative zero is not supported");
      }
      continue;
    }
    if (Array.isArray(value)) {
      stack.push(...value);
      continue;
    }
    if (typeof value === "object") {
      const prototype = Object.getPrototypeOf(value);
      if (prototype !== Object.prototype && prototype !== null) {
        throw new PortableInputError(
          "yaml_unsupported_scalar",
          `host-native ${value.constructor?.name ?? "object"} values are not portable; use JSON-compatible values`,
        );
      }
      stack.push(...Object.values(value));
      continue;
    }
    throw new PortableInputError(
      "yaml_unsupported_scalar",
      `unsupported YAML value: ${typeof value}`,
    );
  }
}

/**
 * Where a frontmatter-md document's metadata sits inside its text.
 *
 * All three offsets index into the *original* text, so a caller can put the document
 * back together exactly:
 *
 *     text.slice(0, metadataOffset) + newMetadata +
 *       text.slice(metadataEnd, bodyOffset) + text.slice(bodyOffset)
 *
 * That middle slice is the closing fence, kept verbatim rather than re-synthesized. This
 * is the difference from `readFrontmatterDoc`, which splits on `/\r?\n/` and rejoins
 * with `"\n"`: fine for reading values, lossy for writing the file back.
 */
export interface FrontmatterSplit {
  metadataText: string;
  metadataOffset: number;
  metadataEnd: number;
  bodyOffset: number;
}

/**
 * Split a frontmatter-md document without disturbing its body.
 *
 * Returns `null` when there is no frontmatter *region to rewrite*: no leading fence, an
 * unterminated fence, or an empty block whose end fence is the very next line.
 *
 * That is narrower than it looks. Of those three, `readFrontmatterDoc` agrees on two —
 * no leading fence and an empty block — but an unterminated fence is a *reader error*
 * there, not a fenceless document. So `null` from this function must never be read as
 * "this document has no frontmatter fence"; use `opensFrontmatterFence` for that.
 * Reading `null` as fenceless is what once let profile detection route an
 * unterminated-fence document to pure-yaml and call it valid while the reader refused to
 * open it at all.
 *
 * This is the same hand-rolled scan as Python's `split_frontmatter`, line for line, and
 * deliberately so. The fence rules have to stay identical to the reader's — if the two
 * disagree about where the frontmatter ends, a repair pass writes one region and
 * validation reads another — and writing the scan twice is what keeps the two runtimes
 * splitting identically.
 */
export function splitFrontmatter(text: string): FrontmatterSplit | null {
  // Scan by offset rather than by `split()`, because the offsets are the whole point: a
  // `\r\n` document must keep its `\r\n` body byte-for-byte.
  const first = lineEnd(text, 0);
  if (first === null || !isFenceLine(text.slice(0, first.contentEnd))) return null;
  const metadataOffset = first.next;
  let cursor = metadataOffset;
  while (cursor < text.length) {
    const line = lineEnd(text, cursor);
    if (line === null) break; // unreachable: the loop guard guarantees a line remains
    if (isFenceLine(text.slice(cursor, line.contentEnd))) {
      const metadataText = text.slice(metadataOffset, cursor);
      // An empty block (end fence on the very next line) is the portable
      // no_frontmatter case, the same as the reader's `end === 1`.
      if (/^[ \t\r\n]*$/u.test(metadataText)) return null;
      return { metadataText, metadataOffset, metadataEnd: cursor, bodyOffset: line.next };
    }
    cursor = line.next;
  }
  return null; // unterminated fence: no region to rewrite (still a reader error)
}

/**
 * Whether the document's first line is a frontmatter opening fence.
 *
 * Profile detection needs this and cannot use `splitFrontmatter`, which returns `null`
 * both for a document that never opened a fence and for one that opened a fence and
 * never closed it. Those two get opposite treatment: the first may be a pure-yaml
 * artifact, while the second is a frontmatter-md document the reader will reject.
 * Detection has to tell them apart before it can decide a profile, and without parsing,
 * because an artifact awaiting repair does not parse.
 *
 * Only the opening fence is examined; a document that opens one is frontmatter-md
 * whether or not it closes it, exactly as `readFrontmatterDoc` treats it.
 */
export function opensFrontmatterFence(text: string): boolean {
  const first = lineEnd(text, 0);
  return first !== null && isFenceLine(text.slice(0, first.contentEnd));
}

/**
 * Whether one line, given without its `\n`, is a frontmatter `---` fence.
 *
 * The spec allows `---` plus optional trailing whitespace, and *whitespace* here is the
 * ASCII blank set, space and tab, after a trailing `\r` is dropped. This is spelled out
 * because the two hosts' default trims disagree: `String.prototype.trimEnd()` strips U+FEFF,
 * which Python's `str.rstrip()` keeps, and `rstrip()` strips U+0085 and U+001C–U+001F,
 * which `trimEnd()` keeps. A fence line is never handed to the preflight (it is outside the
 * YAML block), so the fence scan is the one place such a character decides a verdict; with
 * the default trims a `---` followed by U+0085 opened a fence in Python and no fence in
 * TypeScript. Keep this identical to `is_fence_line` in `_portable.py`.
 */
export function isFenceLine(line: string): boolean {
  const content = line.endsWith("\r") ? line.slice(0, -1) : line;
  return content.replace(/[ \t]+$/u, "") === "---";
}

/**
 * The content end (before the line break) and the start of the next line.
 *
 * A final line with no trailing newline is a line. Its content ends at EOF, and the
 * "next line" starts there too, so a caller that keeps scanning stops on the next
 * iteration.
 *
 * That has to be so, because `readFrontmatterDoc` splits with `split(/\r?\n/)` and
 * Python's `read_frontmatter_doc` on `"\n"`, and both keep such a line. A scan
 * that dropped it would disagree with the reader about where a document's fences are,
 * which is the disagreement this module exists to prevent. Concretely, it made
 * `splitFrontmatter` report "no region to rewrite" for a document ending exactly at its
 * closing fence, so `--repair` silently skipped an artifact it could fix, and it made
 * `opensFrontmatterFence` call a lone `---` fenceless.
 *
 * Returns `null` only when `from` is at or past the end, where no line remains.
 */
function lineEnd(text: string, from: number): { contentEnd: number; next: number } | null {
  if (from >= text.length) return null;
  const index = text.indexOf("\n", from);
  if (index === -1) return { contentEnd: text.length, next: text.length };
  return { contentEnd: index, next: index + 1 };
}

/**
 * Parse YAML in round-trip mode: the document keeps how the author wrote it.
 *
 * Round-trip parsing is what lets a one-scalar correction stay a one-scalar diff. The
 * `yaml` package's `parseDocument` retains quotes, comments, key order, and line
 * structure, which is the direct analogue of ruamel's `typ="rt"` on the Python side.
 */
export function parseRoundTrip(text: string): ReturnType<typeof parseDocument> {
  return parseDocument(text, { uniqueKeys: true });
}

/**
 * Serialize a round-trip document with the emitter settings Python's `round_trip_yaml`
 * uses, so both runtimes write the same bytes for the same edit.
 *
 * `lineWidth: 0` disables re-wrapping (ruamel's `width = 4096` in practice), and
 * `nullStr: "null"` pins the spelling ruamel is pinned to — left alone, both emitters
 * make it depend on position in the document.
 *
 * `singleQuote: true` earns its place twice. It is what makes a newly quoted scalar come
 * out `'1850'` here as it does in ruamel, rather than `"1850"`, which is a byte-parity
 * break in the one value this pass exists to write. It also stops the emitter rewriting
 * an author's `'single'` into `"double"` — a whole-file restyling diff around a
 * one-scalar fix. Without it both regressions appear together, and only the second one
 * is visible in a golden transcript.
 *
 * The output is passed through `escapeNonPortableCharacters`, because the `yaml` emitter
 * writes a U+0085, U+2028 or U+2029 raw inside a double-quoted scalar where ruamel writes
 * `\N`, `\L` or `\P`. The region this document came from passed the portable preflight,
 * so every such character in it was written as an escape inside a double-quoted scalar,
 * and the emitter keeps that scalar double-quoted; the textual re-escape is therefore
 * exact, and without it a conform pass that retyped one scalar undid the escape beside it
 * and failed its own write guard.
 */
export function dumpRoundTrip(document: ReturnType<typeof parseDocument>): string {
  return escapeNonPortableCharacters(
    document.toString({
      lineWidth: 0,
      indent: 2,
      indentSeq: true,
      nullStr: "null",
      singleQuote: true,
    }),
  );
}

/**
 * Write an artifact back: atomically, and without touching its line endings.
 *
 * The one write path for every pass that rewrites an artifact (repair, conform, the
 * combined pipeline), so the "atomic, endings untouched" contract has a single home. The
 * text carries exactly the endings the caller preserved.
 */
export function writeArtifactText(path: string, text: string): void {
  writeFileSync(path, text, { encoding: "utf8" });
}
