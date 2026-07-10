/** Portable JSON Schema regular-expression profile with bounded lazy-DFA matching. */

import { compareUnicodeCodePoints } from "./core/canonical-json.js";

export const PORTABLE_PATTERN_PROFILE = "portable-regex-v1";
export const PORTABLE_PATTERN_MAX_QUANTIFIER = 1000;
export const PORTABLE_PATTERN_MAX_CODEPOINTS = 1024;
export const PORTABLE_PATTERN_MAX_GROUP_DEPTH = 64;
export const PORTABLE_PATTERN_MAX_NFA_STATES = 4096;
export const PORTABLE_PATTERN_MAX_DFA_STATES = 4096;
export const PORTABLE_PATTERN_MAX_DFA_TRANSITIONS = 4096;
export const PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS = 32_768;
export const PORTABLE_PATTERN_MAX_MATCH_COMPUTE_WORK = 4_194_304;
export const PORTABLE_PATTERN_MAX_VALIDATION_WORK = 8_388_608;
export const PORTABLE_PATTERN_MAX_VALIDATION_MEMO_ENTRIES = 4096;
export const PORTABLE_PATTERN_MAX_VALIDATION_MEMO_CODEPOINTS = 1_048_576;
export const PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS = 256;
export const PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS = 16_384;
export const PORTABLE_PATTERN_CACHE_SIZE = 32;
export const PORTABLE_PATTERN_MAX_CACHED_DFA_TRANSITIONS: number =
  PORTABLE_PATTERN_CACHE_SIZE * PORTABLE_PATTERN_MAX_DFA_TRANSITIONS;
export const PORTABLE_PATTERN_MAX_CACHED_SUBSET_MEMBERSHIPS: number =
  PORTABLE_PATTERN_CACHE_SIZE * PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS;

const maxUnicodeCodePoint = 0x10ffff;

const hexDigits = new Set("0123456789abcdefABCDEF");
const escapedSyntaxOutside = new Set("\\.^$*+?{}[]()|");
const escapedSyntaxClass = new Set("\\[]^-.");
const schemaMapKeywords = new Set([
  "$defs",
  "definitions",
  "dependentSchemas",
  "patternProperties",
  "properties",
]);
const schemaArrayKeywords = new Set(["allOf", "anyOf", "oneOf", "prefixItems"]);
const schemaSingleKeywords = new Set([
  "additionalItems",
  "additionalProperties",
  "contains",
  "contentSchema",
  "else",
  "if",
  "items",
  "not",
  "propertyNames",
  "then",
  "unevaluatedItems",
  "unevaluatedProperties",
]);

/** Raised when a pattern falls outside portable-regex-v1. */
export class PortablePatternError extends Error {}

/** Raised instead of allowing profile matching work to become unbounded. */
export class PortablePatternWorkLimitError extends Error {}

interface ValidationWorkContext {
  remaining: number;
  readonly matches: Map<PortableRegExp, Map<string, boolean>>;
  memoEntries: number;
  memoCodePoints: number;
}

let validationWorkContext: ValidationWorkContext | null = null;

/** Bound aggregate pattern/key work for one synchronous structural validation. */
export function withPortablePatternValidationBudget<T>(
  operation: () => T,
  limit: number = PORTABLE_PATTERN_MAX_VALIDATION_WORK,
): T {
  const previous = validationWorkContext;
  validationWorkContext = {
    remaining: limit,
    matches: new Map(),
    memoEntries: 0,
    memoCodePoints: 0,
  };
  try {
    return operation();
  } finally {
    validationWorkContext = previous;
  }
}

interface ClassAtom {
  codePoint: number | null;
  directOperator: string | null;
  term: ClassTerm;
}

type ClassTerm =
  | {
      readonly kind: "range";
      readonly minimum: number;
      readonly maximum: number;
    }
  | { readonly kind: "digit" | "word" | "space"; readonly negated: boolean };

type CharacterMatcher =
  | { readonly kind: "literal"; readonly codePoint: number }
  | { readonly kind: "dot" }
  | { readonly kind: "digit" | "word" | "space"; readonly negated: boolean }
  | {
      readonly kind: "class";
      readonly ranges: readonly (readonly [number, number])[];
    };

function normalizeRanges(
  ranges: readonly (readonly [number, number])[],
): readonly (readonly [number, number])[] {
  const sorted = Array.from(ranges).sort((left, right) => left[0] - right[0] || left[1] - right[1]);
  const merged: [number, number][] = [];
  for (const [start, end] of sorted) {
    const previous = merged[merged.length - 1];
    if (previous !== undefined && start <= previous[1] + 1) {
      previous[1] = Math.max(previous[1], end);
    } else {
      merged.push([start, end]);
    }
  }
  return merged;
}

