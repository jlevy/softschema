/** Bounded parsing and normalization for softschema's portable YAML value domain. */
import {
  Composer,
  CST,
  isAlias,
  isMap,
  isScalar,
  isSeq,
  Lexer,
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
  tagPrefixes?: CstTagPrefixes;
}

type CstCollection = CST.BlockMap | CST.BlockSequence | CST.FlowCollection;
type CstTagPrefixes = ReadonlyMap<string, string>;

interface CstCollectionState {
  depth: number;
  processedItems: number;
}

interface ParsedCstResult {
  documentCount: number;
  semanticError: PortableValueError | undefined;
  tokens: CST.Token[];
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
const taggedIntegerPattern = /^[-+]?(?:[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$/;
const taggedFloatPattern = new RegExp(
  "^[-+]?(?:(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][-+]?[0-9]+)?|" +
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
  const parsedCst = normalizeYamlLibraryErrors(
    () => parseCstWithBudget(text, parser, limits, sourceText),
    sourceText,
  );
  const { documentCount, semanticError, tokens } = parsedCst;
  const errorToken = tokens.find((token) => token.type === "error");
  if (errorToken !== undefined) {
    throw syntaxErrorAt("invalid YAML syntax", errorToken.offset, sourceText);
  }
  const documents = tokens.filter((token): token is CST.Document => token.type === "document");
  if (documentCount === 0) {
    const directives = tokens.filter((token): token is CST.Directive => token.type === "directive");
    rejectCstDirectiveSyntax(directives, sourceText);
    if (directives.length > 0) {
      throw syntaxErrorAt("invalid YAML syntax", text.length, sourceText);
    }
    const budget: Budget = { limits, nodes: 0 };
    countNode(budget, [], 1);
    const point = sourceText.point(0);
    return {
      value: null,
      sourceMap: new SourceMap([["", { value: { start: point, end: point } }]]),
    };
  }
  const document = documents[0];
  if (documentCount !== 1) {
    throw new PortableYamlSyntaxError("exactly one YAML document is required");
  }
  if (semanticError !== undefined) throw semanticError;
  if (document === undefined) throw new Error("retained YAML document is missing");
  rejectCstSyntaxPolicies(document, sourceText);
  const directives = cstDirectivesForDocument(tokens, document);
  rejectCstDirectiveSyntax(directives, sourceText);
  const tagPrefixes = cstTagPrefixesForDocument(tokens, document);
  rejectUndefinedCstTagHandles(document, tagPrefixes, sourceText);

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
    const offset = first === undefined ? 0 : yamlComposerErrorOffset(first, text);
    throw syntaxErrorAt("invalid YAML syntax", offset, sourceText);
  }
  normalizeYamlLibraryErrors(
    () => preflightCst(document, limits, text, sourceText, tagPrefixes),
    sourceText,
  );
  const locations = new Map<string, NodeSource>();
  const value = materializeNode(composed[0].contents, [], text, sourceText, locations);
  return { value, sourceMap: new SourceMap(locations) };
}

/** Parse incrementally, retaining a composable CST only while the resource remains valid. */
function parseCstWithBudget(
  text: string,
  parser: Parser,
  limits: ValidationLimits,
  sourceText: SourceText,
): ParsedCstResult {
  const lexer = new Lexer();
  const tokens: CST.Token[] = [];
  const budget = new CstConstructionBudget(limits, sourceText);
  let discard = false;
  let documentCount = 0;
  let semanticError: PortableValueError | undefined;
  const activeTagPrefixes = defaultCstTagPrefixes();
  let pendingDirectives: CST.Directive[] = [];
  const directivesByDocument = new WeakMap<CST.Document, readonly CST.Directive[]>();
  let previousLexemeType: CST.TokenType | null = null;

  const validateDiscardedDocument = (document: CST.Document): void => {
    rejectCstSyntaxPolicies(document, sourceText);
    validateCstDocumentSyntax(document, text, sourceText, directivesByDocument.get(document) ?? []);
  };

  const beginDiscard = (): void => {
    if (discard) return;
    for (const token of tokens) {
      if (token.type === "document") validateDiscardedDocument(token);
    }
    tokens.length = 0;
    discard = true;
    compactParserStack(parser.stack);
  };

  const consume = (parsed: CST.Token[]): void => {
    const errorToken = parsed.find((token) => token.type === "error");
    if (errorToken !== undefined) {
      throw syntaxErrorAt("invalid YAML syntax", errorToken.offset, sourceText);
    }
    for (const token of parsed) {
      if (token.type === "directive") {
        pendingDirectives.push(token);
        applyCstTagDirective(activeTagPrefixes, token);
      } else if (token.type === "document") {
        documentCount += 1;
        directivesByDocument.set(token, pendingDirectives);
        pendingDirectives = [];
        resetCstTagPrefixes(activeTagPrefixes);
      }
    }
    if (documentCount > 1) beginDiscard();
    if (discard) {
      for (const token of parsed) {
        if (token.type === "document") validateDiscardedDocument(token);
      }
    } else {
      tokens.push(...parsed);
    }
  };

  for (const lexeme of lexer.lex(text)) {
    const parsed = [...parser.next(lexeme)];
    const lexemeType = CST.tokenType(lexeme);
    if (
      lexemeType === "comment" &&
      (previousLexemeType === "flow-map-start" || previousLexemeType === "flow-seq-start")
    ) {
      throw syntaxErrorAt("invalid YAML syntax", parser.offset - lexeme.length, sourceText);
    }
    previousLexemeType = lexemeType;
    if (lexemeType === "doc-end") {
      const document = parsed.find((token): token is CST.Document => token.type === "document");
      if (
        document !== undefined &&
        document.value === undefined &&
        !document.start.some((token) => token.type === "doc-start")
      ) {
        throw syntaxErrorAt("invalid YAML syntax", parser.offset - lexeme.length, sourceText);
      }
    }
    consume(parsed);
    if (
      lexemeType === "comma" ||
      lexemeType === "flow-map-start" ||
      lexemeType === "flow-map-end" ||
      lexemeType === "flow-seq-start" ||
      lexemeType === "flow-seq-end" ||
      lexemeType === "flow-error-end"
    ) {
      rejectActiveCstSyntax(parser.stack, sourceText);
    }
    if (!discard && !budget.exceeded) budget.observe(parser.stack);
    const implicitDepthError =
      semanticError === undefined && CST.tokenType(lexeme) === "map-value-ind"
        ? activeImplicitFlowDepthError(parser.stack, limits.maxDepth)
        : undefined;
    if (semanticError === undefined && implicitDepthError !== undefined) {
      try {
        preflightActiveCst(parser.stack, limits, text, sourceText, activeTagPrefixes);
        semanticError = valueErrorAt(
          "maximum depth exceeded",
          implicitDepthError.path,
          implicitDepthError.offset,
          sourceText,
        );
      } catch (error) {
        if (!(error instanceof PortableValueError)) throw error;
        semanticError = error;
      }
      beginDiscard();
    }
    if (semanticError === undefined && budget.exceeded && !hasUnattachedValueToken(parser.stack)) {
      try {
        preflightActiveCst(parser.stack, limits, text, sourceText, activeTagPrefixes);
      } catch (error) {
        if (!(error instanceof PortableValueError)) throw error;
        semanticError = error;
        beginDiscard();
      }
    }
    if (discard && shouldCompactAfterLexeme(lexeme)) compactParserStack(parser.stack);
  }
  const ended = [...parser.end()];
  consume(ended);
  if (!discard && !budget.exceeded) budget.observe(parser.stack);
  if (semanticError === undefined && budget.exceeded) {
    const document = ended.find((token): token is CST.Document => token.type === "document");
    if (document !== undefined) {
      rejectCstSyntaxPolicies(document, sourceText);
      validateCstDocumentSyntax(
        document,
        text,
        sourceText,
        directivesByDocument.get(document) ?? [],
      );
      try {
        const tagPrefixes = cstTagPrefixesForDirectives(directivesByDocument.get(document) ?? []);
        preflightCst(document, limits, text, sourceText, tagPrefixes);
      } catch (error) {
        if (!(error instanceof PortableValueError)) throw error;
        semanticError = error;
      }
    }
  }
  if (discard) return { documentCount, semanticError, tokens: [] };
  return { documentCount, semanticError, tokens };
}

function validateCstDocumentSyntax(
  document: CST.Document,
  text: string,
  sourceText: SourceText,
  directives: readonly CST.Directive[] = [],
): void {
  rejectCstDirectiveSyntax(directives, sourceText);
  const composer = new Composer({
    keepSourceTokens: true,
    logLevel: "silent",
    prettyErrors: false,
    schema: "core",
    strict: true,
    uniqueKeys: false,
  });
  const composed = [...composer.compose([...directives, document], true, text.length)];
  const first = composed[0]?.errors[0];
  if (composed.length !== 1 || first !== undefined) {
    throw syntaxErrorAt(
      "invalid YAML syntax",
      first === undefined ? document.offset : yamlComposerErrorOffset(first, text),
      sourceText,
    );
  }
}

function yamlComposerErrorOffset(error: YamlLibraryParseError, text: string): number {
  if (error.code === "BAD_DQ_ESCAPE") {
    const escapeType = text[error.pos[0] + 1];
    return escapeType === "x" || escapeType === "u" || escapeType === "U"
      ? error.pos[0] + 2
      : error.pos[1];
  }
  if (
    error.code === "BAD_ALIAS" ||
    error.code === "MULTILINE_IMPLICIT_KEY" ||
    error.code === "TAG_RESOLVE_FAILED"
  ) {
    return error.pos[1];
  }
  return error.pos[0];
}

function rejectCstDirectiveSyntax(
  directives: readonly CST.Directive[],
  sourceText: SourceText,
): void {
  let sawYaml = false;
  const tagHandles = new Set<string>();
  for (const directive of directives) {
    if (/^%YAML(?:[ \t]|$)/.test(directive.source)) {
      if (sawYaml) throw syntaxErrorAt("invalid YAML syntax", directive.offset, sourceText);
      sawYaml = true;
      const version = /^%YAML[ \t]+([0-9]+)\.([0-9]+)(?:[ \t]|$)/.exec(directive.source);
      if (version !== null && (version[1] !== "1" || !["1", "2"].includes(version[2] ?? ""))) {
        throw syntaxErrorAt("invalid YAML syntax", directive.offset, sourceText);
      }
      continue;
    }
    const match = /^%TAG[ \t]+(!|!!|![^ \t!]+!)(?:[ \t]|$)/.exec(directive.source);
    const handle = match?.[1];
    if (/^%TAG(?:[ \t]|$)/.test(directive.source) && handle === undefined) {
      const malformedPrefix = /^%TAG[ \t]+[^ \t]*/.exec(directive.source);
      const offset = directive.offset + (malformedPrefix?.[0].length ?? 0);
      throw syntaxErrorAt("invalid YAML syntax", offset, sourceText);
    }
    if (handle !== undefined) {
      if (tagHandles.has(handle)) {
        throw syntaxErrorAt("invalid YAML syntax", directive.offset, sourceText);
      }
      tagHandles.add(handle);
      continue;
    }
    const name = /^%[0-9A-Za-z-]+(?=[ \t]|$)/.exec(directive.source);
    if (name === null) {
      const prefix = /^%[0-9A-Za-z-]*/.exec(directive.source)?.[0] ?? "%";
      throw syntaxErrorAt("invalid YAML syntax", directive.offset + prefix.length, sourceText);
    }
  }
}

function compactParserStack(stack: CST.Token[]): void {
  for (const token of stack) {
    if (!CST.isCollection(token) || token.items.length <= 2) continue;
    token.items.splice(0, token.items.length - 2);
    if (token.type === "flow-collection") {
      const first = token.items[0];
      if (first !== undefined) {
        first.start = first.start.filter((property) => property.type !== "comma");
      }
    }
  }
}

function shouldCompactAfterLexeme(lexeme: string): boolean {
  const type = CST.tokenType(lexeme);
  return (
    type === "comma" ||
    type === "seq-item-ind" ||
    type === "map-value-ind" ||
    type === "newline" ||
    type === "doc-start" ||
    type === "doc-end"
  );
}

function hasUnattachedValueToken(stack: CST.Token[]): boolean {
  const token = stack.at(-1);
  if (token === undefined) return false;
  if (token.type === "alias" || isCstScalar(token)) return true;
  let parent: CstCollection | undefined;
  for (let index = stack.length - 2; index >= 0; index -= 1) {
    const candidate = stack[index];
    if (CST.isCollection(candidate)) {
      parent = candidate;
      break;
    }
  }
  if (parent?.type === "flow-collection" && parent.start.type === "flow-seq-start") {
    const item = parent.items.at(-1);
    return (
      item !== undefined &&
      item.sep?.some((property) => property.type === "map-value-ind") !== true &&
      !item.start.some((property) => property.type === "explicit-key-ind")
    );
  }
  return false;
}

function preflightActiveCst(
  stack: CST.Token[],
  limits: ValidationLimits,
  text: string,
  sourceText: SourceText,
  tagPrefixes: CstTagPrefixes,
): void {
  const document = stack.find((token): token is CST.Document => token.type === "document");
  if (document === undefined) return;
  const documentIndex = stack.indexOf(document);
  const activeValues = stack.slice(documentIndex + 1).filter((token) => isCstValueToken(token));
  const value = document.value ?? activeCstValueSnapshot(activeValues);
  if (value === undefined) return;
  preflightCst({ ...document, value }, limits, text, sourceText, tagPrefixes);
}

function activeCstValueSnapshot(activeValues: CST.Token[]): CST.Token | undefined {
  let child = activeValues.at(-1);
  if (child === undefined) return undefined;
  for (let index = activeValues.length - 2; index >= 0; index -= 1) {
    const parent = activeValues[index];
    if (!CST.isCollection(parent)) continue;
    const items: CST.CollectionItem[] = parent.items.map((item) => ({
      ...item,
      start: [...item.start],
      sep: item.sep === undefined ? undefined : [...item.sep],
    }));
    let item = items.at(-1);
    if (item === undefined && !isCstMap(parent)) {
      const syntheticItem: CST.CollectionItem = { start: [], sep: undefined, value: child };
      items.push(syntheticItem);
      item = syntheticItem;
    }
    if (item !== undefined) {
      if (isCstMap(parent)) {
        if (item.sep === undefined) item.key = child;
        else item.value = child;
      } else {
        const mapping =
          item.sep?.some((property) => property.type === "map-value-ind") === true ||
          item.start.some((property) => property.type === "explicit-key-ind");
        if (mapping && item.key === undefined) item.key = child;
        else item.value = child;
      }
    }
    child = { ...parent, items } as CstCollection;
  }
  return child;
}

function activeImplicitFlowDepthError(
  stack: CST.Token[],
  maxDepth: number,
): { path: readonly (string | number)[]; offset: number } | undefined {
  const collections = stack.filter((token): token is CstCollection => CST.isCollection(token));
  let path: readonly (string | number)[] = [];
  let depth = 1;
  for (let index = 0; index < collections.length; index += 1) {
    const collection = collections[index];
    if (collection === undefined) continue;
    const itemIndex = Math.max(0, collection.items.length - 1);
    const item = collection.items[itemIndex];
    const child = collections[index + 1];
    if (item === undefined) {
      if (child !== undefined && !isCstMap(collection)) {
        path = [...path, itemIndex];
        depth += 1;
      }
      continue;
    }
    const indicator = item.sep?.find((token) => token.type === "map-value-ind");
    if (
      collection.type === "flow-collection" &&
      collection.start.type === "flow-seq-start" &&
      indicator !== undefined
    ) {
      const mappingPath = [...path, itemIndex];
      if (depth + 1 > maxDepth || depth + 2 > maxDepth) {
        return {
          path: mappingPath,
          offset: item.key?.offset ?? indicator.offset,
        };
      }
    }

    if (child === undefined) continue;
    if (isCstMap(collection)) {
      const key = cstKeyText(item.key);
      if (key !== null) path = [...path, key];
      depth += 1;
    } else if (indicator !== undefined) {
      const key = cstKeyText(item.key);
      path = key === null ? [...path, itemIndex] : [...path, itemIndex, key];
      depth += 2;
    } else {
      path = [...path, itemIndex];
      depth += 1;
    }
  }
  return undefined;
}

/** Detect construction limits before parser-owned collection arrays can grow past them. */
class CstConstructionBudget {
  private readonly seenTokens = new WeakSet<object>();
  private readonly collections = new Map<CstCollection, CstCollectionState>();
  private nodes = 0;
  private limitExceeded = false;

  constructor(
    private readonly limits: ValidationLimits,
    private readonly sourceText: SourceText,
  ) {}

  get exceeded(): boolean {
    return this.limitExceeded;
  }

  observe(stack: CST.Token[]): void {
    const activeCollections = new Set<CstCollection>();
    let depth = 0;
    for (let index = 0; index < stack.length; index += 1) {
      const token = stack[index];
      if (token === undefined || !isCstValueToken(token)) continue;
      depth += 1;
      if (CST.isCollection(token)) activeCollections.add(token);
      if (this.seenTokens.has(token)) continue;

      this.seenTokens.add(token);
      if (depth > this.limits.maxDepth) this.limitExceeded = true;
      if (token.type === "block-map" && depth + 1 > this.limits.maxDepth) {
        const key = token.items[0]?.key;
        if (key !== null && key !== undefined) this.limitExceeded = true;
      }
      this.count();
      if (CST.isCollection(token)) {
        this.collections.set(token, { depth, processedItems: 0 });
      }
    }

    for (const [collection, state] of this.collections) {
      const active = activeCollections.has(collection);
      const completeItems = active
        ? Math.max(0, collection.items.length - 1)
        : collection.items.length;
      while (state.processedItems < completeItems) {
        const index = state.processedItems;
        const item = collection.items[index];
        state.processedItems += 1;
        if (item !== undefined) {
          rejectCompletedCstItemSyntax(collection, item, index, this.sourceText);
          this.countImplicitItem(collection, item, state.depth);
        }
      }
      if (!active) this.collections.delete(collection);
    }
  }

  private countImplicitItem(
    collection: CstCollection,
    item: CST.CollectionItem,
    parentDepth: number,
  ): void {
    if (isCstMap(collection)) {
      if (item.key === null || item.key === undefined) {
        this.countAtDepth(parentDepth + 1);
      } else {
        this.countUnseenToken(item.key, parentDepth + 1);
      }
      if (item.value === undefined) {
        this.countAtDepth(parentDepth + 1);
      } else {
        this.countUnseenToken(item.value, parentDepth + 1);
      }
      return;
    }

    const mappingIndicator = item.sep?.find((token) => token.type === "map-value-ind");
    const explicitKey = item.start.some((token) => token.type === "explicit-key-ind");
    if (explicitKey || mappingIndicator !== undefined) {
      this.countAtDepth(parentDepth + 1);
      if (item.key === null || item.key === undefined) {
        this.countAtDepth(parentDepth + 2);
      } else {
        this.countUnseenToken(item.key, parentDepth + 2);
      }
      if (item.value === undefined) {
        this.countAtDepth(parentDepth + 2);
      } else {
        this.countUnseenToken(item.value, parentDepth + 2);
      }
      return;
    }
    const value = item.value ?? item.key;
    if (value === undefined || value === null) {
      this.countAtDepth(parentDepth + 1);
    } else {
      this.countUnseenToken(value, parentDepth + 1);
    }
  }

  private countUnseenToken(token: CST.Token, depth: number): void {
    if (this.seenTokens.has(token)) return;
    this.seenTokens.add(token);
    this.countAtDepth(depth);
  }

  private countAtDepth(depth: number): void {
    if (depth > this.limits.maxDepth) this.limitExceeded = true;
    this.count();
  }

  private count(): void {
    this.nodes += 1;
    if (this.nodes > this.limits.maxNodesPerResource) this.limitExceeded = true;
  }
}

function rejectCompletedCstItemSyntax(
  collection: CstCollection,
  item: CST.CollectionItem,
  index: number,
  sourceText: SourceText,
): void {
  if (collection.type !== "flow-collection") return;
  const commas = item.start.filter((token) => token.type === "comma");
  const comma = commas[0];
  if (commas[1] !== undefined) {
    throw syntaxErrorAt("invalid YAML syntax", commas[1].offset, sourceText);
  }
  if (index === 0 && comma !== undefined) {
    throw syntaxErrorAt("invalid YAML syntax", comma.offset, sourceText);
  }
  if (index > 0 && comma === undefined) {
    throw syntaxErrorAt(
      "invalid YAML syntax",
      item.key?.offset ?? item.value?.offset ?? itemEndOffset(item),
      sourceText,
    );
  }
  const indicators = item.sep?.filter((token) => token.type === "map-value-ind") ?? [];
  if (indicators[1] !== undefined) {
    throw syntaxErrorAt("invalid YAML syntax", indicators[1].offset, sourceText);
  }
  for (const value of [item.key, item.value]) {
    if (value === null || value === undefined || !("end" in value)) continue;
    const unexpectedStart = value.end?.find(
      (token) => token.type === "flow-map-start" || token.type === "flow-seq-start",
    );
    if (unexpectedStart !== undefined) {
      throw syntaxErrorAt("invalid YAML syntax", unexpectedStart.offset, sourceText);
    }
  }
  if (item.key?.type === "block-map" || item.key?.type === "block-seq") {
    throw syntaxErrorAt("invalid YAML syntax", nestedBlockSyntaxOffset(item.key), sourceText);
  }
  if (item.value?.type === "block-map" || item.value?.type === "block-seq") {
    throw syntaxErrorAt("invalid YAML syntax", nestedBlockSyntaxOffset(item.value), sourceText);
  }
  if (
    collection.start.type === "flow-seq-start" &&
    item.key !== null &&
    item.key !== undefined &&
    item.value !== undefined &&
    item.sep?.some((token) => token.type === "map-value-ind") !== true &&
    !item.start.some((token) => token.type === "explicit-key-ind")
  ) {
    throw syntaxErrorAt("invalid YAML syntax", item.value.offset, sourceText);
  }
}

function nestedBlockSyntaxOffset(collection: CST.BlockMap | CST.BlockSequence): number {
  for (const item of collection.items) {
    const indicator = item.sep?.find((token) => token.type === "map-value-ind");
    if (indicator !== undefined) return indicator.offset;
  }
  return collection.offset;
}

function rejectActiveCstSyntax(stack: CST.Token[], sourceText: SourceText): void {
  for (const token of stack) {
    if (token.type !== "flow-collection") continue;
    const unexpectedStart = token.end.find(
      (item) => item.type === "flow-map-start" || item.type === "flow-seq-start",
    );
    if (unexpectedStart !== undefined) {
      throw syntaxErrorAt("invalid YAML syntax", unexpectedStart.offset, sourceText);
    }
    const end = token.end[0];
    const expectedEnd = token.start.type === "flow-map-start" ? "flow-map-end" : "flow-seq-end";
    if (end !== undefined && end.type !== expectedEnd) {
      throw syntaxErrorAt("invalid YAML syntax", end.offset, sourceText);
    }
    const start = Math.max(0, token.items.length - 2);
    for (let index = start; index < token.items.length; index += 1) {
      const item = token.items[index];
      if (item !== undefined) rejectCompletedCstItemSyntax(token, item, index, sourceText);
    }
  }
}

function isCstValueToken(token: CST.Token): boolean {
  return token.type === "alias" || isCstScalar(token) || CST.isCollection(token);
}

function isCstMap(collection: CstCollection): boolean {
  return (
    collection.type === "block-map" ||
    (collection.type === "flow-collection" && collection.start.type === "flow-map-start")
  );
}

function itemEndOffset(item: CST.CollectionItem): number {
  let end = 0;
  for (const token of [
    ...item.start,
    ...(item.sep ?? []),
    ...(item.key === null || item.key === undefined ? [] : [item.key]),
    ...(item.value === undefined ? [] : [item.value]),
  ]) {
    end = Math.max(end, cstTokenEnd(token));
  }
  return end;
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
  tagPrefixes: CstTagPrefixes,
): void {
  const budget: Budget = { limits, nodes: 0, tagPrefixes };
  const stack: PreflightFrame[] = [
    {
      kind: "value",
      token: document.value,
      props: document.start,
      path: [],
      depth: 1,
      inFlow: false,
      offset: document.value?.offset ?? document.offset,
    },
  ];
  while (stack.length > 0) {
    const frame = stack.pop();
    if (frame === undefined) break;
    if (frame.kind === "value") {
      preflightCstValue(frame, stack, budget, text, sourceText);
    } else if (frame.kind === "map-items") {
      preflightCstMapItem(frame, stack, budget, text, sourceText);
    } else {
      preflightCstSequenceItem(frame, stack, budget, text, sourceText);
    }
  }
}

interface CstValueFrame {
  kind: "value";
  token: CST.Token | null | undefined;
  props: readonly CST.SourceToken[];
  path: readonly (string | number)[];
  depth: number;
  inFlow: boolean;
  offset: number;
  compactIndicator?: CST.SourceToken;
}

interface CstMapItemsFrame {
  kind: "map-items";
  items: readonly CST.CollectionItem[];
  index: number;
  path: readonly (string | number)[];
  depth: number;
  inFlow: boolean;
  keys: Set<string>;
}

interface CstSequenceItemsFrame {
  kind: "sequence-items";
  items: readonly CST.CollectionItem[];
  index: number;
  path: readonly (string | number)[];
  depth: number;
  inFlow: boolean;
}

type PreflightFrame = CstValueFrame | CstMapItemsFrame | CstSequenceItemsFrame;

function preflightCstValue(
  frame: CstValueFrame,
  stack: PreflightFrame[],
  budget: Budget,
  text: string,
  sourceText: SourceText,
): void {
  if (frame.compactIndicator !== undefined && isCstScalar(frame.token)) {
    rejectPlainCompactFlowColon(frame.token, frame.compactIndicator, text, sourceText);
  }
  countNode(
    budget,
    frame.path,
    frame.depth,
    cstNodeEventOffset(frame.props, frame.token, frame.offset),
    sourceText,
  );
  const token = frame.token;
  if (token === null || token === undefined) return;
  if (token.type === "alias") {
    throw valueErrorAt("aliases are not portable", frame.path, token.offset, sourceText);
  }
  if (isCstScalar(token)) {
    preflightCstScalar(
      token,
      frame.props,
      frame.path,
      budget.limits,
      budget.tagPrefixes ?? defaultCstTagPrefixes(),
      sourceText,
    );
    return;
  }
  if (!CST.isCollection(token)) return;

  const tag = cstTag(frame.props);
  const expectedTag = isCstMap(token) ? mapTag : sequenceTag;
  if (
    tag !== undefined &&
    expandCstTag(tag.source, budget.tagPrefixes ?? defaultCstTagPrefixes()) !== expectedTag
  ) {
    throw valueErrorAt(
      isCstMap(token) ? "tagged mappings are not portable" : "tagged sequences are not portable",
      frame.path,
      tag.offset,
      sourceText,
    );
  }
  if (isCstMap(token)) {
    stack.push({
      kind: "map-items",
      items: token.items,
      index: 0,
      path: frame.path,
      depth: frame.depth,
      inFlow: token.type === "flow-collection",
      keys: new Set<string>(),
    });
  } else {
    stack.push({
      kind: "sequence-items",
      items: token.items,
      index: 0,
      path: frame.path,
      depth: frame.depth,
      inFlow: token.type === "flow-collection",
    });
  }
}

function preflightCstMapItem(
  frame: CstMapItemsFrame,
  stack: PreflightFrame[],
  budget: Budget,
  text: string,
  sourceText: SourceText,
): void {
  let index = frame.index;
  let item: CST.CollectionItem | undefined;
  while (index < frame.items.length) {
    item = frame.items[index];
    index += 1;
    if (item !== undefined && (item.key !== undefined || item.sep !== undefined)) break;
    item = undefined;
  }
  if (item === undefined) return;

  const indicator = item.sep?.find((token) => token.type === "map-value-ind");
  const key = preflightCstMapKey(
    item.key,
    item.start,
    indicator,
    frame.path,
    frame.depth + 1,
    frame.inFlow,
    frame.keys,
    budget,
    text,
    sourceText,
  );
  stack.push({ ...frame, index });
  stack.push({
    kind: "value",
    token: item.value,
    props: item.sep ?? [],
    path: [...frame.path, key],
    depth: frame.depth + 1,
    inFlow: frame.inFlow,
    offset: item.value?.offset ?? implicitCstValueOffset(item, frame.inFlow, false),
  });
}

function preflightCstSequenceItem(
  frame: CstSequenceItemsFrame,
  stack: PreflightFrame[],
  budget: Budget,
  text: string,
  sourceText: SourceText,
): void {
  const item = frame.items[frame.index];
  if (item === undefined) return;
  const nextIndex = frame.index + 1;
  stack.push({ ...frame, index: nextIndex });
  const itemPath = [...frame.path, frame.index];
  const indicator = item.sep?.find((token) => token.type === "map-value-ind");
  const explicitKey = item.start.some((token) => token.type === "explicit-key-ind");
  if (indicator !== undefined || explicitKey) {
    if (frame.inFlow && indicator !== undefined && isCstScalar(item.key)) {
      rejectPlainCompactFlowColon(item.key, indicator, text, sourceText);
    }
    countNode(
      budget,
      itemPath,
      frame.depth + 1,
      cstMappingEventOffset(item, indicator),
      sourceText,
    );
    const key = preflightCstMapKey(
      item.key,
      item.start,
      indicator,
      itemPath,
      frame.depth + 2,
      frame.inFlow,
      new Set<string>(),
      budget,
      text,
      sourceText,
    );
    stack.push({
      kind: "value",
      token: item.value,
      props: item.sep ?? [],
      path: [...itemPath, key],
      depth: frame.depth + 2,
      inFlow: frame.inFlow,
      offset: item.value?.offset ?? implicitCstValueOffset(item, frame.inFlow, false),
    });
    return;
  }
  stack.push({
    kind: "value",
    token: item.value ?? item.key,
    props: item.start,
    path: itemPath,
    depth: frame.depth + 1,
    inFlow: frame.inFlow,
    offset:
      item.value?.offset ?? item.key?.offset ?? implicitCstValueOffset(item, frame.inFlow, true),
  });
}

function preflightCstMapKey(
  token: CST.Token | null | undefined,
  props: readonly CST.SourceToken[],
  indicator: CST.SourceToken | undefined,
  path: readonly (string | number)[],
  depth: number,
  inFlow: boolean,
  keys: Set<string>,
  budget: Budget,
  text: string,
  sourceText: SourceText,
): string {
  if (token !== null && token !== undefined && !isCstScalar(token)) {
    throw valueErrorAt(
      "mapping keys must be strings",
      path,
      emptyCstKeyOffset(props, indicator, token),
      sourceText,
    );
  }
  if (token === null || token === undefined) {
    const offset = emptyCstKeyOffset(props, indicator, token);
    countNode(budget, path, depth, offset, sourceText);
    throw valueErrorAt("mapping keys must be strings", path, offset, sourceText);
  }
  if (inFlow && indicator !== undefined) {
    rejectPlainCompactFlowColon(token, indicator, text, sourceText);
  }
  const tag = cstTag(props);
  if (token.type === "scalar" && token.source === "<<" && tag === undefined) {
    throw valueErrorAt("merge keys are not portable", path, token.offset, sourceText);
  }
  countNode(budget, path, depth, cstNodeEventOffset(props, token, token.offset), sourceText);
  const key = preflightCstScalar(
    token,
    props,
    path,
    budget.limits,
    budget.tagPrefixes ?? defaultCstTagPrefixes(),
    sourceText,
  );
  if (typeof key !== "string") {
    throw valueErrorAt("mapping keys must be strings", path, token.offset, sourceText);
  }
  if (keys.has(key)) {
    throw valueErrorAt("duplicate mapping key", [...path, key], token.offset, sourceText);
  }
  keys.add(key);
  return key;
}

function preflightCstScalar(
  token: CST.FlowScalar | CST.BlockScalar,
  props: readonly CST.SourceToken[],
  path: readonly (string | number)[],
  limits: ValidationLimits,
  tagPrefixes: CstTagPrefixes,
  sourceText: SourceText,
): JsonValue {
  const scalar = CST.resolveAsScalar(token, true);
  if (scalar === null) {
    throw valueErrorAt("value is not JSON-compatible", path, token.offset, sourceText);
  }
  if (exceedsCodePointLimit(scalar.value, limits.maxScalarCodePoints)) {
    throw valueErrorAt("maximum scalar size exceeded", path, token.offset, sourceText);
  }
  if (hasUnpairedSurrogate(scalar.value)) {
    throw valueErrorAt("string contains an invalid Unicode scalar", path, token.offset, sourceText);
  }
  const tag = cstTag(props);
  const expandedTag = tag === undefined ? undefined : expandCstTag(tag.source, tagPrefixes);
  if (
    tag !== undefined &&
    ![stringTag, nullTag, booleanTag, integerTag, floatTag].includes(expandedTag ?? "")
  ) {
    throw valueErrorAt("YAML tag is not portable", path, tag.offset, sourceText);
  }
  if (
    tag !== undefined &&
    expandedTag === booleanTag &&
    !trueValues.has(scalar.value) &&
    !falseValues.has(scalar.value)
  ) {
    throw valueErrorAt("invalid boolean scalar", path, tag.offset, sourceText);
  }
  if (tag !== undefined && expandedTag === integerTag) {
    return parseInteger(scalar.value, path, tag.offset, sourceText);
  }
  if (tag !== undefined && expandedTag === floatTag) {
    return parseYamlFloat(scalar.value, path, tag.offset, sourceText);
  }
  const parsed =
    expandedTag === undefined ? scalar : ({ ...scalar, tag: expandedTag } as Scalar.Parsed);
  return materializeScalar(parsed as Scalar.Parsed, path, sourceText);
}

function rejectPlainCompactFlowColon(
  token: CST.FlowScalar | CST.BlockScalar,
  indicator: CST.SourceToken,
  text: string,
  sourceText: SourceText,
): void {
  if (token.type !== "scalar") return;
  const next = text[indicator.offset + indicator.source.length];
  if (next !== undefined && flowDelimiters.has(next)) {
    throw syntaxErrorAt(compactFlowColonMessage, indicator.offset, sourceText);
  }
}

function cstTag(props: readonly CST.SourceToken[]): CST.SourceToken | undefined {
  return props.findLast((token) => token.type === "tag");
}

function expandCstTag(source: string, prefixes: CstTagPrefixes): string {
  if (source.startsWith("!<") && source.endsWith(">")) return source.slice(2, -1);
  const namedHandleEnd = source.indexOf("!", 1);
  const handle = namedHandleEnd === -1 ? "!" : source.slice(0, namedHandleEnd + 1);
  const suffix = namedHandleEnd === -1 ? source.slice(1) : source.slice(namedHandleEnd + 1);
  const prefix = prefixes.get(handle);
  if (prefix !== undefined) return `${prefix}${suffix}`;
  return source;
}

function rejectUndefinedCstTagHandles(
  document: CST.Document,
  prefixes: CstTagPrefixes,
  sourceText: SourceText,
): void {
  const stack: { token: CST.Token | null | undefined; props: readonly CST.SourceToken[] }[] = [
    { token: document.value, props: document.start },
  ];
  while (stack.length > 0) {
    const frame = stack.pop();
    if (frame === undefined) break;
    for (const property of frame.props) {
      if (property.type !== "tag" || property.source.startsWith("!<")) continue;
      const namedHandleEnd = property.source.indexOf("!", 1);
      const handle = namedHandleEnd === -1 ? "!" : property.source.slice(0, namedHandleEnd + 1);
      if (!prefixes.has(handle)) {
        throw syntaxErrorAt("invalid YAML syntax", property.offset, sourceText);
      }
    }
    if (!CST.isCollection(frame.token)) continue;
    for (let index = frame.token.items.length - 1; index >= 0; index -= 1) {
      const item = frame.token.items[index];
      if (item === undefined) continue;
      stack.push(
        { token: item.value, props: item.sep ?? [] },
        { token: item.key, props: item.start },
      );
    }
  }
}

function defaultCstTagPrefixes(): Map<string, string> {
  return new Map([
    ["!", "!"],
    ["!!", "tag:yaml.org,2002:"],
  ]);
}

function resetCstTagPrefixes(prefixes: Map<string, string>): void {
  prefixes.clear();
  for (const [handle, prefix] of defaultCstTagPrefixes()) prefixes.set(handle, prefix);
}

function applyCstTagDirective(prefixes: Map<string, string>, token: CST.Directive): void {
  const match = /^%TAG[ \t]+(!|!!|![^ \t!]+!)[ \t]+([^ \t]+)(?:[ \t]|$)/.exec(token.source);
  if (match?.[1] !== undefined && match[2] !== undefined) prefixes.set(match[1], match[2]);
}

function cstTagPrefixesForDocument(
  tokens: readonly CST.Token[],
  document: CST.Document,
): CstTagPrefixes {
  const prefixes = defaultCstTagPrefixes();
  for (const token of tokens) {
    if (token === document) break;
    if (token.type === "directive") applyCstTagDirective(prefixes, token);
    if (token.type === "document") {
      resetCstTagPrefixes(prefixes);
    }
  }
  return prefixes;
}

function cstTagPrefixesForDirectives(directives: readonly CST.Directive[]): CstTagPrefixes {
  const prefixes = defaultCstTagPrefixes();
  for (const directive of directives) applyCstTagDirective(prefixes, directive);
  return prefixes;
}

function cstDirectivesForDocument(
  tokens: readonly CST.Token[],
  document: CST.Document,
): readonly CST.Directive[] {
  const directives: CST.Directive[] = [];
  for (const token of tokens) {
    if (token === document) break;
    if (token.type === "directive") directives.push(token);
    if (token.type === "document") directives.length = 0;
  }
  return directives;
}

function cstNodeEventOffset(
  props: readonly CST.SourceToken[],
  token: CST.Token | null | undefined,
  fallback: number,
): number {
  const property = props.find((item) => item.type === "anchor" || item.type === "tag");
  return property?.offset ?? token?.offset ?? fallback;
}

function cstMappingEventOffset(
  item: CST.CollectionItem,
  indicator: CST.SourceToken | undefined,
): number {
  const explicit = item.start.find((token) => token.type === "explicit-key-ind");
  return explicit?.offset ?? item.key?.offset ?? indicator?.offset ?? itemEndOffset(item);
}

function implicitCstValueOffset(
  item: CST.CollectionItem,
  inFlow: boolean,
  inSequence: boolean,
): number {
  if (inFlow) {
    const indicator = item.sep?.find((token) => token.type === "map-value-ind");
    if (indicator !== undefined) return indicator.offset + indicator.source.length;
  }
  if (inSequence) {
    const indicator = item.start.find((token) => token.type === "seq-item-ind");
    if (indicator !== undefined) return indicator.offset + indicator.source.length;
  }
  return itemEndOffset(item);
}

function emptyCstKeyOffset(
  props: readonly CST.SourceToken[],
  indicator: CST.SourceToken | undefined,
  token: CST.Token | null | undefined,
): number {
  if (token !== null && token !== undefined) return token.offset;
  const explicit = props.find((property) => property.type === "explicit-key-ind");
  if (explicit !== undefined) return explicit.offset + explicit.source.length;
  if (indicator !== undefined) return indicator.offset + indicator.source.length;
  const last = props.at(-1);
  return last === undefined ? 0 : last.offset + last.source.length;
}

function exceedsCodePointLimit(value: string, limit: number): boolean {
  let count = 0;
  for (const _character of value) {
    count += 1;
    if (count > limit) return true;
  }
  return false;
}

function rejectCstSyntaxPolicies(document: CST.Document, sourceText: SourceText): void {
  const stack: (CST.Token | null | undefined)[] = [document.value];
  while (stack.length > 0) {
    const token = stack.pop();
    if (!CST.isCollection(token)) continue;
    for (const item of token.items) {
      if (
        token.type === "flow-collection" &&
        token.start.type === "flow-seq-start" &&
        item.key === null &&
        !item.start.some((property) => property.type === "explicit-key-ind")
      ) {
        const indicator = item.sep?.find((property) => property.type === "map-value-ind");
        if (indicator !== undefined) {
          throw syntaxErrorAt("invalid YAML syntax", indicator.offset, sourceText);
        }
      }
      stack.push(item.key, item.value);
    }
  }
}

function cstKeyText(token: CST.Token | null | undefined): string | null {
  if (token === null || token === undefined || !isCstScalar(token)) return null;
  return CST.resolveAsScalar(token, true)?.value ?? null;
}

function isCstScalar(
  token: CST.Token | null | undefined,
): token is CST.FlowScalar | CST.BlockScalar {
  if (token === null || token === undefined) return false;
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
  if (!taggedIntegerPattern.test(cleaned)) {
    throw valueErrorAt("invalid integer scalar", path, offset, sourceText);
  }
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
  if (!taggedFloatPattern.test(cleaned)) {
    throw valueErrorAt("invalid numeric scalar", path, offset, sourceText);
  }
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
  if ("flow" in node && node.flow === true) {
    if (isMap(node) && node.srcToken === undefined) {
      let end = node.range[1];
      for (const pair of node.items) {
        const item = pair.srcToken;
        if (item === undefined) continue;
        for (const token of [
          ...item.start,
          ...(item.sep ?? []),
          ...(item.key === null || item.key === undefined ? [] : [item.key]),
          ...(item.value === undefined ? [] : [item.value]),
        ]) {
          end = Math.max(end, cstTokenEnd(token));
        }
      }
      return { start: span.start, end: sourceText.point(end) };
    }
    return span;
  }
  return { start: span.start, end: sourceText.nextLinePoint(node.range[1]) };
}

function cstTokenEnd(token: CST.Token): number {
  let end = token.offset;
  if ("source" in token) end += token.source.length;
  if ("end" in token && token.end !== undefined) {
    for (const trailing of token.end) {
      end = Math.max(end, trailing.offset + trailing.source.length);
    }
  }
  return end;
}

function utf8Size(value: string): number {
  return new TextEncoder().encode(value).byteLength;
}
