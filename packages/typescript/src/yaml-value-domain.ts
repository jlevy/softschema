/** Bounded parsing and normalization for softschema's portable YAML value domain. */
import {
  Composer,
  CST,
  isAlias,
  isMap,
  isScalar,
  isSeq,
  LineCounter,
  type ParsedNode,
  Parser,
  type Scalar,
} from "yaml";

const MAX_SAFE_INTEGER = 9_007_199_254_740_991;
const MAX_SAFE_INTEGER_BIGINT = 9_007_199_254_740_991n;
const MIB = 1024 * 1024;

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

/** Resource budgets applied at untrusted artifact and schema boundaries. */
export interface ValidationLimits {
  maxResourceBytes: number;
  maxBundleBytes: number;
  maxResources: number;
  maxNodesPerResource: number;
  maxDepth: number;
  maxScalarCodePoints: number;
}

/** Trusted per-call overrides; omitted fields retain the portable defaults. */
export type ValidationLimitOverrides = Partial<ValidationLimits>;

export const DEFAULT_VALIDATION_LIMITS: Readonly<ValidationLimits> = Object.freeze({
  maxResourceBytes: 8 * MIB,
  maxBundleBytes: 64 * MIB,
  maxResources: 256,
  maxNodesPerResource: 100_000,
  maxDepth: 128,
  maxScalarCodePoints: MIB,
});

/** Base class for stable portable-YAML boundary failures. */
export class PortableYamlError extends Error {
  readonly path: string;
  readonly line: number | null;
  readonly column: number | null;

  constructor(
    message: string,
    options: { path?: string; line?: number | null; column?: number | null } = {},
  ) {
    super(message);
    this.path = options.path ?? "";
    this.line = options.line ?? null;
    this.column = options.column ?? null;
  }
}

/** The input is not a single syntactically valid YAML document. */
export class PortableYamlSyntaxError extends PortableYamlError {}

/** The input is outside the bounded JSON-compatible value domain. */
export class PortableValueError extends PortableYamlError {}

interface Budget {
  limits: ValidationLimits;
  nodes: number;
}

interface PendingCstNode {
  token: CST.Token | null | undefined;
  path: readonly (string | number)[];
  depth: number;
}

interface NormalizedValue {
  value: JsonValue;
  sizeBytes: number;
}

const nullValues = new Set(["", "~", "null", "Null", "NULL"]);
const trueValues = new Set(["true", "True", "TRUE"]);
const falseValues = new Set(["false", "False", "FALSE"]);
const integerPattern = /^[-+]?(?:0|[1-9][0-9_]*|0o[0-7_]+|0x[0-9a-fA-F_]+)$/;
const floatPattern = new RegExp(
  "^[-+]?(?:(?:[0-9][0-9_]*)?\\.[0-9_]+(?:[eE][-+]?[0-9]+)?|" +
    "[0-9][0-9_]*(?:\\.[0-9_]*)?[eE][-+]?[0-9]+|" +
    "\\.(?:inf|Inf|INF|nan|NaN|NAN))$",
);
const stringTag = "tag:yaml.org,2002:str";
const nullTag = "tag:yaml.org,2002:null";
const booleanTag = "tag:yaml.org,2002:bool";
const integerTag = "tag:yaml.org,2002:int";
const floatTag = "tag:yaml.org,2002:float";
const mapTag = "tag:yaml.org,2002:map";
const sequenceTag = "tag:yaml.org,2002:seq";

/** Resolve and validate caller-provided limit overrides. */
export function resolveValidationLimits(
  overrides: ValidationLimitOverrides = {},
): ValidationLimits {
  const limits = { ...DEFAULT_VALIDATION_LIMITS, ...overrides };
  const nonnegative = ["maxResourceBytes", "maxBundleBytes", "maxScalarCodePoints"] as const;
  const positive = ["maxResources", "maxNodesPerResource", "maxDepth"] as const;
  for (const name of [...nonnegative, ...positive]) {
    if (!Number.isSafeInteger(limits[name])) throw new TypeError(`${name} must be an integer`);
  }
  for (const name of nonnegative) {
    if (limits[name] < 0) throw new RangeError(`${name} must be nonnegative`);
  }
  for (const name of positive) {
    if (limits[name] < 1) throw new RangeError(`${name} must be positive`);
  }
  return limits;
}