function complementRanges(
  ranges: readonly (readonly [number, number])[],
): readonly (readonly [number, number])[] {
  const complement: [number, number][] = [];
  let cursor = 0;
  for (const [start, end] of ranges) {
    if (cursor < start) complement.push([cursor, start - 1]);
    cursor = end + 1;
  }
  if (cursor <= maxUnicodeCodePoint) complement.push([cursor, maxUnicodeCodePoint]);
  return complement;
}

type PatternNode =
  | { readonly kind: "empty" }
  | { readonly kind: "sequence"; readonly nodes: readonly PatternNode[] }
  | { readonly kind: "alternation"; readonly nodes: readonly PatternNode[] }
  | { readonly kind: "character"; readonly matcher: CharacterMatcher }
  | { readonly kind: "start" | "end" }
  | {
      readonly kind: "repeat";
      readonly node: PatternNode;
      readonly minimum: number;
      readonly maximum: number | null;
    };

type NfaState =
  | { readonly kind: "accept" }
  | {
      readonly kind: "character";
      readonly matcher: CharacterMatcher;
      next: number | null;
    }
  | { readonly kind: "jump" | "start" | "end"; next: number | null }
  | { readonly kind: "split"; first: number | null; second: number | null };

interface PatchReference {
  readonly state: number;
  readonly edge: "next" | "first" | "second";
}

interface Fragment {
  readonly start: number;
  readonly outs: readonly PatchReference[];
}

function enforcePatternSourceLimits(pattern: string): void {
  let codePoints = 0;
  let groupDepth = 0;
  let inClass = false;
  let escaped = false;

  for (const character of pattern) {
    codePoints += 1;
    if (codePoints > PORTABLE_PATTERN_MAX_CODEPOINTS) {
      throw new PortablePatternError("pattern exceeds the profile code-point limit");
    }
    if (escaped) {
      escaped = false;
      continue;
    }
    if (character === "\\") {
      escaped = true;
      continue;
    }
    if (inClass) {
      if (character === "]") inClass = false;
      continue;
    }
    if (character === "[") {
      inClass = true;
    } else if (character === "(") {
      groupDepth += 1;
      if (groupDepth > PORTABLE_PATTERN_MAX_GROUP_DEPTH) {
        throw new PortablePatternError("pattern exceeds the profile group-depth limit");
      }
    } else if (character === ")") {
      groupDepth = Math.max(0, groupDepth - 1);
    }
  }
}

class Parser {
  private index = 0;

  constructor(private readonly pattern: string) {
    enforcePatternSourceLimits(pattern);
  }

  parse(): PatternNode {
    const node = this.expression(null);
    if (this.index !== this.pattern.length) {
      throw new PortablePatternError("unexpected trailing pattern syntax");
    }
    return node;
  }

  private expression(terminator: string | null): PatternNode {
    const alternatives: PatternNode[] = [];
    let sequence: PatternNode[] = [];
    while (true) {
      const current = this.peek();
      if (current === null || (terminator !== null && current === terminator)) {
        alternatives.push(this.sequence(sequence));
        if (current === null && terminator !== null) {
          throw new PortablePatternError("unterminated group");
        }
        break;
      }
      if (current === "|") {
        this.take();
        alternatives.push(this.sequence(sequence));
        sequence = [];
      } else {
        sequence.push(this.piece());
      }
    }
    return alternatives.length === 1
      ? (alternatives[0] as PatternNode)
      : { kind: "alternation", nodes: alternatives };
  }

  private sequence(nodes: readonly PatternNode[]): PatternNode {
    if (nodes.length === 0) return { kind: "empty" };
    return nodes.length === 1 ? (nodes[0] as PatternNode) : { kind: "sequence", nodes };
  }

  private piece(): PatternNode {
    const { node, quantifiable } = this.atom();
    const current = this.peek();
    if (current === null || !"*+?{".includes(current)) return node;
    if (!quantifiable) throw new PortablePatternError("assertions cannot be quantified");
    const { minimum, maximum } = this.quantifier();
    return { kind: "repeat", node, minimum, maximum };
  }

  private atom(): { node: PatternNode; quantifiable: boolean } {
    const current = this.peek();
    if (current === null) throw new PortablePatternError("expected an atom");
    if (current === "(") {
      this.take();
      if (this.pattern.startsWith("?:", this.index)) {
        this.index += 2;
      } else if (this.peek() === "?") {
        throw new PortablePatternError("unsupported group construct");
      }
      const node = this.expression(")");
      this.take();
      return { node, quantifiable: true };
    }
    if (current === "[") {
      return {
        node: { kind: "character", matcher: this.characterClass() },
        quantifiable: true,
      };
    }
    if (current === "\\") {
      return {
        node: {
          kind: "character",
          matcher: this.matcherFromAtom(this.escape(false)),
        },
        quantifiable: true,
      };
    }
    if (current === ".") {
      this.take();
      return {
        node: { kind: "character", matcher: { kind: "dot" } },
        quantifiable: true,
      };
    }
    if (current === "^") {
      this.take();
      return { node: { kind: "start" }, quantifiable: false };
    }
    if (current === "$") {
      this.take();
      return { node: { kind: "end" }, quantifiable: false };
    }
    if (")]*+?{}]".includes(current)) {
      throw new PortablePatternError("unexpected pattern syntax");
    }
    const codePoint = current.codePointAt(0);
    if (codePoint !== undefined && codePoint >= 0xd800 && codePoint <= 0xdfff) {
      throw new PortablePatternError("surrogate literals are unsupported");
    }
    this.take();
    return {
      node: {
        kind: "character",
        matcher: { kind: "literal", codePoint: codePoint as number },
      },
      quantifiable: true,
    };
  }

