/** Portable YAML input shared by artifact and schema reads.
 *
 * Size and shape ceilings were removed. They only answered whether a hostile document
 * could exhaust the parser, and softschema reads artifacts its own callers just wrote.
 * The portable-value rules here stay, because they are what makes a document mean the
 * same thing in both runtimes.
 */
import { readFileSync } from "node:fs";
import { isAlias, isCollection, isPair, isScalar, parseDocument, visit } from "yaml";

/** Largest integer that survives a round trip through a JS number. */
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
  visit(document, (_key, node) => {
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