/** Parse one YAML document after a CST limit pass and before ordinary object creation. */
export function parsePortableYaml(
  text: string,
  validationLimits: ValidationLimitOverrides = {},
  options: { encodedSize?: number; lineOffset?: number } = {},
): JsonValue {
  const limits = resolveValidationLimits(validationLimits);
  const encodedSize = options.encodedSize ?? utf8Size(text);
  if (encodedSize > limits.maxResourceBytes) {
    throw new PortableValueError("maximum resource size exceeded");
  }

  const lineCounter = new LineCounter();
  const parser = new Parser((offset) => lineCounter.addNewLine(offset));
  const tokens = [...parser.parse(text)];
  const errorToken = tokens.find((token) => token.type === "error");
  if (errorToken !== undefined) {
    throw syntaxErrorAt("invalid YAML syntax", errorToken.offset, lineCounter, options.lineOffset);
  }
  const documents = tokens.filter((token): token is CST.Document => token.type === "document");
  if (documents.length === 0) {
    const budget: Budget = { limits, nodes: 0 };
    countNode(budget, [], 1);
    return null;
  }
  const document = documents[0];
  if (documents.length !== 1 || document === undefined) {
    throw new PortableYamlSyntaxError("exactly one YAML document is required");
  }
  preflightCst(document, limits, lineCounter, options.lineOffset ?? 0);

  const composer = new Composer({
    keepSourceTokens: true,
    lineCounter,
    logLevel: "silent",
    prettyErrors: false,
    schema: "core",
    strict: true,
    uniqueKeys: false,
  });
  const composed = [...composer.compose(tokens, true, text.length)];
  if (composed.length !== 1 || composed[0] === undefined || composed[0].errors.length > 0) {
    const first = composed[0]?.errors[0];
    const offset = first?.pos[0] ?? 0;
    throw syntaxErrorAt("invalid YAML syntax", offset, lineCounter, options.lineOffset);
  }
  return materializeNode(composed[0].contents, [], lineCounter, options.lineOffset ?? 0);
}

/** Normalize an already-materialized value and return its compact canonical JSON size. */
export function normalizePortableValue(
  value: unknown,
  validationLimits: ValidationLimitOverrides = {},
  encodedSize?: number,
): NormalizedValue {
  const limits = resolveValidationLimits(validationLimits);
  if (encodedSize !== undefined && encodedSize > limits.maxResourceBytes) {
    throw new PortableValueError("maximum resource size exceeded");
  }
  const budget: Budget = { limits, nodes: 0 };
  const normalized = normalizeMaterialized(value, [], 1, budget, new Set());
  const sizeBytes = encodedSize ?? canonicalPortableJsonSize(normalized);
  if (sizeBytes > limits.maxResourceBytes) {
    throw new PortableValueError("maximum resource size exceeded");
  }
  return { value: normalized, sizeBytes };
}

/** Return the UTF-8 size of compact JSON with recursively sorted object keys. */
export function canonicalPortableJsonSize(value: JsonValue): number {
  if (value === null) return 4;
  if (typeof value === "boolean") return value ? 4 : 5;
  if (typeof value === "number") return canonicalNumberText(value).length;
  if (typeof value === "string") return utf8Size(JSON.stringify(value));
  if (Array.isArray(value)) {
    return (
      2 +
      Math.max(0, value.length - 1) +
      value.reduce<number>((size, item) => size + canonicalPortableJsonSize(item), 0)
    );
  }
  const keys = Object.keys(value).sort();
  return (
    2 +
    Math.max(0, keys.length - 1) +
    keys.reduce<number>(
      (size, key) =>
        size +
        utf8Size(JSON.stringify(key)) +
        1 +
        canonicalPortableJsonSize(value[key] as JsonValue),
      0,
    )
  );
}