  private characterClass(): CharacterMatcher {
    this.take();
    const negated = this.peek() === "^";
    if (negated) this.take();

    let itemCount = 0;
    let previousOperator: string | null = null;
    const terms: ClassTerm[] = [];
    while (this.peek() !== null && this.peek() !== "]") {
      let start: ClassAtom;
      if (this.peek() === "-" && (itemCount === 0 || this.peekAt(this.index + 1) === "]")) {
        this.take();
        start = this.literalClassAtom("-".codePointAt(0) as number);
      } else {
        start = this.classAtom();
      }
      itemCount += 1;
      if (previousOperator !== null && previousOperator === start.directOperator) {
        throw new PortablePatternError("ambiguous future character-set operator");
      }
      previousOperator = start.directOperator;

      if (
        this.peek() === "-" &&
        this.peekAt(this.index + 1) !== null &&
        this.peekAt(this.index + 1) !== "]"
      ) {
        if (start.codePoint === null) {
          throw new PortablePatternError("class shorthand cannot start a range");
        }
        this.take();
        const end = this.classAtom();
        if (end.codePoint === null || start.codePoint > end.codePoint) {
          throw new PortablePatternError("invalid character range");
        }
        terms.push({
          kind: "range",
          minimum: start.codePoint,
          maximum: end.codePoint,
        });
        previousOperator = end.directOperator;
      } else {
        terms.push(start.term);
      }
    }
    if (this.peek() !== "]" || itemCount === 0) {
      throw new PortablePatternError("unterminated or empty character class");
    }
    this.take();
    return { kind: "class", ranges: normalizeClassRanges(terms, negated) };
  }

  private classAtom(): ClassAtom {
    const current = this.peek();
    if (current === null) throw new PortablePatternError("unterminated character class");
    if (current === "\\") return this.escape(true);
    if ("[]-^".includes(current)) {
      throw new PortablePatternError("class syntax characters must be escaped");
    }
    const codePoint = current.codePointAt(0);
    if (codePoint !== undefined && codePoint >= 0xd800 && codePoint <= 0xdfff) {
      throw new PortablePatternError("surrogate literals are unsupported");
    }
    this.take();
    return this.literalClassAtom(codePoint as number, "&|~".includes(current) ? current : null);
  }

  private escape(inClass: boolean): ClassAtom {
    this.take();
    const escaped = this.take();
    if (escaped === null) throw new PortablePatternError("dangling escape");

    if ("dDwW".includes(escaped)) {
      return {
        codePoint: null,
        directOperator: null,
        term: {
          kind: escaped.toLowerCase() === "d" ? "digit" : "word",
          negated: escaped === escaped.toUpperCase(),
        },
      };
    }
    if ("sS".includes(escaped)) {
      if (inClass) {
        throw new PortablePatternError("whitespace complements in classes are unsupported");
      }
      return {
        codePoint: null,
        directOperator: null,
        term: { kind: "space", negated: escaped === "S" },
      };
    }
    if ("nrtfv".includes(escaped)) {
      const codePoints: Record<string, number> = {
        n: 10,
        r: 13,
        t: 9,
        f: 12,
        v: 11,
      };
      return this.literalClassAtom(codePoints[escaped] as number);
    }
    if (escaped === "x") {
      return this.literalClassAtom(Number.parseInt(this.hex(2), 16));
    }
    if (escaped === "u") {
      const codePoint = Number.parseInt(this.hex(4), 16);
      if (codePoint >= 0xd800 && codePoint <= 0xdfff) {
        throw new PortablePatternError("surrogate escapes are unsupported");
      }
      return this.literalClassAtom(codePoint);
    }

    const allowed = inClass ? escapedSyntaxClass : escapedSyntaxOutside;
    if (!allowed.has(escaped)) throw new PortablePatternError("unsupported escape");
    return this.literalClassAtom(escaped.codePointAt(0) as number);
  }

  private literalClassAtom(codePoint: number, directOperator: string | null = null): ClassAtom {
    return {
      codePoint,
      directOperator,
      term: { kind: "range", minimum: codePoint, maximum: codePoint },
    };
  }

