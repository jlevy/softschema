/** Bounded UTF-8 and portable YAML input shared by artifact and schema reads. */
import { readFileSync, statSync } from "node:fs";
import { isAlias, isCollection, isPair, isScalar, parseDocument, visit } from "yaml";

export const MAX_INPUT_BYTES = 1_048_576;
const MAX_DEPTH = 64;
const MAX_NODES = 100_000;
const MAX_SCALAR_BYTES = 262_144;
const MAX_SAFE_INTEGER = 9_007_199_254_740_991;

export class PortableInputError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export function readUtf8(path: string): string {
  const size = statSync(path).size;
  if (size > MAX_INPUT_BYTES) {
    throw new PortableInputError(
      "input_too_large",
      `input is ${size} bytes; limit is ${MAX_INPUT_BYTES}`,
    );
  }
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
  const document = parseDocument(text, { uniqueKeys: true });
  if (document.errors.length > 0) {
    const message = document.errors[0]?.message ?? "invalid YAML";
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

  let nodes = 0;
  let hasAlias = false;
  visit(document, (_key, node, path) => {
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
      node.type === "PLAIN" &&
      typeof node.source === "string" &&
      /^\d{4}-\d{2}-\d{2}(?:[Tt]|$)/u.test(node.source)
    ) {
      throw new PortableInputError("yaml_unsupported_scalar", "timestamps are not supported");
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
    if (isScalar(node) || isCollection(node)) nodes += 1;
    if (nodes > MAX_NODES) {
      throw new PortableInputError("yaml_limit", "YAML exceeds the node limit");
    }
    if (
      isScalar(node) &&
      Buffer.byteLength(String(node.source ?? node.value), "utf8") > MAX_SCALAR_BYTES
    ) {
      throw new PortableInputError("yaml_limit", "YAML scalar exceeds the size limit");
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
  const stack: Array<[unknown, number]> = [[root, 0]];
  let nodes = 0;
  while (stack.length > 0) {
    const [value, depth] = stack.pop() as [unknown, number];
    nodes += 1;
    if (nodes > MAX_NODES || depth > MAX_DEPTH) {
      throw new PortableInputError("yaml_limit", "YAML value exceeds the structure limit");
    }
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
      stack.push(...value.map((item): [unknown, number] => [item, depth + 1]));
      continue;
    }
    if (typeof value === "object") {
      stack.push(...Object.values(value).map((item): [unknown, number] => [item, depth + 1]));
      continue;
    }
    throw new PortableInputError(
      "yaml_unsupported_scalar",
      `unsupported YAML value: ${typeof value}`,
    );
  }
}
