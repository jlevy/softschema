/** Portable YAML input shared by artifact and schema reads.
 *
 * The input, node, and scalar ceilings were removed. They only answered whether a
 * hostile document could exhaust the parser, and softschema reads artifacts its own
 * callers just wrote. The portable-value rules here stay, because they are what makes a
 * document mean the same thing in both runtimes.
 */
import { readFileSync } from "node:fs";
import { writeFileSync } from "atomically";
import { isAlias, isCollection, isPair, isScalar, parseDocument, visit } from "yaml";

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

export function readUtf8(path: string): string {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(readFileSync(path));
  } catch (error) {
    if (error instanceof TypeError) {
      throw new PortableInputError("invalid_utf8", "input is not valid UTF-8");
    }
    throw error;
  }
}

export function parsePortableYaml(text: string): unknown {
  let document: ReturnType<typeof parseDocument>;
  try {
    document = parseDocument(text, { uniqueKeys: true });
  } catch (error) {
    if (error instanceof RangeError || String(error).includes("Maximum call stack size exceeded")) {
      throw new PortableInputError("yaml_limit", "YAML exceeds the depth limit");
    }
    throw error;
  }
  if (document.errors.length > 0) {
    const message = document.errors[0]?.message ?? "invalid YAML";
    if (message.includes("Maximum call stack size exceeded")) {
      throw new PortableInputError("yaml_limit", "YAML exceeds the depth limit");
    }
    const code = message.includes("Map keys must be unique")
      ? "yaml_duplicate_key"
      : "yaml_parse_error";
    throw new PortableInputError(code, message);
  }
  if (document.warnings.length > 0) {
    throw new PortableInputError(
      "yaml_custom_tag",
      document.warnings[0]?.message ?? "unsupported tag",
    );
  }

  let hasAlias = false;
  visit(document, (_key, node, path) => {
    // `path` is bounded by MAX_DEPTH, because exceeding it throws on the next node.
    const depth = path.reduce((total, ancestor) => total + (isCollection(ancestor) ? 1 : 0), 0);
    if (depth > MAX_DEPTH) {
      throw new PortableInputError("yaml_limit", "YAML exceeds the depth limit");
    }
    if (isPair(node)) {
      if (!isScalar(node.key) || typeof node.key.value !== "string") {
        throw new PortableInputError("yaml_non_string_key", "mapping keys must be strings");
      }
      if (node.key.value === "<<") {
        throw new PortableInputError("yaml_merge_key", "YAML merge keys are not supported");
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
 * Returns `null` when the document has no frontmatter, matching what
 * `readFrontmatterDoc` reports: no leading fence, an unterminated fence, or an empty
 * block whose end fence is the very next line.
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
  if (first === null || text.slice(0, first.contentEnd).trimEnd() !== "---") return null;
  const metadataOffset = first.next;
  let cursor = metadataOffset;
  while (cursor < text.length) {
    const line = lineEnd(text, cursor);
    if (line === null) return null; // unterminated fence: no frontmatter to speak of
    if (text.slice(cursor, line.contentEnd).trimEnd() === "---") {
      const metadataText = text.slice(metadataOffset, cursor);
      // An empty block (end fence on the very next line) is the portable
      // no_frontmatter case, the same as the reader's `end === 1`.
      if (metadataText.trim() === "") return null;
      return { metadataText, metadataOffset, metadataEnd: cursor, bodyOffset: line.next };
    }
    cursor = line.next;
  }
  return null;
}

/** The content end (before the line break) and the start of the next line. */
function lineEnd(text: string, from: number): { contentEnd: number; next: number } | null {
  const index = text.indexOf("\n", from);
  if (index === -1) return null;
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
 */
export function dumpRoundTrip(document: ReturnType<typeof parseDocument>): string {
  return document.toString({
    lineWidth: 0,
    indent: 2,
    indentSeq: true,
    nullStr: "null",
    singleQuote: true,
  });
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