  private matcherFromAtom(atom: ClassAtom): CharacterMatcher {
    if (atom.codePoint !== null) return { kind: "literal", codePoint: atom.codePoint };
    if (atom.term.kind === "range") throw new PortablePatternError("invalid character escape");
    return { kind: atom.term.kind, negated: atom.term.negated };
  }

  private hex(count: number): string {
    const end = this.index + count;
    const digits = this.pattern.slice(this.index, end);
    if (digits.length !== count || [...digits].some((digit) => !hexDigits.has(digit))) {
      throw new PortablePatternError("invalid hexadecimal escape");
    }
    this.index = end;
    return digits;
  }

  private quantifier(): { minimum: number; maximum: number | null } {
    const current = this.peek();
    let minimum: number;
    let maximum: number | null;
    if (current === "*") {
      this.take();
      minimum = 0;
      maximum = null;
    } else if (current === "+") {
      this.take();
      minimum = 1;
      maximum = null;
    } else if (current === "?") {
      this.take();
      minimum = 0;
      maximum = 1;
    } else {
      this.take();
      minimum = this.bound();
      maximum = minimum;
      if (this.peek() === ",") {
        this.take();
        maximum = this.peek() === "}" ? null : this.bound();
      }
      if (this.peek() !== "}") {
        throw new PortablePatternError("unterminated bounded quantifier");
      }
      this.take();
      if (maximum !== null && maximum < minimum) {
        throw new PortablePatternError("reversed bounded quantifier");
      }
    }
    if (this.peek() === "?") this.take();
    return { minimum, maximum };
  }

  private bound(): number {
    const start = this.index;
    while (true) {
      const digit = this.peek();
      if (digit === null || digit < "0" || digit > "9") break;
      this.take();
    }
    const digits = this.pattern.slice(start, this.index);
    if (digits.length === 0 || (digits.length > 1 && digits.startsWith("0"))) {
      throw new PortablePatternError("invalid quantifier bound");
    }
    const value = Number.parseInt(digits, 10);
    if (value > PORTABLE_PATTERN_MAX_QUANTIFIER) {
      throw new PortablePatternError("quantifier bound exceeds the profile limit");
    }
    return value;
  }

  private peek(): string | null {
    return this.peekAt(this.index);
  }

  private peekAt(index: number): string | null {
    if (index >= this.pattern.length) return null;
    const codePoint = this.pattern.codePointAt(index);
    return codePoint === undefined ? null : String.fromCodePoint(codePoint);
  }

  private take(): string | null {
    const value = this.peek();
    if (value !== null) this.index += value.length;
    return value;
  }
}

class NfaBuilder {
  readonly states: NfaState[] = [];

  build(node: PatternNode): {
    readonly states: readonly NfaState[];
    readonly start: number;
  } {
    const fragment = this.compile(node);
    const accept = this.add({ kind: "accept" });
    this.patch(fragment.outs, accept);
    return { states: this.states, start: fragment.start };
  }

  private compile(node: PatternNode): Fragment {
    switch (node.kind) {
      case "empty": {
        const state = this.add({ kind: "jump", next: null });
        return { start: state, outs: [{ state, edge: "next" }] };
      }
      case "character": {
        const state = this.add({
          kind: "character",
          matcher: node.matcher,
          next: null,
        });
        return { start: state, outs: [{ state, edge: "next" }] };
      }
      case "start":
      case "end": {
        const state = this.add({ kind: node.kind, next: null });
        return { start: state, outs: [{ state, edge: "next" }] };
      }
      case "sequence":
        return this.sequence(node.nodes.map((child) => this.compile(child)));
      case "alternation": {
        const fragments = node.nodes.map((child) => this.compile(child));
        let result = fragments[0] as Fragment;
        for (const fragment of fragments.slice(1)) {
          const split = this.add({
            kind: "split",
            first: result.start,
            second: fragment.start,
          });
          result = { start: split, outs: [...result.outs, ...fragment.outs] };
        }
        return result;
      }
      case "repeat":
        return this.repeat(node);
    }
  }

  private repeat(node: Extract<PatternNode, { kind: "repeat" }>): Fragment {
    if (node.maximum === 0) return this.compile({ kind: "empty" });

    const fragments: Fragment[] = [];
    for (let count = 0; count < node.minimum; count += 1) {
      fragments.push(this.compile(node.node));
    }
    if (node.maximum === null) {
      const repeated = this.compile(node.node);
      const split = this.add({
        kind: "split",
        first: repeated.start,
        second: null,
      });
      this.patch(repeated.outs, split);
      fragments.push({
        start: split,
        outs: [{ state: split, edge: "second" }],
      });
    } else {
      for (let count = node.minimum; count < node.maximum; count += 1) {
        const optional = this.compile(node.node);
        const split = this.add({
          kind: "split",
          first: optional.start,
          second: null,
        });
        fragments.push({
          start: split,
          outs: [...optional.outs, { state: split, edge: "second" }],
        });
      }
    }
    return this.sequence(fragments);
  }