function preflightCst(
  document: CST.Document,
  limits: ValidationLimits,
  lineCounter: LineCounter,
  lineOffset: number,
): void {
  const budget: Budget = { limits, nodes: 0 };
  const stack: PendingCstNode[] = [{ token: document.value, path: [], depth: 1 }];
  while (stack.length > 0) {
    const pending = stack.pop();
    if (pending === undefined) break;
    countNode(budget, pending.path, pending.depth, pending.token?.offset, lineCounter, lineOffset);
    const token = pending.token;
    if (token === null || token === undefined) continue;
    if (token.type === "alias") {
      throw valueErrorAt(
        "aliases are not portable",
        pending.path,
        token.offset,
        lineCounter,
        lineOffset,
      );
    }
    if (isCstScalar(token)) {
      const scalar = CST.resolveAsScalar(token, true);
      if (scalar !== null && [...scalar.value].length > limits.maxScalarCodePoints) {
        throw valueErrorAt(
          "maximum scalar size exceeded",
          pending.path,
          token.offset,
          lineCounter,
          lineOffset,
        );
      }
      if (scalar !== null && hasUnpairedSurrogate(scalar.value)) {
        throw valueErrorAt(
          "string contains an invalid Unicode scalar",
          pending.path,
          token.offset,
          lineCounter,
          lineOffset,
        );
      }
      continue;
    }
    if (token.type === "block-map") {
      pushMapItems(stack, token.items, pending.path, pending.depth);
      continue;
    }
    if (token.type === "block-seq") {
      pushSequenceItems(stack, token.items, pending.path, pending.depth);
      continue;
    }
    if (token.type === "flow-collection") {
      if (token.start.type === "flow-map-start") {
        pushMapItems(stack, token.items, pending.path, pending.depth);
      } else {
        pushSequenceItems(stack, token.items, pending.path, pending.depth);
      }
    }
  }
}

function pushMapItems(
  stack: PendingCstNode[],
  items: CST.CollectionItem[],
  parentPath: readonly (string | number)[],
  parentDepth: number,
): void {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if (item === undefined || (item.key === undefined && item.sep === undefined)) continue;
    const key = cstKeyText(item.key);
    const valuePath = key === null ? parentPath : [...parentPath, key];
    stack.push({ token: item.value, path: valuePath, depth: parentDepth + 1 });
    stack.push({ token: item.key, path: parentPath, depth: parentDepth + 1 });
  }
}

function pushSequenceItems(
  stack: PendingCstNode[],
  items: CST.CollectionItem[],
  parentPath: readonly (string | number)[],
  parentDepth: number,
): void {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if (item === undefined) continue;
    stack.push({
      token: item.value,
      path: [...parentPath, index],
      depth: parentDepth + 1,
    });
  }
}

function cstKeyText(token: CST.Token | null | undefined): string | null {
  if (token === null || token === undefined || !isCstScalar(token)) return null;
  return CST.resolveAsScalar(token, true)?.value ?? null;
}

function isCstScalar(token: CST.Token): token is CST.FlowScalar | CST.BlockScalar {
  return (
    token.type === "scalar" ||
    token.type === "single-quoted-scalar" ||
    token.type === "double-quoted-scalar" ||
    token.type === "block-scalar"
  );
}

