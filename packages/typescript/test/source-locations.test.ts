import { expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import {
  type NodeSource,
  SourceMap,
  type SourcePoint,
  type SourceSpan,
} from "../src/core/index.js";
import { SourceText } from "../src/core/source-map.js";
import {
  readFrontmatter,
  readFrontmatterWithLocations,
  readPureYamlArtifactWithLocations,
} from "../src/validate.js";
import {
  type JsonValue,
  parsePortableYaml,
  parsePortableYamlWithLocations,
  PortableValueError,
} from "../src/yaml-value-domain.js";
import { loadYamlFixture } from "./yaml-fixture.js";

interface SourceVector {
  id: string;
  kind: "frontmatter" | "yaml";
  content: string;
  value?: unknown;
  error?: { reason: string; path?: string; line: number; column: number };
  nodes?: Record<string, PlainNode>;
  projection?: {
    prefix: (string | number)[];
    root: PlainNode;
    lookups: { pointer: string; anchor: "key" | "value"; span: PlainSpan }[];
  };
}

interface PlainPoint {
  line: number;
  column: number;
}

interface PlainSpan {
  start: PlainPoint;
  end: PlainPoint;
}

interface PlainNode {
  key?: PlainSpan;
  value: PlainSpan;
}

interface SourceSeparatorVector {
  id: string;
  code_point: string;
  yaml: string;
  line: number;
  column: number;
}

interface SourceSeparatorVectors {
  value_error_message: string;
  literal_cases: SourceSeparatorVector[];
  escaped_case: { id: string; yaml: string; value: JsonValue };
}

const ROOT = resolve(import.meta.dir, "../../..");
const VECTORS = loadYamlFixture<{ cases: SourceVector[] }>(
  resolve(ROOT, "tests/diagnostics/source-location-vectors.yaml"),
);
const SOURCE_SEPARATOR_VECTORS = loadYamlFixture<SourceSeparatorVectors>(
  resolve(ROOT, "tests/value-domain/source-separator-vectors.yaml"),
);

function point(value: SourcePoint): PlainPoint {
  return { line: value.line, column: value.column };
}

function span(value: SourceSpan): PlainSpan {
  return { start: point(value.start), end: point(value.end) };
}

function node(value: NodeSource): PlainNode {
  return {
    ...(value.key === undefined ? {} : { key: span(value.key) }),
    value: span(value.value),
  };
}

function nodes(sourceMap: SourceMap): Record<string, PlainNode> {
  return Object.fromEntries(sourceMap.entries().map(([pointer, value]) => [pointer, node(value)]));
}

function tempPath(name: string): string {
  return join(mkdtempSync(join(tmpdir(), "softschema-source-")), name);
}

function legacyLineStarts(text: string): number[] {
  const starts = [0];
  let index = 0;
  while (index < text.length) {
    const character = text[index];
    if (character === "\r") {
      index += text[index + 1] === "\n" ? 2 : 1;
      starts.push(index);
    } else if (character === "\n") {
      index += 1;
      starts.push(index);
    } else {
      const codePoint = text.codePointAt(index) as number;
      index += codePoint > 0xffff ? 2 : 1;
    }
  }
  return starts;
}

function legacyPoint(text: string, offset: number, lineOffset: number): PlainPoint {
  const starts = legacyLineStarts(text);
  const bounded = Math.max(0, Math.min(offset, text.length));
  let low = 0;
  let high = starts.length;
  while (low + 1 < high) {
    const middle = Math.floor((low + high) / 2);
    if ((starts[middle] as number) <= bounded) low = middle;
    else high = middle;
  }
  const lineStart = starts[low] as number;
  let prefix = text.slice(lineStart, bounded);
  if (lineStart === 0 && prefix.startsWith("\uFEFF")) prefix = prefix.slice(1);
  return { line: low + 1 + lineOffset, column: [...prefix].length + 1 };
}

function legacyNextLinePoint(text: string, offset: number, lineOffset: number): PlainPoint {
  const starts = legacyLineStarts(text);
  const bounded = Math.max(0, Math.min(offset, text.length));
  for (const start of starts) {
    if (start === bounded) return legacyPoint(text, bounded, lineOffset);
    if (start > bounded) return legacyPoint(text, start, lineOffset);
  }
  return legacyPoint(text, bounded, lineOffset);
}

test.each(VECTORS.cases)("shared source location vector $id", (vector) => {
  if (vector.error !== undefined) {
    let caught: unknown;
    try {
      if (vector.kind === "frontmatter") {
        const source = tempPath("artifact.md");
        writeFileSync(source, new TextEncoder().encode(vector.content));
        readFrontmatterWithLocations(source);
      } else {
        parsePortableYamlWithLocations(vector.content);
      }
    } catch (error) {
      caught = error;
    }
    expect(caught).toBeInstanceOf(Error);
    const located = caught as Error & { path?: string; line?: number; column?: number };
    expect(located.line).toBe(vector.error.line);
    expect(located.column).toBe(vector.error.column);
    if (vector.error.path !== undefined) expect(located.path).toBe(vector.error.path);
    return;
  }

  let value: unknown;
  let sourceMap: SourceMap;
  if (vector.kind === "frontmatter") {
    const source = tempPath("artifact.md");
    writeFileSync(source, new TextEncoder().encode(vector.content));
    const parsed = readFrontmatterWithLocations(source);
    value = parsed.value;
    sourceMap = parsed.sourceMap;
  } else {
    const parsed = parsePortableYamlWithLocations(vector.content);
    value = parsed.value;
    sourceMap = parsed.sourceMap;
  }

  expect(value).toEqual(vector.value);
  expect(nodes(sourceMap)).toEqual(vector.nodes as Record<string, PlainNode>);

  if (vector.projection !== undefined) {
    const projected = sourceMap.project(vector.projection.prefix);
    const root = projected.node("");
    if (root === undefined) throw new Error("projected root missing");
    expect(node(root)).toEqual(vector.projection.root);
    for (const lookup of vector.projection.lookups) {
      const located = projected.span(lookup.pointer, { anchor: lookup.anchor });
      if (located === undefined) throw new Error(`source span missing for ${lookup.pointer}`);
      expect(span(located)).toEqual(lookup.span);
    }
    expect(projected.span("/not-present", { nearest: false })).toBeUndefined();
  }
});

test.each(SOURCE_SEPARATOR_VECTORS.literal_cases)(
  "literal nonportable source separator $code_point has a shared location",
  (vector) => {
    let caught: unknown;
    try {
      parsePortableYamlWithLocations(vector.yaml);
    } catch (error) {
      caught = error;
    }
    expect(caught).toBeInstanceOf(PortableValueError);
    const located = caught as PortableValueError;
    expect(located.message).toBe(SOURCE_SEPARATOR_VECTORS.value_error_message);
    expect(located.path).toBe("");
    expect({ line: located.line, column: located.column }).toEqual({
      line: vector.line,
      column: vector.column,
    });
  },
);

test("escaped nonportable source separators remain string values", () => {
  const vector = SOURCE_SEPARATOR_VECTORS.escaped_case;
  expect(parsePortableYamlWithLocations(vector.yaml).value).toEqual(vector.value);
});

test("a nonportable separator cannot create a Markdown frontmatter fence", () => {
  for (const separator of ["\u0085", "\u2028", "\u2029"]) {
    const source = tempPath("artifact.md");
    const text = `---${separator}\nbody\n`;
    writeFileSync(source, text, "utf8");

    const parsed = readFrontmatterWithLocations(source);

    expect(parsed.hasFence).toBe(false);
    expect(parsed.value).toBeNull();
    expect(parsed.sourceMap.size).toBe(0);
  }
});

test("SourceText treats only CR, LF, and CRLF as line breaks", () => {
  const text = "a\u0085b\u2028c\u2029d\nx";
  const sourceText = new SourceText(text);

  expect(sourceText.point(text.indexOf("\n"))).toEqual({ line: 1, column: 8 });
  expect(sourceText.point(text.length)).toEqual({ line: 2, column: 2 });
});

test("SourceText indexes preserve every legacy offset coordinate", () => {
  const text = "\uFEFFA😀\r\nB\u0085\u2028\u2029\ud800C\rD\nE\udc00";
  const lineOffset = 3;
  const sourceText = new SourceText(text, lineOffset);
  const offsets = [Number.NaN, Number.NEGATIVE_INFINITY, Number.POSITIVE_INFINITY];
  for (let offset = -1; offset <= text.length + 1; offset += 0.5) offsets.push(offset);

  for (const offset of offsets) {
    expect(sourceText.point(offset)).toEqual(legacyPoint(text, offset, lineOffset));
    expect(sourceText.nextLinePoint(offset)).toEqual(
      legacyNextLinePoint(text, offset, lineOffset),
    );
  }
});

test("SourceText lookups do not scan source prefixes or line-start arrays", () => {
  const text = `\uFEFF${"row😀\r\n".repeat(2_048)}tail😀`;
  const sourceText = new SourceText(text, 2);
  const sliceDescriptor = Object.getOwnPropertyDescriptor(String.prototype, "slice");
  const iteratorDescriptor = Object.getOwnPropertyDescriptor(Array.prototype, Symbol.iterator);
  if (sliceDescriptor === undefined || iteratorDescriptor === undefined) {
    throw new Error("built-in instrumentation descriptors are unavailable");
  }
  const originalSlice = String.prototype.slice;
  const originalArrayIterator = Array.prototype[Symbol.iterator];
  let sliceCalls = 0;
  let arrayValuesVisited = 0;
  let finalPoint: SourcePoint | undefined;
  let finalNextLinePoint: SourcePoint | undefined;

  Object.defineProperty(String.prototype, "slice", {
    ...sliceDescriptor,
    value: function instrumentedSlice(this: string, start?: number, end?: number): string {
      sliceCalls += 1;
      return Reflect.apply(originalSlice, this, [start, end]);
    },
  });
  Object.defineProperty(Array.prototype, Symbol.iterator, {
    ...iteratorDescriptor,
    value: function* instrumentedArrayIterator(this: unknown[]): Generator<unknown, void, unknown> {
      const iterator = originalArrayIterator.call(this);
      while (true) {
        const result = iterator.next();
        if (result.done) return;
        arrayValuesVisited += 1;
        yield result.value;
      }
    },
  });
  try {
    for (let offset = text.length; offset >= 0; offset -= 97) {
      finalPoint = sourceText.point(offset);
      finalNextLinePoint = sourceText.nextLinePoint(offset - 0.25);
    }
  } finally {
    Object.defineProperty(String.prototype, "slice", sliceDescriptor);
    Object.defineProperty(Array.prototype, Symbol.iterator, iteratorDescriptor);
  }

  expect(finalPoint).toBeDefined();
  expect(finalNextLinePoint).toBeDefined();
  expect(sliceCalls).toBe(0);
  expect(arrayValuesVisited).toBe(0);
});

test("source maps freeze nodes and copy constructor entries", () => {
  const sourceSpan = { start: { line: 1, column: 1 }, end: { line: 1, column: 2 } };
  const entries: [string, NodeSource][] = [["", { value: sourceSpan }]];
  const sourceMap = new SourceMap(entries);
  entries.length = 0;

  expect(sourceMap.node("")).toEqual({ value: sourceSpan });
  expect(() => {
    (sourceMap.node("")?.value.start as { line: number }).line = 2;
  }).toThrow();
  expect(sourceMap.node("")?.value.start.line).toBe(1);
});

test("legacy parsers preserve their return shapes", () => {
  const yamlText = "root:\n  child: value\n";
  expect(parsePortableYaml(yamlText)).toEqual({ root: { child: "value" } });

  const source = tempPath("artifact.md");
  writeFileSync(source, `---\n${yamlText}---\nbody\n`, "utf8");
  expect(readFrontmatter(source)).toEqual({
    hasFence: true,
    value: { root: { child: "value" } },
  });
});

test("pure YAML reader exposes the same source map", () => {
  const vector = VECTORS.cases.find((item) => item.id === "yaml-bom-crlf-unicode-key");
  if (vector === undefined) throw new Error("unicode vector missing");
  const source = tempPath("artifact.yaml");
  writeFileSync(source, new TextEncoder().encode(vector.content));

  const parsed = readPureYamlArtifactWithLocations(source);

  expect(parsed.value as unknown).toEqual(vector.value);
  expect(nodes(parsed.sourceMap)).toEqual(vector.nodes as Record<string, PlainNode>);
});

test("value-domain errors retain the portable class", () => {
  expect(() => parsePortableYamlWithLocations("value: .nan\n")).toThrow(PortableValueError);
});