  private sequence(fragments: readonly Fragment[]): Fragment {
    if (fragments.length === 0) return this.compile({ kind: "empty" });
    const first = fragments[0] as Fragment;
    let outs = first.outs;
    for (const fragment of fragments.slice(1)) {
      this.patch(outs, fragment.start);
      outs = fragment.outs;
    }
    return { start: first.start, outs };
  }

  private patch(references: readonly PatchReference[], target: number): void {
    for (const reference of references) {
      const state = this.states[reference.state];
      if (state === undefined || state.kind === "accept" || state.kind === "character") {
        if (state?.kind === "character" && reference.edge === "next" && state.next === null) {
          state.next = target;
          continue;
        }
        throw new Error("invalid portable-regex NFA patch");
      }
      if (reference.edge === "next" && state.kind !== "split" && state.next === null) {
        state.next = target;
      } else if (reference.edge === "first" && state.kind === "split" && state.first === null) {
        state.first = target;
      } else if (reference.edge === "second" && state.kind === "split" && state.second === null) {
        state.second = target;
      } else {
        throw new Error("invalid portable-regex NFA patch");
      }
    }
  }

  private add(state: NfaState): number {
    if (this.states.length >= PORTABLE_PATTERN_MAX_NFA_STATES) {
      throw new PortablePatternError("pattern exceeds the profile NFA-state limit");
    }
    this.states.push(state);
    return this.states.length - 1;
  }
}

function isWhitespace(codePoint: number): boolean {
  return (
    (codePoint >= 0x0009 && codePoint <= 0x000d) ||
    codePoint === 0x0020 ||
    codePoint === 0x00a0 ||
    codePoint === 0x1680 ||
    (codePoint >= 0x2000 && codePoint <= 0x200a) ||
    codePoint === 0x2028 ||
    codePoint === 0x2029 ||
    codePoint === 0x202f ||
    codePoint === 0x205f ||
    codePoint === 0x3000 ||
    codePoint === 0xfeff
  );
}

function classTermRanges(term: ClassTerm): readonly (readonly [number, number])[] {
  if (term.kind === "range") return [[term.minimum, term.maximum]];
  let ranges: readonly (readonly [number, number])[];
  if (term.kind === "digit") {
    ranges = [[0x30, 0x39]];
  } else if (term.kind === "word") {
    ranges = [
      [0x30, 0x39],
      [0x41, 0x5a],
      [0x5f, 0x5f],
      [0x61, 0x7a],
    ];
  } else {
    ranges = [
      [0x0009, 0x000d],
      [0x0020, 0x0020],
      [0x00a0, 0x00a0],
      [0x1680, 0x1680],
      [0x2000, 0x200a],
      [0x2028, 0x2029],
      [0x202f, 0x202f],
      [0x205f, 0x205f],
      [0x3000, 0x3000],
      [0xfeff, 0xfeff],
    ];
  }
  return term.negated ? complementRanges(ranges) : ranges;
}

function normalizeClassRanges(
  terms: readonly ClassTerm[],
  negated: boolean,
): readonly (readonly [number, number])[] {
  const ranges = normalizeRanges(terms.flatMap((term) => classTermRanges(term)));
  return negated ? complementRanges(ranges) : ranges;
}

function rangesContain(ranges: readonly (readonly [number, number])[], codePoint: number): boolean {
  let low = 0;
  let high = ranges.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if ((ranges[middle]?.[0] ?? 0) <= codePoint) low = middle + 1;
    else high = middle;
  }
  const candidate = ranges[low - 1];
  return candidate !== undefined && codePoint <= candidate[1];
}

function matchesCharacter(matcher: CharacterMatcher, codePoint: number): boolean {
  switch (matcher.kind) {
    case "literal":
      return codePoint === matcher.codePoint;
    case "dot":
      return ![0x000a, 0x000d, 0x2028, 0x2029].includes(codePoint);
    case "digit": {
      const positive = codePoint >= 0x30 && codePoint <= 0x39;
      return matcher.negated ? !positive : positive;
    }
    case "word": {
      const positive =
        (codePoint >= 0x30 && codePoint <= 0x39) ||
        (codePoint >= 0x41 && codePoint <= 0x5a) ||
        codePoint === 0x5f ||
        (codePoint >= 0x61 && codePoint <= 0x7a);
      return matcher.negated ? !positive : positive;
    }
    case "space": {
      const positive = isWhitespace(codePoint);
      return matcher.negated ? !positive : positive;
    }
    case "class": {
      return rangesContain(matcher.ranges, codePoint);
    }
  }
}