function materializeNode(
  node: ParsedNode | null,
  path: readonly (string | number)[],
  lineCounter: LineCounter,
  lineOffset: number,
): JsonValue {
  if (node === null) return null;
  if (isAlias(node)) {
    throw valueErrorAt("aliases are not portable", path, node.range[0], lineCounter, lineOffset);
  }
  if (isScalar(node)) return materializeScalar(node, path, lineCounter, lineOffset);
  if (isSeq(node)) {
    if (node.tag !== undefined && node.tag !== sequenceTag) {
      throw valueErrorAt(
        "tagged sequences are not portable",
        path,
        node.range[0],
        lineCounter,
        lineOffset,
      );
    }
    return node.items.map((item, index) =>
      materializeNode(item, [...path, index], lineCounter, lineOffset),
    );
  }
  if (isMap(node)) {
    if (node.tag !== undefined && node.tag !== mapTag) {
      throw valueErrorAt(
        "tagged mappings are not portable",
        path,
        node.range[0],
        lineCounter,
        lineOffset,
      );
    }
    const result: Record<string, JsonValue> = {};
    for (const pair of node.items) {
      if (!isScalar(pair.key)) {
        const offset = "range" in pair.key ? pair.key.range[0] : node.range[0];
        throw valueErrorAt("mapping keys must be strings", path, offset, lineCounter, lineOffset);
      }
      if (pair.key.type === "PLAIN" && pair.key.tag === undefined && pair.key.source === "<<") {
        throw valueErrorAt(
          "merge keys are not portable",
          path,
          pair.key.range[0],
          lineCounter,
          lineOffset,
        );
      }
      const key = materializeScalar(pair.key, path, lineCounter, lineOffset);
      if (typeof key !== "string") {
        throw valueErrorAt(
          "mapping keys must be strings",
          path,
          pair.key.range[0],
          lineCounter,
          lineOffset,
        );
      }
      const valuePath = [...path, key];
      if (Object.hasOwn(result, key)) {
        throw valueErrorAt(
          "duplicate mapping key",
          valuePath,
          pair.key.range[0],
          lineCounter,
          lineOffset,
        );
      }
      Object.defineProperty(result, key, {
        configurable: true,
        enumerable: true,
        value: materializeNode(pair.value, valuePath, lineCounter, lineOffset),
        writable: true,
      });
    }
    return result;
  }
  throw new PortableValueError("value is not JSON-compatible", { path: jsonPointer(path) });
}

function materializeScalar(
  node: Scalar.Parsed,
  path: readonly (string | number)[],
  lineCounter: LineCounter,
  lineOffset: number,
): JsonValue {
  const tag = node.tag;
  const source = node.source ?? String(node.value ?? "");
  if (tag === stringTag || (tag === undefined && node.type !== "PLAIN")) return String(node.value);
  if (tag !== undefined && ![nullTag, booleanTag, integerTag, floatTag].includes(tag)) {
    throw valueErrorAt("YAML tag is not portable", path, node.range[0], lineCounter, lineOffset);
  }
  if (tag === nullTag) return null;
  if (tag === booleanTag) {
    if (trueValues.has(source)) return true;
    if (falseValues.has(source)) return false;
    throw valueErrorAt("invalid boolean scalar", path, node.range[0], lineCounter, lineOffset);
  }
  if (tag === integerTag) return parseInteger(source, path, node.range[0], lineCounter, lineOffset);
  if (tag === floatTag) return parseYamlFloat(source, path, node.range[0], lineCounter, lineOffset);

  if (nullValues.has(source)) return null;
  if (trueValues.has(source)) return true;
  if (falseValues.has(source)) return false;
  if (integerPattern.test(source)) {
    return parseInteger(source, path, node.range[0], lineCounter, lineOffset);
  }
  if (floatPattern.test(source)) {
    return parseYamlFloat(source, path, node.range[0], lineCounter, lineOffset);
  }
  return String(node.value);
}

function parseInteger(
  source: string,
  path: readonly (string | number)[],
  offset: number,
  lineCounter: LineCounter,
  lineOffset: number,
): number {
  const cleaned = source.replaceAll("_", "");
  const negative = cleaned.startsWith("-");
  const unsigned = cleaned.replace(/^[-+]/, "");
  let base = 10;
  let digits = unsigned;
  if (unsigned.startsWith("0o")) {
    base = 8;
    digits = unsigned.slice(2);
  } else if (unsigned.startsWith("0x")) {
    base = 16;
    digits = unsigned.slice(2);
  }
  const significant = digits.replace(/^0+/, "");
  if (significant === "") return 0;
  const safeDigits = base === 10 ? 16 : base === 8 ? 18 : 13;
  if (significant.length > safeDigits) {
    throw valueErrorAt("integer is outside the safe range", path, offset, lineCounter, lineOffset);
  }
  const magnitude = BigInt(base === 10 ? digits : `${base === 8 ? "0o" : "0x"}${digits}`);
  const value = negative ? -magnitude : magnitude;
  if (value < -MAX_SAFE_INTEGER_BIGINT || value > MAX_SAFE_INTEGER_BIGINT) {
    throw valueErrorAt("integer is outside the safe range", path, offset, lineCounter, lineOffset);
  }
  return Number(value);
}

