/** Official Node/Bun adapter for language-neutral conformance vector suites. */

import { readSync } from "node:fs";
import { pathToFileURL } from "node:url";

const REQUEST_FORMAT = "softschema-vector-suite-v1";
const MAX_REQUEST_BYTES = 16 * 1024 * 1024;
const MAX_REQUEST_CASES = 4_096;
const MAX_JSON_DEPTH = 128;
const MAX_JSON_NODES = 100_000;
const REQUEST_READ_CHUNK_BYTES = 64 * 1024;
const STDIN_FILE_DESCRIPTOR = 0;
const HIGH_SURROGATE_START = 0xd800;
const HIGH_SURROGATE_END = 0xdbff;
const LOW_SURROGATE_START = 0xdc00;
const LOW_SURROGATE_END = 0xdfff;
const IDENTIFIER_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const LIMIT_FIELDS = new Set([
  "max_resource_bytes",
  "max_bundle_bytes",
  "max_resources",
  "max_nodes_per_resource",
  "max_depth",
  "max_scalar_codepoints",
]);
const POSITIVE_LIMIT_FIELDS = new Set(["max_resources", "max_nodes_per_resource", "max_depth"]);
const OPERATIONS = new Set([
  "canonicalize",
  "diagnostic-summary",
  "identity",
  "metadata",
  "pattern",
  "portable-yaml",
  "validate-structural",
]);

class AdapterRequestError extends Error {}

function readBoundedStdin() {
  const chunks = [];
  let total = 0;
  while (total <= MAX_REQUEST_BYTES) {
    const remaining = MAX_REQUEST_BYTES + 1 - total;
    const chunk = Buffer.allocUnsafe(Math.min(REQUEST_READ_CHUNK_BYTES, remaining));
    const count = readSync(STDIN_FILE_DESCRIPTOR, chunk, 0, chunk.byteLength, null);
    if (count === 0) break;
    chunks.push(chunk.subarray(0, count));
    total += count;
  }
  if (total > MAX_REQUEST_BYTES) {
    throw new AdapterRequestError("request exceeds the byte limit");
  }
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks, total));
  } catch (error) {
    throw new AdapterRequestError("request is not strict UTF-8 JSON", { cause: error });
  }
}

function hasUnpairedSurrogate(value) {
  for (let index = 0; index < value.length; index += 1) {
    const current = value.charCodeAt(index);
    if (current >= HIGH_SURROGATE_START && current <= HIGH_SURROGATE_END) {
      const next = value.charCodeAt(index + 1);
      if (
        index + 1 >= value.length ||
        next < LOW_SURROGATE_START ||
        next > LOW_SURROGATE_END
      ) {
        return true;
      }
      index += 1;
    } else if (current >= LOW_SURROGATE_START && current <= LOW_SURROGATE_END) {
      return true;
    }
  }
  return false;
}

function rejectDuplicateJsonKeys(text) {
  let index = 0;
  let nodes = 0;
  const skipWhitespace = () => {
    while (
      text[index] === " " ||
      text[index] === "\t" ||
      text[index] === "\r" ||
      text[index] === "\n"
    ) {
      index += 1;
    }
  };
  const scanString = (decode) => {
    const start = index;
    index += 1;
    while (index < text.length) {
      if (text[index] === "\\") {
        index += 2;
      } else if (text[index] === "\"") {
        index += 1;
        return decode ? JSON.parse(text.slice(start, index)) : undefined;
      } else {
        index += 1;
      }
    }
    throw new AdapterRequestError("request is not strict UTF-8 JSON");
  };
  const scanValue = (depth) => {
    if (depth > MAX_JSON_DEPTH) {
      throw new AdapterRequestError("request exceeds the depth limit");
    }
    nodes += 1;
    if (nodes > MAX_JSON_NODES) {
      throw new AdapterRequestError("request exceeds the node limit");
    }
    skipWhitespace();
    if (text[index] === "{") {
      scanObject(depth);
    } else if (text[index] === "[") {
      scanArray(depth);
    } else if (text[index] === "\"") {
      scanString(false);
    } else {
      while (index < text.length && !",]} \t\r\n".includes(text[index])) {
        index += 1;
      }
    }
  };
  const scanObject = (depth) => {
    index += 1;
    skipWhitespace();
    const keys = new Set();
    if (text[index] === "}") {
      index += 1;
      return;
    }
    while (index < text.length) {
      const key = scanString(true);
      if (keys.has(key)) {
        throw new AdapterRequestError(`duplicate JSON key: ${key}`);
      }
      keys.add(key);
      skipWhitespace();
      index += 1; // JSON.parse already proved this token is a colon.
      scanValue(depth + 1);
      skipWhitespace();
      if (text[index] === "}") {
        index += 1;
        return;
      }
      index += 1;
      skipWhitespace();
    }
  };
  const scanArray = (depth) => {
    index += 1;
    skipWhitespace();
    if (text[index] === "]") {
      index += 1;
      return;
    }
    while (index < text.length) {
      scanValue(depth + 1);
      skipWhitespace();
      if (text[index] === "]") {
        index += 1;
        return;
      }
      index += 1;
    }
  };
  scanValue(1);
}