function matcherRanges(matcher: CharacterMatcher): readonly (readonly [number, number])[] {
  switch (matcher.kind) {
    case "literal":
      return [[matcher.codePoint, matcher.codePoint]];
    case "dot":
      return complementRanges([
        [0x000a, 0x000a],
        [0x000d, 0x000d],
        [0x2028, 0x2029],
      ]);
    case "digit":
    case "word":
    case "space":
      return classTermRanges(matcher);
    case "class":
      return matcher.ranges;
  }
}

interface ReadyState {
  readonly active: readonly number[];
  readonly accepted: boolean;
}

class PortableRegExp {
  private readonly states: readonly NfaState[];
  private readonly start: number;
  private readonly boundaries: readonly number[];
  private readonly pendingStates: number[][] = [[]];
  private readonly pendingIds = new Map<string, number>([["", 0]]);
  private readonly closures = new Map<number, ReadyState>();
  private readonly transitions = new Map<string, number>();
  private retainedSubsetMemberships = 0;

  constructor(private readonly pattern: string) {
    const built = new NfaBuilder().build(new Parser(pattern).parse());
    this.states = built.states;
    this.start = built.start;
    const boundaries = new Set<number>([0, maxUnicodeCodePoint + 1]);
    for (const state of this.states) {
      if (state.kind !== "character") continue;
      for (const [start, end] of matcherRanges(state.matcher)) {
        boundaries.add(start);
        if (end < maxUnicodeCodePoint) boundaries.add(end + 1);
      }
    }
    this.boundaries = Array.from(boundaries).sort((left, right) => left - right);
  }

  test(value: string): boolean {
    const context = validationWorkContext;
    const cached = context?.matches.get(this)?.get(value);
    if (cached !== undefined) return cached;
    let codePoints = 1;
    for (const _character of value) codePoints += 1;
    if (context !== null) this.chargeValidation(context, codePoints);
    const result = this.testUncached(value);
    if (
      context !== null &&
      context.memoEntries < PORTABLE_PATTERN_MAX_VALIDATION_MEMO_ENTRIES &&
      context.memoCodePoints + codePoints - 1 + Array.from(this.pattern).length <=
        PORTABLE_PATTERN_MAX_VALIDATION_MEMO_CODEPOINTS
    ) {
      let patternMatches = context.matches.get(this);
      if (patternMatches === undefined) {
        patternMatches = new Map();
        context.matches.set(this, patternMatches);
      }
      patternMatches.set(value, result);
      context.memoEntries += 1;
      context.memoCodePoints += codePoints - 1 + Array.from(this.pattern).length;
    }
    return result;
  }

  private testUncached(value: string): boolean {
    const computeWork = { remaining: PORTABLE_PATTERN_MAX_MATCH_COMPUTE_WORK };
    let pendingId = 0;
    let offset = 0;

    while (true) {
      const atStart = offset === 0;
      const atEnd = offset === value.length;
      let ready: ReadyState | undefined;
      if (!atStart && !atEnd) ready = this.closures.get(pendingId);
      if (ready === undefined) {
        ready = this.closure(pendingId, atStart, atEnd, computeWork);
        if (!atStart && !atEnd) {
          if (this.closures.size >= PORTABLE_PATTERN_MAX_DFA_STATES) {
            throw new PortablePatternWorkLimitError("portable pattern DFA-state limit exceeded");
          }
          if (this.retainSubsetMemberships(ready.active.length)) {
            this.closures.set(pendingId, ready);
          }
        }
      }
      if (ready.accepted) return true;
      if (atEnd) return false;

      const codePoint = value.codePointAt(offset);
      if (codePoint === undefined) return false;
      const classIndex = this.classIndex(codePoint);
      const transitionKey = `${atStart ? "s" : pendingId}:${classIndex}`;
      let nextPendingId = this.transitions.get(transitionKey);
      if (nextPendingId === undefined) {
        this.chargeCompute(computeWork, ready.active.length);
        const next = new Set<number>();
        for (const stateIndex of ready.active) {
          const state = this.states[stateIndex];
          if (state?.kind === "character" && matchesCharacter(state.matcher, codePoint)) {
            if (state.next !== null) next.add(state.next);
          }
        }
        const interned = this.internPending(Array.from(next).sort((left, right) => left - right));
        nextPendingId = interned.identifier;
        // A membership-budget reset renumbers retained DFA subsets. Do not retain a
        // transition whose key belongs to the discarded generation; the exact current
        // state is still carried forward and may be recomputed on a later match.
        if (!interned.cacheReset) {
          if (this.transitions.size >= PORTABLE_PATTERN_MAX_DFA_TRANSITIONS) {
            throw new PortablePatternWorkLimitError(
              "portable pattern DFA-transition limit exceeded",
            );
          }
          this.transitions.set(transitionKey, nextPendingId);
        }
      }
      pendingId = nextPendingId;
      offset += codePoint > 0xffff ? 2 : 1;
    }
  }