function parseYamlFloat(
  source: string,
  path: readonly (string | number)[],
  offset: number,
  lineCounter: LineCounter,
  lineOffset: number,
): number {
  const cleaned = source.replaceAll("_", "");
  if ([".inf", ".nan"].includes(cleaned.replace(/^[-+]/, "").toLowerCase())) {
    throw valueErrorAt("number must be finite", path, offset, lineCounter, lineOffset);
  }
  const exactInteger = exactDecimalInteger(cleaned);
  if (exactInteger !== null) {
    if (exactInteger < -MAX_SAFE_INTEGER_BIGINT || exactInteger > MAX_SAFE_INTEGER_BIGINT) {
      throw valueErrorAt(
        "integer is outside the safe range",
        path,
        offset,
        lineCounter,
        lineOffset,
      );
    }
    return Number(exactInteger);
  }
  const value = Number(cleaned);
  if (!Number.isFinite(value)) {
    throw valueErrorAt("number must be finite", path, offset, lineCounter, lineOffset);
  }
  if (Number.isInteger(value) && Math.abs(value) > MAX_SAFE_INTEGER) {
    throw valueErrorAt(
      "rounded integer is outside the safe range",
      path,
      offset,
      lineCounter,
      lineOffset,
    );
  }
  return Object.is(value, -0) ? 0 : value;
}

function exactDecimalInteger(source: string): bigint | null {
  const negative = source.startsWith("-");
  const unsigned = source.replace(/^[-+]/, "");
  const exponentIndex = unsigned.search(/[eE]/);
  const mantissa = exponentIndex === -1 ? unsigned : unsigned.slice(0, exponentIndex);
  const exponentSource = exponentIndex === -1 ? "0" : unsigned.slice(exponentIndex + 1);
  const dotIndex = mantissa.indexOf(".");
  const integerPart = dotIndex === -1 ? mantissa : mantissa.slice(0, dotIndex);
  const fractionalPart = dotIndex === -1 ? "" : mantissa.slice(dotIndex + 1);
  const digits = `${integerPart || "0"}${fractionalPart}`;
  if (/^0+$/.test(digits)) return 0n;
  const exponent = clampedExponent(exponentSource, digits.length + 20);
  const decimalPosition = (integerPart || "0").length + exponent;
  if (decimalPosition <= 0) return null;
  if (decimalPosition < digits.length && /[^0]/.test(digits.slice(decimalPosition))) return null;

  let integerDigits: string;
  if (decimalPosition >= digits.length) {
    const significant = digits.replace(/^0+/, "");
    const finalLength = significant.length + decimalPosition - digits.length;
    if (finalLength > 16) return negative ? -10_000_000_000_000_000n : 10_000_000_000_000_000n;
    integerDigits = `${digits}${"0".repeat(decimalPosition - digits.length)}`;
  } else {
    integerDigits = digits.slice(0, decimalPosition);
  }
  const magnitude = BigInt(integerDigits || "0");
  return negative ? -magnitude : magnitude;
}

function clampedExponent(source: string, maximum: number): number {
  const negative = source.startsWith("-");
  const digits = source.replace(/^[-+]/, "").replace(/^0+/, "") || "0";
  const magnitude =
    digits.length > String(maximum).length ? maximum : Math.min(Number(digits), maximum);
  return negative ? -magnitude : magnitude;
}

