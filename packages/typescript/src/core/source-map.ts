/** Runtime-neutral source spans for parsed portable values. */

export type JsonPathSegment = string | number;
export type SourceAnchor = "key" | "value";

/** One-based Unicode-code-point position in decoded source text. */
export interface SourcePoint {
  readonly line: number;
  readonly column: number;
}

/** Half-open source span with an exclusive end point. */
export interface SourceSpan {
  readonly start: SourcePoint;
  readonly end: SourcePoint;
}

/** Source spans for a value node and its mapping key, when one exists. */
export interface NodeSource {
  readonly value: SourceSpan;
  readonly key?: SourceSpan;
}

/** Immutable RFC 6901 pointer-to-source index with ancestor fallback. */
export class SourceMap {
  readonly #nodes: ReadonlyMap<string, NodeSource>;

  constructor(entries: Iterable<readonly [string, NodeSource]> = []) {
    const nodes = new Map<string, NodeSource>();
    for (const [pointer, node] of entries) nodes.set(pointer, freezeNodeSource(node));
    this.#nodes = nodes;
  }

  static empty(): SourceMap {
    return new SourceMap();
  }

  get size(): number {
    return this.#nodes.size;
  }

  /** Return a stable snapshot of the pointer/node entries. */
  entries(): readonly (readonly [string, NodeSource])[] {
    return [...this.#nodes.entries()];
  }

  /** Return the exact mapped node for an RFC 6901 pointer. */
  node(pointer: string): NodeSource | undefined {
    return this.#nodes.get(pointer);
  }

  /** Resolve a trusted internal pointer, optionally using its nearest ancestor. */
  span(
    pointer: string,
    options: { anchor?: SourceAnchor; nearest?: boolean } = {},
  ): SourceSpan | undefined {
    const anchor = options.anchor ?? "value";
    const nearest = options.nearest ?? true;
    let candidate = pointer;
    let exact = true;
    while (true) {
      const node = this.#nodes.get(candidate);
      if (node !== undefined) {
        if (exact && anchor === "key" && node.key !== undefined) return node.key;
        return node.value;
      }
      if (!nearest || candidate === "") return undefined;
      candidate = candidate.slice(0, candidate.lastIndexOf("/"));
      exact = false;
    }
  }

  /** Rebase a mapped subtree so `prefix` becomes the projected root. */
  project(prefix: readonly JsonPathSegment[]): SourceMap {
    const prefixPointer = jsonPointer(prefix);
    if (prefixPointer === "") return this;
    const childPrefix = `${prefixPointer}/`;
    const projected: [string, NodeSource][] = [];
    for (const [pointer, node] of this.#nodes) {
      if (pointer === prefixPointer) projected.push(["", node]);
      else if (pointer.startsWith(childPrefix)) {
        projected.push([pointer.slice(prefixPointer.length), node]);
      }
    }
    return new SourceMap(projected);
  }
}

/** Convert parser UTF-16 offsets into portable one-based code-point positions. */
export class SourceText {
  readonly #length: number;
  readonly #lineStarts: readonly number[];
  readonly #lineOffset: number;
  readonly #surrogatePairEnds: readonly number[];
  readonly #startsWithBom: boolean;

  constructor(text: string, lineOffset = 0) {
    const sourceIndex = indexSourceText(text);
    this.#length = text.length;
    this.#lineStarts = Object.freeze(sourceIndex.lineStarts);
    this.#lineOffset = lineOffset;
    this.#surrogatePairEnds = Object.freeze(sourceIndex.surrogatePairEnds);
    this.#startsWithBom = text.charCodeAt(0) === 0xfeff;
  }

  point(offset: number): SourcePoint {
    const bounded = boundOffset(offset, this.#length);
    const integerOffset = Math.trunc(bounded);
    const lineIndex = upperBound(this.#lineStarts, bounded) - 1;
    const lineStart = this.#lineStarts[lineIndex] as number;
    const completePairs =
      upperBound(this.#surrogatePairEnds, integerOffset) -
      upperBound(this.#surrogatePairEnds, lineStart);
    const bomWidth = lineStart === 0 && this.#startsWithBom && integerOffset > 0 ? 1 : 0;
    return Object.freeze({
      line: lineIndex + 1 + this.#lineOffset,
      column: integerOffset - lineStart - completePairs - bomWidth + 1,
    });
  }

  span(startOffset: number, endOffset: number): SourceSpan {
    return Object.freeze({ start: this.point(startOffset), end: this.point(endOffset) });
  }

  /** Return the current point when already at a line start, otherwise the next line. */
  nextLinePoint(offset: number): SourcePoint {
    const bounded = boundOffset(offset, this.#length);
    const lineIndex = lowerBound(this.#lineStarts, bounded);
    if (lineIndex < this.#lineStarts.length) {
      return Object.freeze({
        line: lineIndex + 1 + this.#lineOffset,
        column: 1,
      });
    }
    return this.point(bounded);
  }
}

/** Render path segments as an RFC 6901 JSON Pointer. */
export function jsonPointer(path: readonly JsonPathSegment[]): string {
  return path.map((part) => `/${String(part).replace(/~/g, "~0").replace(/\//g, "~1")}`).join("");
}

function freezePoint(point: SourcePoint): SourcePoint {
  if (
    !Number.isInteger(point.line) ||
    point.line < 1 ||
    !Number.isInteger(point.column) ||
    point.column < 1
  ) {
    throw new RangeError("source points must use positive one-based coordinates");
  }
  return Object.freeze({ line: point.line, column: point.column });
}

function freezeSpan(span: SourceSpan): SourceSpan {
  const start = freezePoint(span.start);
  const end = freezePoint(span.end);
  if (end.line < start.line || (end.line === start.line && end.column < start.column)) {
    throw new RangeError("source span end must not precede its start");
  }
  return Object.freeze({ start, end });
}

function freezeNodeSource(node: NodeSource): NodeSource {
  return Object.freeze({
    value: freezeSpan(node.value),
    ...(node.key === undefined ? {} : { key: freezeSpan(node.key) }),
  });
}

interface SourceTextIndex {
  readonly lineStarts: number[];
  readonly surrogatePairEnds: number[];
}

function indexSourceText(text: string): SourceTextIndex {
  const lineStarts = [0];
  const surrogatePairEnds: number[] = [];
  let index = 0;
  while (index < text.length) {
    const character = text[index];
    if (character === "\r") {
      index += text[index + 1] === "\n" ? 2 : 1;
      lineStarts.push(index);
    } else if (character === "\n") {
      index += 1;
      lineStarts.push(index);
    } else {
      const codePoint = text.codePointAt(index) as number;
      if (codePoint > 0xffff) {
        index += 2;
        surrogatePairEnds.push(index);
      } else {
        index += 1;
      }
    }
  }
  return { lineStarts, surrogatePairEnds };
}

function boundOffset(offset: number, length: number): number {
  const bounded = Math.max(0, Math.min(offset, length));
  return Number.isNaN(bounded) ? 0 : bounded;
}

function lowerBound(values: readonly number[], target: number): number {
  let low = 0;
  let high = values.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if ((values[middle] as number) < target) low = middle + 1;
    else high = middle;
  }
  return low;
}

function upperBound(values: readonly number[], target: number): number {
  let low = 0;
  let high = values.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if ((values[middle] as number) <= target) low = middle + 1;
    else high = middle;
  }
  return low;
}