  private closure(
    pendingId: number,
    atStart: boolean,
    atEnd: boolean,
    computeWork: { remaining: number },
  ): ReadyState {
    const pending = this.pendingStates[pendingId];
    if (pending === undefined) throw new Error("invalid portable-regex DFA state");
    const stack = [...pending, this.start];
    const seen = new Uint8Array(this.states.length);
    const active: number[] = [];
    let accepted = false;
    while (stack.length > 0) {
      const stateIndex = stack.pop() as number;
      if (seen[stateIndex] === 1) continue;
      seen[stateIndex] = 1;
      this.chargeCompute(computeWork, 1);
      const state = this.states[stateIndex];
      if (state === undefined) throw new Error("invalid portable-regex NFA state");
      switch (state.kind) {
        case "accept":
          accepted = true;
          break;
        case "character":
          active.push(stateIndex);
          break;
        case "jump":
          if (state.next !== null) stack.push(state.next);
          break;
        case "split":
          if (state.first !== null) stack.push(state.first);
          if (state.second !== null) stack.push(state.second);
          break;
        case "start":
          if (atStart && state.next !== null) stack.push(state.next);
          break;
        case "end":
          if (atEnd && state.next !== null) stack.push(state.next);
          break;
      }
    }
    active.sort((left, right) => left - right);
    return { active, accepted };
  }

  private internPending(pending: number[]): {
    readonly identifier: number;
    readonly cacheReset: boolean;
  } {
    const key = pending.join(",");
    const existing = this.pendingIds.get(key);
    if (existing !== undefined) return { identifier: existing, cacheReset: false };
    let cacheReset = false;
    if (
      this.retainedSubsetMemberships + pending.length >
      PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS
    ) {
      this.resetDfaCache();
      cacheReset = true;
      const retained = this.pendingIds.get(key);
      if (retained !== undefined) return { identifier: retained, cacheReset };
    }
    if (this.pendingStates.length >= PORTABLE_PATTERN_MAX_DFA_STATES) {
      throw new PortablePatternWorkLimitError("portable pattern DFA-state limit exceeded");
    }
    // One pending subset contains at most one member per bounded NFA state, so it
    // must fit in the per-engine membership budget after any reset above.
    if (!this.retainSubsetMemberships(pending.length)) {
      throw new Error("portable pattern subset membership accounting drifted");
    }
    const identifier = this.pendingStates.length;
    this.pendingStates.push(pending);
    this.pendingIds.set(key, identifier);
    return { identifier, cacheReset };
  }

  private retainSubsetMemberships(amount: number): boolean {
    if (
      this.retainedSubsetMemberships + amount >
      PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS
    ) {
      return false;
    }
    this.retainedSubsetMemberships += amount;
    return true;
  }

  private resetDfaCache(): void {
    this.closures.clear();
    this.transitions.clear();
    this.pendingStates.splice(0, this.pendingStates.length, []);
    this.pendingIds.clear();
    this.pendingIds.set("", 0);
    this.retainedSubsetMemberships = 0;
  }

  private classIndex(codePoint: number): number {
    let low = 0;
    let high = this.boundaries.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if ((this.boundaries[middle] ?? 0) <= codePoint) low = middle + 1;
      else high = middle;
    }
    return low - 1;
  }

  private chargeCompute(computeWork: { remaining: number }, amount: number): void {
    computeWork.remaining -= amount;
    if (computeWork.remaining < 0) {
      throw new PortablePatternWorkLimitError("portable pattern match work limit exceeded");
    }
    if (validationWorkContext !== null) this.chargeValidation(validationWorkContext, amount);
  }

  private chargeValidation(context: ValidationWorkContext, amount: number): void {
    context.remaining -= amount;
    if (context.remaining < 0) {
      throw new PortablePatternWorkLimitError("portable pattern validation work limit exceeded");
    }
  }

  toString(): string {
    return `${PORTABLE_PATTERN_PROFILE}:${this.pattern}`;
  }

  transitionCount(): number {
    return this.transitions.size;
  }

  subsetMembershipCount(): number {
    return this.retainedSubsetMemberships;
  }
}

interface PortableRegExpEngine {
  (pattern: string, flags: string): PortableRegExp;
  readonly code: string;
}

const compiledPatternCache = new Map<string, PortableRegExp>();

function compiledPortablePattern(pattern: string): PortableRegExp {
  const cached = compiledPatternCache.get(pattern);
  if (cached !== undefined) {
    compiledPatternCache.delete(pattern);
    compiledPatternCache.set(pattern, cached);
    return cached;
  }
  const compiled = new PortableRegExp(pattern);
  compiledPatternCache.set(pattern, compiled);
  if (compiledPatternCache.size > PORTABLE_PATTERN_CACHE_SIZE) {
    const oldest = compiledPatternCache.keys().next().value;
    if (oldest !== undefined) compiledPatternCache.delete(oldest);
  }
  return compiled;
}