function normalizeMaterialized(
  value: unknown,
  path: readonly (string | number)[],
  depth: number,
  budget: Budget,
  active: Set<object>,
): JsonValue {
  countNode(budget, path, depth);
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "string") {
    if ([...value].length > budget.limits.maxScalarCodePoints) {
      throw new PortableValueError("maximum scalar size exceeded", { path: jsonPointer(path) });
    }
    if (hasUnpairedSurrogate(value)) {
      throw new PortableValueError("string contains an invalid Unicode scalar", {
        path: jsonPointer(path),
      });
    }
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new PortableValueError("number must be finite", { path: jsonPointer(path) });
    }
    if (Number.isInteger(value) && !Number.isSafeInteger(value)) {
      throw new PortableValueError("integer is outside the safe range", {
        path: jsonPointer(path),
      });
    }
    return Object.is(value, -0) ? 0 : value;
  }
  if (typeof value !== "object" || value === undefined) {
    throw new PortableValueError("value is not JSON-compatible", { path: jsonPointer(path) });
  }
  if (active.has(value)) {
    throw new PortableValueError("cycles are not portable", { path: jsonPointer(path) });
  }
  active.add(value);
  try {
    if (Array.isArray(value)) {
      return value.map((item, index) =>
        normalizeMaterialized(item, [...path, index], depth + 1, budget, active),
      );
    }
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new PortableValueError("value is not JSON-compatible", { path: jsonPointer(path) });
    }
    const result: Record<string, JsonValue> = {};
    // Match the materialized JSON object surface: hidden and symbol metadata is
    // outside the value, just as it is for JSON.stringify and Object.keys. This
    // matters for Zod-generated schemas, which carry non-enumerable ~standard
    // metadata. Enumerable accessors remain forbidden so normalization never
    // invokes user code at this trust boundary.
    for (const key of Object.keys(value)) {
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (descriptor === undefined || !("value" in descriptor)) {
        throw new PortableValueError("value is not JSON-compatible", {
          path: jsonPointer([...path, key]),
        });
      }
      countNode(budget, path, depth + 1);
      if ([...key].length > budget.limits.maxScalarCodePoints) {
        throw new PortableValueError("maximum scalar size exceeded", { path: jsonPointer(path) });
      }
      if (hasUnpairedSurrogate(key)) {
        throw new PortableValueError("string contains an invalid Unicode scalar", {
          path: jsonPointer(path),
        });
      }
      Object.defineProperty(result, key, {
        configurable: true,
        enumerable: true,
        value: normalizeMaterialized(descriptor.value, [...path, key], depth + 1, budget, active),
        writable: true,
      });
    }
    return result;
  } finally {
    active.delete(value);
  }
}

function canonicalNumberText(value: number): string {
  const absolute = Math.abs(value);
  if (absolute > 0 && absolute < 1e-4 && !Number.isInteger(value)) {
    const [mantissa, rawExponent] = value.toExponential().split("e") as [string, string];
    const negative = rawExponent.startsWith("-");
    const digits = rawExponent.replace(/^[-+]/, "").padStart(2, "0");
    return `${mantissa}e${negative ? "-" : "+"}${digits}`;
  }
  return String(value);
}

function hasUnpairedSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (next < 0xdc00 || next > 0xdfff) return true;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true;
    }
  }
  return false;
}

function countNode(
  budget: Budget,
  path: readonly (string | number)[],
  depth: number,
  offset?: number,
  lineCounter?: LineCounter,
  lineOffset = 0,
): void {
  if (depth > budget.limits.maxDepth) {
    throw valueErrorAt("maximum depth exceeded", path, offset, lineCounter, lineOffset);
  }
  budget.nodes += 1;
  if (budget.nodes > budget.limits.maxNodesPerResource) {
    throw valueErrorAt("maximum node count exceeded", path, offset, lineCounter, lineOffset);
  }
}

function valueErrorAt(
  message: string,
  path: readonly (string | number)[],
  offset?: number,
  lineCounter?: LineCounter,
  lineOffset = 0,
): PortableValueError {
  const position =
    offset === undefined || lineCounter === undefined ? null : lineCounter.linePos(offset);
  return new PortableValueError(message, {
    path: jsonPointer(path),
    line: position === null ? null : position.line + lineOffset,
    column: position?.col ?? null,
  });
}

function syntaxErrorAt(
  message: string,
  offset: number,
  lineCounter: LineCounter,
  lineOffset = 0,
): PortableYamlSyntaxError {
  const position = lineCounter.linePos(offset);
  return new PortableYamlSyntaxError(message, {
    line: position.line + lineOffset,
    column: position.col,
  });
}

function jsonPointer(path: readonly (string | number)[]): string {
  return path.map((part) => `/${String(part).replace(/~/g, "~0").replace(/\//g, "~1")}`).join("");
}

function utf8Size(value: string): number {
  return new TextEncoder().encode(value).byteLength;
}
