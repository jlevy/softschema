/** Portable JSON Schema regular-expression profile (ECMA-262 Unicode/search semantics). */

export const PORTABLE_PATTERN_PROFILE = "portable-regex-v1";
export const PORTABLE_PATTERN_MAX_QUANTIFIER = 1000;

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

interface ClassAtom {
  codePoint: number | null;
  directOperator: string | null;
}

class Parser {
  private index = 0;

  constructor(private readonly pattern: string) {}

  parse(): void {
    this.expression(null);
    if (this.index !== this.pattern.length) {
      throw new PortablePatternError("unexpected trailing pattern syntax");
    }
    try {
      new RegExp(this.pattern, "u");
    } catch {
      throw new PortablePatternError("pattern does not compile");
    }
  }

  private expression(terminator: string | null): void {
    while (this.index < this.pattern.length) {
      const current = this.peek();
      if (terminator !== null && current === terminator) return;
      if (current === "|") {
        this.take();
        continue;
      }
      this.piece();
    }
    if (terminator !== null) throw new PortablePatternError("unterminated group");
  }

  private piece(): void {
    const quantifiable = this.atom();
    const current = this.peek();
    if (current === null || !"*+?{".includes(current)) return;
    if (!quantifiable) throw new PortablePatternError("assertions cannot be quantified");
    this.quantifier();
  }

  private atom(): boolean {
    const current = this.peek();
    if (current === null) throw new PortablePatternError("expected an atom");
    if (current === "(") {
      this.take();
      if (this.pattern.startsWith("?:", this.index)) {
        this.index += 2;
      } else if (this.peek() === "?") {
        throw new PortablePatternError("unsupported group construct");
      }
      this.expression(")");
      this.take();
      return true;
    }
    if (current === "[") {
      this.characterClass();
      return true;
    }
    if (current === "\\") {
      this.escape(false);
      return true;
    }
    if (current === ".") {
      this.take();
      return true;
    }
    if (current === "^" || current === "$") {
      this.take();
      return false;
    }
    if (")]*+?{}]".includes(current)) {
      throw new PortablePatternError("unexpected pattern syntax");
    }
    const codePoint = current.codePointAt(0);
    if (codePoint !== undefined && codePoint >= 0xd800 && codePoint <= 0xdfff) {
      throw new PortablePatternError("surrogate literals are unsupported");
    }
    this.take();
    return true;
  }

  private characterClass(): void {
    this.take();
    if (this.peek() === "^") this.take();

    let itemCount = 0;
    let previousOperator: string | null = null;
    while (this.peek() !== null && this.peek() !== "]") {
      let start: ClassAtom;
      if (this.peek() === "-" && (itemCount === 0 || this.peekAt(this.index + 1) === "]")) {
        this.take();
        start = { codePoint: "-".codePointAt(0) ?? null, directOperator: null };
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
        previousOperator = end.directOperator;
      }
    }
    if (this.peek() !== "]" || itemCount === 0) {
      throw new PortablePatternError("unterminated or empty character class");
    }
    this.take();
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
    return {
      codePoint: codePoint ?? null,
      directOperator: "&|~".includes(current) ? current : null,
    };
  }

  private escape(inClass: boolean): ClassAtom {
    this.take();
    const escaped = this.take();
    if (escaped === null) throw new PortablePatternError("dangling escape");

    if ("dDwW".includes(escaped)) return { codePoint: null, directOperator: null };
    if ("sS".includes(escaped)) {
      if (inClass) {
        throw new PortablePatternError("whitespace complements in classes are unsupported");
      }
      return { codePoint: null, directOperator: null };
    }
    if ("nrtfv".includes(escaped)) {
      const codePoints: Record<string, number> = { n: 10, r: 13, t: 9, f: 12, v: 11 };
      return { codePoint: codePoints[escaped] ?? null, directOperator: null };
    }
    if (escaped === "x") {
      return { codePoint: Number.parseInt(this.hex(2), 16), directOperator: null };
    }
    if (escaped === "u") {
      const codePoint = Number.parseInt(this.hex(4), 16);
      if (codePoint >= 0xd800 && codePoint <= 0xdfff) {
        throw new PortablePatternError("surrogate escapes are unsupported");
      }
      return { codePoint, directOperator: null };
    }

    const allowed = inClass ? escapedSyntaxClass : escapedSyntaxOutside;
    if (!allowed.has(escaped)) throw new PortablePatternError("unsupported escape");
    return { codePoint: escaped.codePointAt(0) ?? null, directOperator: null };
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

  private quantifier(): void {
    const current = this.peek();
    if (current !== null && "*+?".includes(current)) {
      this.take();
    } else {
      this.take();
      const minimum = this.bound();
      let maximum: number | null = minimum;
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
  }

  private bound(): number {
    const start = this.index;
    while (this.peek() !== null && /^[0-9]$/.test(this.peek() as string)) this.take();
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

/** Return whether a pattern belongs to portable-regex-v1. */
export function isPortablePattern(pattern: string): boolean {
  try {
    new Parser(pattern).parse();
  } catch (error) {
    if (error instanceof PortablePatternError) return false;
    throw error;
  }
  return true;
}

/** Apply the profile's unanchored Unicode-search semantics. */
export function portablePatternMatches(pattern: string, value: string): boolean {
  new Parser(pattern).parse();
  return new RegExp(pattern, "u").test(value);
}

export interface UnsupportedPattern {
  path: readonly (string | number)[];
  pattern: string;
}

/** Find the first unsupported pattern in actual Draft 2020-12 schema positions. */
export function firstUnsupportedPattern(
  value: boolean | Record<string, unknown>,
  path: readonly (string | number)[] = [],
): UnsupportedPattern | null {
  if (typeof value === "boolean") return null;

  const pattern = value.pattern;
  if (typeof pattern === "string" && !isPortablePattern(pattern)) {
    return { path: [...path, "pattern"], pattern };
  }
  const patternProperties = value.patternProperties;
  if (isRecord(patternProperties)) {
    for (const candidate of Object.keys(patternProperties).sort()) {
      if (!isPortablePattern(candidate)) {
        return { path: [...path, "patternProperties", candidate], pattern: candidate };
      }
    }
  }

  for (const keyword of [...schemaMapKeywords].sort()) {
    const mapping = value[keyword];
    if (!isRecord(mapping)) continue;
    for (const key of Object.keys(mapping).sort()) {
      const child = mapping[key];
      if (!isSchemaResource(child)) continue;
      const nested = firstUnsupportedPattern(child, [...path, keyword, key]);
      if (nested !== null) return nested;
    }
  }
  for (const keyword of [...schemaArrayKeywords].sort()) {
    const items = value[keyword];
    if (!Array.isArray(items)) continue;
    for (const [index, child] of items.entries()) {
      if (!isSchemaResource(child)) continue;
      const nested = firstUnsupportedPattern(child, [...path, keyword, index]);
      if (nested !== null) return nested;
    }
  }
  for (const keyword of [...schemaSingleKeywords].sort()) {
    const child = value[keyword];
    if (!isSchemaResource(child)) continue;
    const nested = firstUnsupportedPattern(child, [...path, keyword]);
    if (nested !== null) return nested;
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSchemaResource(value: unknown): value is boolean | Record<string, unknown> {
  return typeof value === "boolean" || isRecord(value);
}