/** Return retained pattern, transition, and configured transition-cap counts. */
export function portablePatternCacheInfo(): {
  readonly patterns: number;
  readonly transitions: number;
  readonly maxTransitions: number;
  readonly memberships: number;
  readonly maxEngineMemberships: number;
  readonly maxMemberships: number;
  readonly maxMembershipsPerEngine: number;
} {
  const compiled = Array.from(compiledPatternCache.values());
  const memberships = compiled.map((pattern) => pattern.subsetMembershipCount());
  return {
    patterns: compiledPatternCache.size,
    transitions: compiled.reduce((total, compiled) => total + compiled.transitionCount(), 0),
    maxTransitions: PORTABLE_PATTERN_MAX_CACHED_DFA_TRANSITIONS,
    memberships: memberships.reduce((total, count) => total + count, 0),
    maxEngineMemberships: Math.max(0, ...memberships),
    maxMemberships: PORTABLE_PATTERN_MAX_CACHED_SUBSET_MEMBERSHIPS,
    maxMembershipsPerEngine: PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS,
  };
}

/** Ajv RegExpEngine adapter that routes every schema pattern through the linear NFA. */
export const portableRegExpEngine: PortableRegExpEngine = Object.assign(
  (pattern: string, flags: string): PortableRegExp => {
    if (flags !== "" && flags !== "u") {
      throw new PortablePatternError("unsupported regular-expression flags");
    }
    return compiledPortablePattern(pattern);
  },
  { code: "portableRegExpEngine" },
);

/** Return whether a pattern belongs to portable-regex-v1. */
export function isPortablePattern(pattern: string): boolean {
  try {
    portableRegExpEngine(pattern, "u");
  } catch (error) {
    if (error instanceof PortablePatternError) return false;
    throw error;
  }
  return true;
}

/** Apply the profile's unanchored Unicode-search semantics. */
export function portablePatternMatches(pattern: string, value: string): boolean {
  return portableRegExpEngine(pattern, "u").test(value);
}

export interface UnsupportedPattern {
  path: readonly (string | number)[];
  pattern: string;
}

interface SchemaChild {
  readonly path: readonly (string | number)[];
  readonly value: boolean | Record<string, unknown>;
}

function compareSchemaPaths(
  left: readonly (string | number)[],
  right: readonly (string | number)[],
): number {
  for (let index = 0; index < Math.min(left.length, right.length); index += 1) {
    const order = compareUnicodeCodePoints(String(left[index]), String(right[index]));
    if (order !== 0) return order;
  }
  return left.length - right.length;
}

function schemaChildren(
  value: Record<string, unknown>,
  path: readonly (string | number)[],
): SchemaChild[] {
  const children: SchemaChild[] = [];
  for (const keyword of schemaMapKeywords) {
    const mapping = value[keyword];
    if (!isRecord(mapping)) continue;
    for (const key of Object.keys(mapping)) {
      const child = mapping[key];
      if (isSchemaResource(child)) children.push({ path: [...path, keyword, key], value: child });
    }
  }
  for (const keyword of schemaArrayKeywords) {
    const items = value[keyword];
    if (!Array.isArray(items)) continue;
    for (const [index, child] of items.entries()) {
      if (isSchemaResource(child)) children.push({ path: [...path, keyword, index], value: child });
    }
  }
  for (const keyword of schemaSingleKeywords) {
    const child = value[keyword];
    if (isSchemaResource(child)) children.push({ path: [...path, keyword], value: child });
  }
  return children.sort((left, right) => compareSchemaPaths(left.path, right.path));
}

/** Find the first unsupported pattern in actual Draft 2020-12 schema positions. */
export function firstUnsupportedPattern(
  value: boolean | Record<string, unknown>,
  path: readonly (string | number)[] = [],
): UnsupportedPattern | null {
  let patternCount = 0;
  let codePointCount = 0;
  for (const candidate of schemaPatterns(value, path)) {
    patternCount += 1;
    codePointCount += Array.from(candidate.pattern).length;
    if (
      patternCount > PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS ||
      codePointCount > PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS ||
      !isPortablePattern(candidate.pattern)
    ) {
      return candidate;
    }
  }
  return null;
}

function* schemaPatterns(
  value: boolean | Record<string, unknown>,
  path: readonly (string | number)[],
): Generator<UnsupportedPattern> {
  if (typeof value === "boolean") return;

  const pattern = value.pattern;
  if (typeof pattern === "string") yield { path: [...path, "pattern"], pattern };
  const patternProperties = value.patternProperties;
  if (isRecord(patternProperties)) {
    for (const candidate of Object.keys(patternProperties).sort(compareUnicodeCodePoints)) {
      yield {
        path: [...path, "patternProperties", candidate],
        pattern: candidate,
      };
    }
  }

  for (const child of schemaChildren(value, path)) {
    yield* schemaPatterns(child.value, child.path);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSchemaResource(value: unknown): value is boolean | Record<string, unknown> {
  return typeof value === "boolean" || isRecord(value);
}
