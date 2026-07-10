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
  YAMLParseError as YamlLibraryParseError,
} from "yaml";
import {
  jsonPointer,
  type NodeSource,
  SourceMap,
  type SourcePoint,
  type SourceSpan,
  SourceText,
} from "./core/source-map.js";
import {
  type JsonValue,
  PortableValueError,
  PortableYamlSyntaxError,
  resolveValidationLimits,
  type ValidationLimitOverrides,
  type ValidationLimits,
} from "./core/value-domain.js";

export {
  canonicalPortableJsonSize,
  DEFAULT_VALIDATION_LIMITS,
  type JsonObject,
  type JsonValue,
  type NormalizedValue,
  normalizePortableValue,
  PortableValueError,
  PortableYamlError,
  PortableYamlSyntaxError,
  resolveValidationLimits,
  type ValidationLimitOverrides,
  type ValidationLimits,
} from "./core/value-domain.js";

const MAX_SAFE_INTEGER = 9_007_199_254_740_991;
const MAX_SAFE_INTEGER_BIGINT = 9_007_199_254_740_991n;
interface Budget {
  limits: ValidationLimits;
  nodes: number;
}

interface PendingCstNode {
  token: CST.Token | null | undefined;
  path: readonly (string | number)[];
  depth: number;
  offset?: number;
  countOnly?: boolean;
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
const nonportableSourceSeparators = new Set(["\u0085", "\u2028", "\u2029"]);
const nonportableSourceSeparatorMessage = "literal YAML source line separator is not portable";
const flowDelimiters = new Set([",", "]", "}"]);
const compactFlowColonMessage = "plain compact flow mapping values must be separated after ':'";

export interface ParsedPortableYaml {
  readonly value: JsonValue;
  readonly sourceMap: SourceMap;
}

/** Parse one YAML document after a CST limit pass and before ordinary object creation. */
export function parsePortableYaml(
  text: string,
  validationLimits: ValidationLimitOverrides = {},
  options: { encodedSize?: number; lineOffset?: number } = {},
): JsonValue {
  return parsePortableYamlWithLocations(text, validationLimits, options).value;
}

/** Parse portable YAML once and retain immutable key/value source spans. */
export function parsePortableYamlWithLocations(
  text: string,
  validationLimits: ValidationLimitOverrides = {},
  options: { encodedSize?: number; lineOffset?: number } = {},
): ParsedPortableYaml {
  const limits = resolveValidationLimits(validationLimits);
  const encodedSize = options.encodedSize ?? utf8Size(text);
  if (encodedSize > limits.maxResourceBytes) {
    throw new PortableValueError("maximum resource size exceeded");
  }

  const lineCounter = new LineCounter();
  const sourceText = new SourceText(text, options.lineOffset ?? 0);
  rejectNonportableSourceSeparators(text, sourceText);
  const parser = new Parser((offset) => lineCounter.addNewLine(offset));
  const tokens = normalizeYamlLibraryErrors(() => [...parser.parse(text)], sourceText);
  const errorToken = tokens.find((token) => token.type === "error");
  if (errorToken !== undefined) {
    throw syntaxErrorAt("invalid YAML syntax", errorToken.offset, sourceText);
  }
  const documents = tokens.filter((token): token is CST.Document => token.type === "document");
  if (documents.length === 0) {
    const budget: Budget = { limits, nodes: 0 };
    countNode(budget, [], 1);
    const point = sourceText.point(0);
    return {
      value: null,
      sourceMap: new SourceMap([["", { value: { start: point, end: point } }]]),
    };
  }
  const document = documents[0];
  if (documents.length !== 1 || document === undefined) {
    throw new PortableYamlSyntaxError("exactly one YAML document is required");
  }
  normalizeYamlLibraryErrors(() => preflightCst(document, limits, text, sourceText), sourceText);

  const composer = new Composer({
    keepSourceTokens: true,
    lineCounter,
    logLevel: "silent",
    prettyErrors: false,
    schema: "core",
    strict: true,
    uniqueKeys: false,
  });
  const composed = normalizeYamlLibraryErrors(
    () => [...composer.compose(tokens, true, text.length)],
    sourceText,
  );
  if (composed.length !== 1 || composed[0] === undefined || composed[0].errors.length > 0) {
    const first = composed[0]?.errors[0];
    const offset = first?.pos[0] ?? 0;
    throw syntaxErrorAt("invalid YAML syntax", offset, sourceText);
  }
  const locations = new Map<string, NodeSource>();
  const value = materializeNode(composed[0].contents, [], text, sourceText, locations);
  return { value, sourceMap: new SourceMap(locations) };
}

function normalizeYamlLibraryErrors<T>(operation: () => T, sourceText: SourceText): T {
  try {
    return operation();
  } catch (error) {
    if (error instanceof YamlLibraryParseError) {
      throw syntaxErrorAt("invalid YAML syntax", error.pos[0], sourceText);
    }
    throw error;
  }
}

function rejectNonportableSourceSeparators(text: string, sourceText: SourceText): void {
  for (let offset = 0; offset < text.length; ) {
    const codePoint = text.codePointAt(offset) as number;
    const character = String.fromCodePoint(codePoint);
    if (nonportableSourceSeparators.has(character)) {
      throw valueErrorAt(nonportableSourceSeparatorMessage, [], offset, sourceText);
    }
    offset += codePoint > 0xffff ? 2 : 1;
  }
}

function preflightCst(
  document: CST.Document,
  limits: ValidationLimits,
  text: string,
  sourceText: SourceText,
): void {
  const budget: Budget = { limits, nodes: 0 };
  const stack: PendingCstNode[] = [{ token: document.value, path: [], depth: 1 }];
  while (stack.length > 0) {
    const pending = stack.pop();
    if (pending === undefined) break;
    countNode(
      budget,
      pending.path,
      pending.depth,
      pending.offset ?? pending.token?.offset,
      sourceText,
    );
    if (pending.countOnly === true) continue;
    const token = pending.token;
    if (token === null || token === undefined) continue;
    if (token.type === "alias") {
      throw valueErrorAt("aliases are not portable", pending.path, token.offset, sourceText);
    }
    if (isCstScalar(token)) {
      const scalar = CST.resolveAsScalar(token, true);
      if (scalar !== null && [...scalar.value].length > limits.maxScalarCodePoints) {
        throw valueErrorAt("maximum scalar size exceeded", pending.path, token.offset, sourceText);
      }
      if (scalar !== null && hasUnpairedSurrogate(scalar.value)) {
        throw valueErrorAt(
          "string contains an invalid Unicode scalar",
          pending.path,
          token.offset,
          sourceText,
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
      rejectPlainCompactFlowColons(token.items, text, sourceText);
      if (token.start.type === "flow-map-start") {
        pushMapItems(stack, token.items, pending.path, pending.depth);
      } else {
        pushSequenceItems(stack, token.items, pending.path, pending.depth);
      }
    }
  }
}

function rejectPlainCompactFlowColons(
  items: CST.CollectionItem[],
  text: string,
  sourceText: SourceText,
): void {
  for (const item of items) {
    if (item.key?.type !== "scalar") continue;
    const indicator = item.sep?.find((token) => token.type === "map-value-ind");
    if (indicator === undefined) continue;
    const next = text[indicator.offset + indicator.source.length];
    if (next !== undefined && flowDelimiters.has(next)) {
      throw syntaxErrorAt(compactFlowColonMessage, indicator.offset, sourceText);
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
    const itemPath = [...parentPath, index];
    const mappingIndicator = item.sep?.find((token) => token.type === "map-value-ind");
    if (item.key !== undefined || mappingIndicator !== undefined) {
      const key = cstKeyText(item.key);
      const valuePath = key === null ? itemPath : [...itemPath, key];
      stack.push({ token: item.value, path: valuePath, depth: parentDepth + 2 });
      stack.push({
        token: item.key,
        path: itemPath,
        depth: parentDepth + 2,
        offset: item.key?.offset ?? mappingIndicator?.offset,
      });
      stack.push({
        token: null,
        path: itemPath,
        depth: parentDepth + 1,
        offset: item.key?.offset ?? mappingIndicator?.offset,
        countOnly: true,
      });
      continue;
    }
    stack.push({
      token: item.value,
      path: itemPath,
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
  text: string,
  sourceText: SourceText,
  locations: Map<string, NodeSource>,
): JsonValue {
  const pointer = jsonPointer(path);
  if (node === null) {
    const point = sourceText.point(0);
    locations.set(pointer, { value: { start: point, end: point } });
    return null;
  }
  if (isAlias(node)) {
    throw valueErrorAt("aliases are not portable", path, node.range[0], sourceText);
  }
  if (isScalar(node)) {
    const value = materializeScalar(node, path, sourceText);
    locations.set(pointer, { value: scalarSpan(node, text, sourceText) });
    return value;
  }
  if (isSeq(node)) {
    if (node.tag !== undefined && node.tag !== sequenceTag) {
      throw valueErrorAt("tagged sequences are not portable", path, node.range[0], sourceText);
    }
    const result = node.items.map((item, index) =>
      materializeNode(item, [...path, index], text, sourceText, locations),
    );
    locations.set(pointer, { value: collectionSpan(node, sourceText) });
    return result;
  }
  if (isMap(node)) {
    if (node.tag !== undefined && node.tag !== mapTag) {
      throw valueErrorAt("tagged mappings are not portable", path, node.range[0], sourceText);
    }
    const result: Record<string, JsonValue> = {};
    for (const pair of node.items) {
      if (!isScalar(pair.key)) {
        const offset = "range" in pair.key ? pair.key.range[0] : node.range[0];
        throw valueErrorAt("mapping keys must be strings", path, offset, sourceText);
      }
      if (pair.key.type === "PLAIN" && pair.key.tag === undefined && pair.key.source === "<<") {
        throw valueErrorAt("merge keys are not portable", path, pair.key.range[0], sourceText);
      }
      const key = materializeScalar(pair.key, path, sourceText);
      if (typeof key !== "string") {
        throw valueErrorAt("mapping keys must be strings", path, pair.key.range[0], sourceText);
      }
      const valuePath = [...path, key];
      if (Object.hasOwn(result, key)) {
        throw valueErrorAt("duplicate mapping key", valuePath, pair.key.range[0], sourceText);
      }
      const value = materializeNode(pair.value, valuePath, text, sourceText, locations);
      const valuePointer = jsonPointer(valuePath);
      const valueSource = locations.get(valuePointer);
      if (valueSource === undefined) throw new Error("missing value source after materialization");
      locations.set(valuePointer, {
        value: valueSource.value,
        key: scalarSpan(pair.key, text, sourceText),
      });
      Object.defineProperty(result, key, {
        configurable: true,
        enumerable: true,
        value,
        writable: true,
      });
    }
    locations.set(pointer, { value: collectionSpan(node, sourceText) });
    return result;
  }
  throw new PortableValueError("value is not JSON-compatible", { path: jsonPointer(path) });
}

function materializeScalar(
  node: Scalar.Parsed,
  path: readonly (string | number)[],
  sourceText: SourceText,
): JsonValue {
  const tag = node.tag;
  const source = node.source ?? String(node.value ?? "");
  if (tag === stringTag || (tag === undefined && node.type !== "PLAIN")) return String(node.value);
  if (tag !== undefined && ![nullTag, booleanTag, integerTag, floatTag].includes(tag)) {
    throw valueErrorAt("YAML tag is not portable", path, node.range[0], sourceText);
  }
  if (tag === nullTag) return null;
  if (tag === booleanTag) {
    if (trueValues.has(source)) return true;
    if (falseValues.has(source)) return false;
    throw valueErrorAt("invalid boolean scalar", path, node.range[0], sourceText);
  }
  if (tag === integerTag) return parseInteger(source, path, node.range[0], sourceText);
  if (tag === floatTag) return parseYamlFloat(source, path, node.range[0], sourceText);

  if (nullValues.has(source)) return null;
  if (trueValues.has(source)) return true;
  if (falseValues.has(source)) return false;
  if (integerPattern.test(source)) {
    return parseInteger(source, path, node.range[0], sourceText);
  }
  if (floatPattern.test(source)) {
    return parseYamlFloat(source, path, node.range[0], sourceText);
  }
  return typeof node.value === "string" ? node.value : source;
}

function parseInteger(
  source: string,
  path: readonly (string | number)[],
  offset: number,
  sourceText: SourceText,
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
    throw valueErrorAt("integer is outside the safe range", path, offset, sourceText);
  }
  const magnitude = BigInt(base === 10 ? digits : `${base === 8 ? "0o" : "0x"}${digits}`);
  const value = negative ? -magnitude : magnitude;
  if (value < -MAX_SAFE_INTEGER_BIGINT || value > MAX_SAFE_INTEGER_BIGINT) {
    throw valueErrorAt("integer is outside the safe range", path, offset, sourceText);
  }
  return Number(value);
}

function parseYamlFloat(
  source: string,
  path: readonly (string | number)[],
  offset: number,
  sourceText: SourceText,
): number {
  const cleaned = source.replaceAll("_", "");
  if ([".inf", ".nan"].includes(cleaned.replace(/^[-+]/, "").toLowerCase())) {
    throw valueErrorAt("number must be finite", path, offset, sourceText);
  }
  const exactInteger = exactDecimalInteger(cleaned);
  if (exactInteger !== null) {
    if (exactInteger < -MAX_SAFE_INTEGER_BIGINT || exactInteger > MAX_SAFE_INTEGER_BIGINT) {
      throw valueErrorAt("integer is outside the safe range", path, offset, sourceText);
    }
    return Number(exactInteger);
  }
  const value = Number(cleaned);
  if (!Number.isFinite(value)) {
    throw valueErrorAt("number must be finite", path, offset, sourceText);
  }
  if (Number.isInteger(value) && Math.abs(value) > MAX_SAFE_INTEGER) {
    throw valueErrorAt("rounded integer is outside the safe range", path, offset, sourceText);
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

function hasUnpairedSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (index + 1 >= value.length || next < 0xdc00 || next > 0xdfff) return true;
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
  sourceText?: SourceText,
): void {
  if (depth > budget.limits.maxDepth) {
    throw valueErrorAt("maximum depth exceeded", path, offset, sourceText);
  }
  budget.nodes += 1;
  if (budget.nodes > budget.limits.maxNodesPerResource) {
    throw valueErrorAt("maximum node count exceeded", path, offset, sourceText);
  }
}

function valueErrorAt(
  message: string,
  path: readonly (string | number)[],
  offset?: number,
  sourceText?: SourceText,
): PortableValueError {
  const position =
    offset === undefined || sourceText === undefined ? null : sourceText.point(offset);
  return new PortableValueError(message, {
    path: jsonPointer(path),
    line: position?.line ?? null,
    column: position?.column ?? null,
  });
}

function syntaxErrorAt(
  message: string,
  offset: number,
  sourceText: SourceText,
): PortableYamlSyntaxError {
  const position = sourceText.point(offset);
  return new PortableYamlSyntaxError(message, {
    line: position.line,
    column: position.column,
  });
}

function nodeSpan(node: ParsedNode, sourceText: SourceText): SourceSpan {
  return sourceText.span(node.range[0], node.range[1]);
}

function scalarSpan(node: Scalar.Parsed, text: string, sourceText: SourceText): SourceSpan {
  if (node.value === null && (node.source ?? "") === "" && node.range[0] === node.range[1]) {
    const point = implicitNullPoint(text, node.range[0], sourceText);
    return { start: point, end: point };
  }
  return nodeSpan(node, sourceText);
}

function implicitNullPoint(text: string, offset: number, sourceText: SourceText): SourcePoint {
  let boundary = offset;
  while (text[boundary] === " " || text[boundary] === "\t") boundary += 1;

  if (text[boundary] === "#") {
    const commentStart = boundary;
    while (boundary < text.length && text[boundary] !== "\r" && text[boundary] !== "\n") {
      boundary += 1;
    }
    if (boundary === text.length) boundary = commentStart;
  }
  if (text[boundary] === "\r") {
    return sourceText.point(boundary + (text[boundary + 1] === "\n" ? 2 : 1));
  }
  if (text[boundary] === "\n") return sourceText.point(boundary + 1);
  return sourceText.point(boundary);
}

function collectionSpan(
  node: Exclude<ParsedNode, Scalar.Parsed>,
  sourceText: SourceText,
): SourceSpan {
  const span = nodeSpan(node, sourceText);
  if ("flow" in node && node.flow === true) return span;
  return { start: span.start, end: sourceText.nextLinePoint(node.range[1]) };
}

function utf8Size(value: string): number {
  return new TextEncoder().encode(value).byteLength;
}