function validateJsonStructure(value) {
  let nodes = 0;
  const stack = [{ value, depth: 1 }];
  while (stack.length > 0) {
    const current = stack.pop();
    if (current.depth > MAX_JSON_DEPTH) {
      throw new AdapterRequestError("request exceeds the depth limit");
    }
    nodes += 1;
    if (nodes > MAX_JSON_NODES) {
      throw new AdapterRequestError("request exceeds the node limit");
    }
    if (typeof current.value === "string") {
      if (hasUnpairedSurrogate(current.value)) {
        throw new AdapterRequestError("request contains an invalid Unicode scalar value");
      }
    } else if (typeof current.value === "number") {
      if (!Number.isFinite(current.value)) {
        throw new AdapterRequestError("request contains a non-finite JSON number");
      }
    } else if (Array.isArray(current.value)) {
      for (const item of current.value) stack.push({ value: item, depth: current.depth + 1 });
    } else if (current.value !== null && typeof current.value === "object") {
      for (const [key, item] of Object.entries(current.value)) {
        if (hasUnpairedSurrogate(key)) {
          throw new AdapterRequestError("request contains an invalid Unicode scalar key");
        }
        stack.push({ value: item, depth: current.depth + 1 });
      }
    }
  }
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactFields(value, required, allowed) {
  const fields = Object.keys(value);
  return (
    required.every((field) => Object.hasOwn(value, field)) &&
    fields.every((field) => allowed.has(field))
  );
}

function isIdentifier(value) {
  const match = typeof value === "string" ? value.match(IDENTIFIER_PATTERN) : null;
  return match?.[0] === value;
}

function invalidCaseInput(index, operation, detail) {
  throw new AdapterRequestError(`request case ${index} input for ${operation} ${detail}`);
}

function validateLimitFields(value, index, operation) {
  if (!isObject(value) || !Object.keys(value).every((field) => LIMIT_FIELDS.has(field))) {
    invalidCaseInput(index, operation, "limits has invalid fields");
  }
  for (const [field, limit] of Object.entries(value)) {
    const minimum = POSITIVE_LIMIT_FIELDS.has(field) ? 1 : 0;
    if (!Number.isSafeInteger(limit) || limit < minimum) {
      const qualifier = minimum === 1 ? "positive" : "nonnegative";
      invalidCaseInput(
        index,
        operation,
        `limit ${field} must be a ${qualifier} safe integer`,
      );
    }
  }
}

function validateCaseInput(operation, value, index) {
  if (operation === "canonicalize") {
    const required = ["schema"];
    if (!hasExactFields(value, required, new Set([...required, "instances"]))) {
      invalidCaseInput(index, operation, "has missing or unexpected fields");
    }
    if (!isObject(value.schema)) invalidCaseInput(index, operation, "schema must be an object");
    if (value.instances !== undefined && !Array.isArray(value.instances)) {
      invalidCaseInput(index, operation, "instances must be an array");
    }
    return;
  }
  if (operation === "diagnostic-summary") {
    const required = ["profile", "results"];
    if (!hasExactFields(value, required, new Set(required))) {
      invalidCaseInput(index, operation, "has missing or unexpected fields");
    }
    if (value.profile !== "frontmatter-md" && value.profile !== "pure-yaml") {
      invalidCaseInput(index, operation, "profile is unsupported");
    }
    if (!Array.isArray(value.results) || value.results.length === 0) {
      invalidCaseInput(index, operation, "results must be a non-empty array");
    }
    return;
  }
  if (operation === "identity") {
    const required = ["kind", "value"];
    if (!hasExactFields(value, required, new Set(required))) {
      invalidCaseInput(index, operation, "has missing or unexpected fields");
    }
    if (!new Set(["contract", "extension", "schema"]).has(value.kind)) {
      invalidCaseInput(index, operation, "kind is unsupported");
    }
    return;
  }
  if (operation === "metadata") {
    const required = ["raw"];
    if (!hasExactFields(value, required, new Set(required))) {
      invalidCaseInput(index, operation, "has missing or unexpected fields");
    }
    return;
  }
  if (operation === "pattern") {
    const required = ["pattern"];
    if (!hasExactFields(value, required, new Set([...required, "value"]))) {
      invalidCaseInput(index, operation, "has missing or unexpected fields");
    }
    if (typeof value.pattern !== "string") {
      invalidCaseInput(index, operation, "pattern must be a string");
    }
    if (value.value !== undefined && typeof value.value !== "string") {
      invalidCaseInput(index, operation, "value must be a string");
    }
    return;
  }
  if (operation === "portable-yaml") {
    const required = ["text"];
    const allowed = new Set([...required, "limits", "include_location", "source_pointers"]);
    if (!hasExactFields(value, required, allowed)) {
      invalidCaseInput(index, operation, "has missing or unexpected fields");
    }
    if (typeof value.text !== "string") {
      invalidCaseInput(index, operation, "text must be a string");
    }
    if (value.limits !== undefined) validateLimitFields(value.limits, index, operation);
    if (value.include_location !== undefined && typeof value.include_location !== "boolean") {
      invalidCaseInput(index, operation, "include_location must be a boolean");
    }
    if (value.source_pointers !== undefined) {
      const pointers = value.source_pointers;
      if (
        !Array.isArray(pointers) ||
        pointers.length === 0 ||
        pointers.some((pointer) => typeof pointer !== "string") ||
        new Set(pointers).size !== pointers.length
      ) {
        invalidCaseInput(
          index,
          operation,
          "source_pointers must be a non-empty array of unique strings",
        );
      }
    }
    return;
  }
  if (operation === "validate-structural") {
    const required = ["schema", "values"];
    const allowed = new Set([...required, "resources", "strict_extras"]);
    if (!hasExactFields(value, required, allowed)) {
      invalidCaseInput(index, operation, "has missing or unexpected fields");
    }
    if (!isObject(value.schema)) invalidCaseInput(index, operation, "schema must be an object");
    if (value.resources !== undefined && !isObject(value.resources)) {
      invalidCaseInput(index, operation, "resources must be an object");
    }
    if (value.strict_extras !== undefined && typeof value.strict_extras !== "boolean") {
      invalidCaseInput(index, operation, "strict_extras must be a boolean");
    }
    return;
  }
  throw new AdapterRequestError("request operation is unsupported");
}

function parseRequest(text) {
  let request;
  try {
    request = JSON.parse(text);
  } catch (error) {
    throw new AdapterRequestError("request is not strict UTF-8 JSON", { cause: error });
  }
  validateJsonStructure(request);
  rejectDuplicateJsonKeys(text);
  if (!isObject(request)) throw new AdapterRequestError("request must be an object");
  const required = ["format", "id", "operation", "cases"];
  if (!hasExactFields(request, required, new Set([...required, "description"]))) {
    throw new AdapterRequestError("request has missing or unexpected fields");
  }
  if (request.format !== REQUEST_FORMAT) {
    throw new AdapterRequestError("request has an unsupported format");
  }
  if (!isIdentifier(request.id)) {
    throw new AdapterRequestError("request id must be a lowercase kebab identifier");
  }
  if (typeof request.operation !== "string" || !OPERATIONS.has(request.operation)) {
    throw new AdapterRequestError("request operation is unsupported");
  }
  if (
    request.description !== undefined &&
    (typeof request.description !== "string" || request.description.length === 0)
  ) {
    throw new AdapterRequestError("request description must be a non-empty string");
  }
  if (
    !Array.isArray(request.cases) ||
    request.cases.length === 0 ||
    request.cases.length > MAX_REQUEST_CASES
  ) {
    throw new AdapterRequestError("request cases must be a non-empty array");
  }
  const caseIds = new Set();
  for (const [index, testCase] of request.cases.entries()) {
    if (!isObject(testCase)) {
      throw new AdapterRequestError(`request case ${index} must be an object`);
    }
    const caseRequired = ["id", "input", "expected"];
    if (!hasExactFields(testCase, caseRequired, new Set([...caseRequired, "description"]))) {
      throw new AdapterRequestError(`request case ${index} has invalid fields`);
    }
    if (
      !isIdentifier(testCase.id) ||
      caseIds.has(testCase.id)
    ) {
      throw new AdapterRequestError(`request case ${index} has an invalid id`);
    }
    caseIds.add(testCase.id);
    if (!isObject(testCase.input)) {
      throw new AdapterRequestError(`request case ${index} input must be an object`);
    }
    if (!isObject(testCase.expected)) {
      throw new AdapterRequestError(`request case ${index} expected must be an object`);
    }
    if (
      testCase.description !== undefined &&
      (typeof testCase.description !== "string" || testCase.description.length === 0)
    ) {
      throw new AdapterRequestError(
        `request case ${index} description must be a non-empty string`,
      );
    }
    validateCaseInput(request.operation, testCase.input, index);
  }
  return request;
}

function failRequest(error) {
  const message = error instanceof AdapterRequestError ? error.message : "invalid adapter request";
  process.stderr.write(`softschema vector adapter: ${message}\n`);
  process.exit(2);
}

const [nodePath, corePath, yamlPath] = process.argv.slice(2);
if (nodePath === undefined || corePath === undefined || yamlPath === undefined) {
  failRequest(new AdapterRequestError("adapter requires node, core, and YAML module paths"));
}

let request;
try {
  request = parseRequest(readBoundedStdin());
} catch (error) {
  failRequest(error);
}

let nodeModule;
let core;
let yaml;
try {
  nodeModule = await import(pathToFileURL(nodePath).href);
  core = await import(pathToFileURL(corePath).href);
  yaml = await import(pathToFileURL(yamlPath).href);
} catch (error) {
  failRequest(new AdapterRequestError("adapter modules could not be loaded", { cause: error }));
}

function identity(input) {
  const validators = {
    contract: core.validateContractId,
    extension: core.validateExtensionNamespace,
    schema: core.validateSchemaId,
  };
  try {
    const validator = validators[input.kind];
    if (validator === undefined) return { ok: false };
    return { ok: true, value: validator(input.value) };
  } catch {
    return { ok: false };
  }
}

function metadata(input) {
  try {
    return {
      ok: true,
      value: core.metadataToOutput(core.parseSchemaMetadata(input.raw)),
    };
  } catch {
    return { ok: false };
  }
}

function pattern(input) {
  const supported = core.isPortablePattern(input.pattern);
  const result = { ok: true, supported };
  if (Object.hasOwn(input, "value")) {
    result.matches = supported ? core.portablePatternMatches(input.pattern, input.value) : null;
  }
  return result;
}

function validationLimits(input) {
  const limits = input.limits ?? {};
  return {
    ...(limits.max_resource_bytes === undefined
      ? {}
      : { maxResourceBytes: limits.max_resource_bytes }),
    ...(limits.max_bundle_bytes === undefined ? {} : { maxBundleBytes: limits.max_bundle_bytes }),
    ...(limits.max_resources === undefined ? {} : { maxResources: limits.max_resources }),
    ...(limits.max_nodes_per_resource === undefined
      ? {}
      : { maxNodesPerResource: limits.max_nodes_per_resource }),
    ...(limits.max_depth === undefined ? {} : { maxDepth: limits.max_depth }),
    ...(limits.max_scalar_codepoints === undefined
      ? {}
      : { maxScalarCodePoints: limits.max_scalar_codepoints }),
  };
}

function portableYaml(input) {
  try {
    const parsed = yaml.parsePortableYamlWithLocations(input.text, validationLimits(input));
    const result = { ok: true, value: parsed.value };
    if (input.source_pointers !== undefined) {
      result.sources = Object.fromEntries(
        input.source_pointers.map((pointer) => {
          const node = parsed.sourceMap.node(pointer);
          if (node === undefined) {
            throw new AdapterRequestError(`portable-yaml source pointer is unmapped: ${pointer}`);
          }
          return [pointer, { start: node.value.start, end: node.value.end }];
        }),
      );
    }
    return result;
  } catch (error) {
    if (!(error instanceof yaml.PortableYamlError)) throw error;
    const result = {
      ok: false,
      kind: error instanceof yaml.PortableYamlSyntaxError ? "syntax" : "value_domain",
      path: error.path,
    };
    if (input.include_location === true && error.line !== null) result.line = error.line;
    if (input.include_location === true && error.column !== null) result.column = error.column;
    return result;
  }
}

function execute(operation, input) {
  if (operation === "canonicalize") {
    const transformed = core.canonicalizeJsonSchema(input.schema);
    const value = core.normalizePortableValue(transformed).value;
    const validity = (input.instances ?? []).map((instance) => ({
      raw: nodeModule.validateStructural(instance, input.schema).ok,
      canonical: nodeModule.validateStructural(instance, value).ok,
    }));
    return { ok: true, value, validity };
  }
  if (operation === "diagnostic-summary") {
    const aggregate = core.projectDiagnosticAggregate(
      input.profile,
      core.DEFAULT_VALIDATION_LIMITS,
      input.results,
    );
    const jsonl = core.serializeDiagnosticJsonl(aggregate);
    const sarif = core.projectDiagnosticSarif(aggregate);
    const run = sarif.runs[0];
    return {
      ok: aggregate.ok,
      summary: aggregate.summary,
      outcomes: aggregate.results.map((result) => result.outcome),
      rule_ids: aggregate.results.flatMap((result) =>
        result.diagnostics.map((diagnostic) => diagnostic.rule_id),
      ),
      jsonl_records: jsonl.trimEnd().split("\n").length,
      sarif: {
        artifacts: run.artifacts.length,
        column_kind: run.columnKind,
        execution_successful: run.invocations[0].executionSuccessful,
        exit_code: run.invocations[0].exitCode,
        results: run.results.length,
        rules: run.tool.driver.rules.map((rule) => rule.id),
      },
    };
  }
  if (operation === "identity") return identity(input);
  if (operation === "metadata") return metadata(input);
  if (operation === "pattern") return pattern(input);
  if (operation === "portable-yaml") return portableYaml(input);
  if (operation === "validate-structural") {
    return nodeModule.validateStructural(input.values, input.schema, {
      strictExtras: input.strict_extras ?? false,
      resources: input.resources ?? {},
    });
  }
  throw new Error(`unsupported vector operation: ${operation}`);
}

let output;
try {
  const results = request.cases.map((testCase) => ({
    id: testCase.id,
    actual: execute(request.operation, testCase.input),
  }));
  output = JSON.stringify({ format: "softschema-vector-results-v1", id: request.id, results });
} catch (error) {
  const requestError =
    error instanceof AdapterRequestError
      ? error
      : new AdapterRequestError("request execution failed", { cause: error });
  failRequest(requestError);
}
process.stdout.write(`${output}\n`);
