/**
 * Canonical JSON Schema profile shared with the Python implementation. Both compilers
 * run their raw output through this so a Pydantic-compiled and a Zod-compiled schema
 * converge to the same canonical schema content with an equal schema_sha256.
 *
 * Transforms (schema-aware): drop auto-generated `title` keywords (never property
 * names), strip implicit `default: null`, and rewrite only provably disjoint nullable
 * `oneOf` unions to `anyOf`. Key ordering is handled at serialization time.
 */

import { isMapping } from "./guards.js";

type Json = unknown;

const NAME_MAP_KEYWORDS = new Set([
  "properties",
  "$defs",
  "definitions",
  "patternProperties",
  "dependentSchemas",
]);
const SCHEMA_LIST_KEYWORDS = new Set(["anyOf", "oneOf", "allOf", "prefixItems"]);
const SCHEMA_KEYWORDS = new Set([
  "items",
  "additionalProperties",
  "unevaluatedProperties",
  "unevaluatedItems",
  "not",
  "if",
  "then",
  "else",
  "contains",
  "propertyNames",
  "contentSchema",
]);
const CHILD_SCHEMA_KEYWORDS = new Set([
  "items",
  "additionalProperties",
  "unevaluatedProperties",
  "unevaluatedItems",
  "contains",
  "propertyNames",
  "contentSchema",
]);
const SAME_INSTANCE_SCHEMA_KEYWORDS = new Set(["not", "if", "then", "else"]);
const SAME_INSTANCE_LIST_KEYWORDS = new Set(["anyOf", "oneOf", "allOf"]);
const NULL_ANNOTATION_KEYWORDS = new Set([
  "type",
  "title",
  "description",
  "$comment",
  "default",
  "deprecated",
  "readOnly",
  "writeOnly",
  "examples",
]);

export const ENFORCEMENT_UNSUPPORTED_MESSAGE =
  "enforced validation cannot be applied safely to this schema";

/** Raised when the strict overlay cannot preserve a schema's composition semantics. */
export class EnforcementUnsupportedError extends Error {
  constructor(readonly schemaPath: string) {
    super(ENFORCEMENT_UNSUPPORTED_MESSAGE);
    this.name = "EnforcementUnsupportedError";
  }
}

export function canonicalizeJsonSchema(schema: Record<string, Json>): Record<string, Json> {
  return canonicalizeSchema(schema, schema) as Record<string, Json>;
}

function isEmptyDefault(value: Json): boolean {
  if (value === null) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (isMapping(value)) return Object.keys(value).length === 0;
  return false;
}

function isStringKeyConstraint(value: Json): boolean {
  return isMapping(value) && Object.keys(value).length === 1 && value.type === "string";
}

function canonicalizeSchema(node: Json, root: Record<string, Json>): Json {
  if (!isMapping(node)) {
    return node;
  }
  const normalized = normalizeNullableUnion(node, root);
  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(normalized)) {
    if (key === "title") continue;
    // Drop implicit/empty defaults (null, [], {}); Pydantic omits these, Zod emits them.
    if (key === "default" && isEmptyDefault(value)) continue;
    // Drop Zod's JS safe-integer sentinel bounds (z.int() adds these for unbounded sides).
    if (key === "minimum" && value === Number.MIN_SAFE_INTEGER) continue;
    if (key === "maximum" && value === Number.MAX_SAFE_INTEGER) continue;
    // Drop the redundant string-key constraint z.record emits; JSON keys are always strings.
    if (key === "propertyNames" && isStringKeyConstraint(value)) continue;
    if (key === "required" && Array.isArray(value)) {
      // `required` is a set; sort it so cross-language field order is irrelevant.
      out[key] = [...(value as string[])].sort();
      continue;
    }
    if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
      const mapped: Record<string, Json> = {};
      for (const [name, sub] of Object.entries(value)) {
        mapped[name] = canonicalizeSchema(sub, root);
      }
      out[key] = mapped;
    } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
      out[key] = value.map((item) => canonicalizeSchema(item, root));
    } else if (SCHEMA_KEYWORDS.has(key)) {
      out[key] = canonicalizeSchema(value, root);
    } else {
      out[key] = value;
    }
  }
  return out;
}

function normalizeNullableUnion(
  node: Record<string, Json>,
  root: Record<string, Json>,
): Record<string, Json> {
  const union = node.oneOf;
  if (!Array.isArray(union) || "anyOf" in node) {
    return node;
  }
  if (!isNullableUnion(union, root)) {
    return node;
  }
  const { oneOf: _oneOf, ...rest } = node;
  return { ...rest, anyOf: union };
}

function isNullableUnion(union: Json[], root: Record<string, Json>): boolean {
  if (union.length !== 2) return false;
  const nullIndexes = union.flatMap((entry, index) => (isExactNullSchema(entry) ? [index] : []));
  if (nullIndexes.length !== 1) return false;
  return schemaExcludesNull(union[1 - (nullIndexes[0] as number)], root, new Set());
}

function isExactNullSchema(value: Json): boolean {
  return (
    isMapping(value) &&
    value.type === "null" &&
    Object.keys(value).every((key) => NULL_ANNOTATION_KEYWORDS.has(key))
  );
}

function schemaExcludesNull(value: Json, root: Record<string, Json>, seen: Set<object>): boolean {
  if (!isMapping(value)) return false;
  const schemaType = value.type;
  if (typeof schemaType === "string") return schemaType !== "null";
  if (Array.isArray(schemaType) && schemaType.length > 0) return !schemaType.includes("null");
  const reference = value.$ref;
  if (typeof reference !== "string") return false;
  const target = resolveInternalReference(root, reference);
  if (!isMapping(target) || seen.has(target)) return false;
  return schemaExcludesNull(target, root, new Set([...seen, target]));
}

function resolveInternalReference(root: Record<string, Json>, reference: string): Json | null {
  const hashIndex = reference.indexOf("#");
  const resourceId = hashIndex === -1 ? reference : reference.slice(0, hashIndex);
  const fragment = hashIndex === -1 ? "" : reference.slice(hashIndex + 1);
  if (resourceId !== "" && resourceId !== root.$id) return null;
  if (resourceId === "" && !reference.startsWith("#") && reference !== "") return null;
  if (fragment === "") return root;
  if (!fragment.startsWith("/")) return null;
  let decoded: string;
  try {
    decoded = decodeURIComponent(fragment.slice(1));
  } catch {
    return null;
  }
  let current: Json = root;
  for (const encoded of decoded.split("/")) {
    const token = encoded.replace(/~1/g, "/").replace(/~0/g, "~");
    if (isMapping(current) && Object.hasOwn(current, token)) {
      current = current[token];
    } else if (Array.isArray(current) && /^\d+$/.test(token) && Number(token) < current.length) {
      current = current[Number(token)];
    } else {
      return null;
    }
  }
  return current;
}

/**
 * Return a composition-aware `status: enforced` overlay. Simple object boundaries retain
 * `additionalProperties: false`; composed boundaries use `unevaluatedProperties: false`.
 * Explicit closure keywords win, free-form mappings remain open, and unsafe compositions
 * throw `EnforcementUnsupportedError`. Validation-time only; never changes compiler output.
 */
export function applyEnforcedExtras(schema: Record<string, Json>): Record<string, Json> {
  return applyEnforced(schema, schema, true, []) as Record<string, Json>;
}

function applyEnforced(
  node: Json,
  root: Record<string, Json>,
  closeBoundary: boolean,
  path: readonly (string | number)[],
): Json {
  if (!isMapping(node)) {
    return node;
  }
  checkEnforcementSupport(node, root, path);
  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(node)) {
    if ((key === "properties" || key === "patternProperties") && isMapping(value)) {
      const mapped: Record<string, Json> = {};
      for (const [name, sub] of Object.entries(value)) {
        mapped[name] = applyEnforced(sub, root, true, [...path, key, name]);
      }
      out[key] = mapped;
    } else if (
      (key === "$defs" || key === "definitions" || key === "dependentSchemas") &&
      isMapping(value)
    ) {
      const mapped: Record<string, Json> = {};
      for (const [name, sub] of Object.entries(value)) {
        mapped[name] = applyEnforced(sub, root, false, [...path, key, name]);
      }
      out[key] = mapped;
    } else if (SAME_INSTANCE_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
      out[key] = value.map((item, index) =>
        applyEnforced(item, root, false, [...path, key, index]),
      );
    } else if (key === "prefixItems" && Array.isArray(value)) {
      out[key] = value.map((item, index) => applyEnforced(item, root, true, [...path, key, index]));
    } else if (CHILD_SCHEMA_KEYWORDS.has(key)) {
      out[key] = applyEnforced(value, root, true, [...path, key]);
    } else if (SAME_INSTANCE_SCHEMA_KEYWORDS.has(key)) {
      out[key] = applyEnforced(value, root, false, [...path, key]);
    } else {
      out[key] = value;
    }
  }
  if (
    closeBoundary &&
    !("additionalProperties" in out) &&
    !("unevaluatedProperties" in out) &&
    objectPropertiesAreEvaluated(node, root, new Set())
  ) {
    checkStaticObjectBoundary(node, root, path);
    const keyword = compositionEvaluatesObjectProperties(node, root)
      ? "unevaluatedProperties"
      : "additionalProperties";
    out[keyword] = false;
  }
  return out;
}

function checkStaticObjectBoundary(
  node: Record<string, Json>,
  root: Record<string, Json>,
  path: readonly (string | number)[],
): void {
  const directNames = new Set(isMapping(node.properties) ? Object.keys(node.properties) : []);
  if (objectPropertiesAreEvaluated(node.if, root, new Set())) {
    const conditionalProperties = isMapping(node.if) ? node.if.properties : null;
    if (
      !isMapping(conditionalProperties) ||
      Object.keys(conditionalProperties).some((name) => !directNames.has(name))
    ) {
      throw new EnforcementUnsupportedError(jsonPointer([...path, "if"]));
    }
  }
  if (isMapping(node.dependentSchemas)) {
    for (const name of Object.keys(node.dependentSchemas)) {
      if (!directNames.has(name)) {
        throw new EnforcementUnsupportedError(jsonPointer([...path, "dependentSchemas", name]));
      }
    }
  }
}

function checkEnforcementSupport(
  node: Record<string, Json>,
  root: Record<string, Json>,
  path: readonly (string | number)[],
): void {
  for (const keyword of ["$dynamicRef", "$recursiveRef"] as const) {
    if (keyword in node) throw new EnforcementUnsupportedError(jsonPointer([...path, keyword]));
  }
  const reference = node.$ref;
  if (typeof reference === "string" && resolveInternalReference(root, reference) === null) {
    throw new EnforcementUnsupportedError(jsonPointer([...path, "$ref"]));
  }
  if (containsEnforceableObject(node.not, root, new Set())) {
    throw new EnforcementUnsupportedError(jsonPointer([...path, "not"]));
  }
}

function objectPropertiesAreEvaluated(
  node: Json,
  root: Record<string, Json>,
  seen: Set<object>,
): boolean {
  if (!isMapping(node) || seen.has(node)) return false;
  const nextSeen = new Set([...seen, node]);
  if (isMapping(node.properties) || isMapping(node.patternProperties)) return true;
  if (typeof node.$ref === "string") {
    const target = resolveInternalReference(root, node.$ref);
    if (objectPropertiesAreEvaluated(target, root, nextSeen)) return true;
  }
  for (const keyword of SAME_INSTANCE_LIST_KEYWORDS) {
    const value = node[keyword];
    if (
      Array.isArray(value) &&
      value.some((item) => objectPropertiesAreEvaluated(item, root, nextSeen))
    ) {
      return true;
    }
  }
  for (const keyword of ["then", "else"]) {
    if (objectPropertiesAreEvaluated(node[keyword], root, nextSeen)) return true;
  }
  return (
    isMapping(node.dependentSchemas) &&
    Object.values(node.dependentSchemas).some((item) =>
      objectPropertiesAreEvaluated(item, root, nextSeen),
    )
  );
}

function compositionEvaluatesObjectProperties(
  node: Record<string, Json>,
  root: Record<string, Json>,
): boolean {
  const seen = new Set<object>([node]);
  if (
    typeof node.$ref === "string" &&
    objectPropertiesAreEvaluated(resolveInternalReference(root, node.$ref), root, seen)
  ) {
    return true;
  }
  for (const keyword of SAME_INSTANCE_LIST_KEYWORDS) {
    const value = node[keyword];
    if (
      Array.isArray(value) &&
      value.some((item) => objectPropertiesAreEvaluated(item, root, seen))
    ) {
      return true;
    }
  }
  for (const keyword of ["then", "else"]) {
    if (objectPropertiesAreEvaluated(node[keyword], root, seen)) return true;
  }
  return (
    isMapping(node.dependentSchemas) &&
    Object.values(node.dependentSchemas).some((item) =>
      objectPropertiesAreEvaluated(item, root, seen),
    )
  );
}

function containsEnforceableObject(
  node: Json,
  root: Record<string, Json>,
  seen: Set<object>,
): boolean {
  if (!isMapping(node) || seen.has(node)) return false;
  const nextSeen = new Set([...seen, node]);
  if (objectPropertiesAreEvaluated(node, root, new Set())) return true;
  for (const keyword of NAME_MAP_KEYWORDS) {
    const value = node[keyword];
    if (
      isMapping(value) &&
      Object.values(value).some((item) => containsEnforceableObject(item, root, nextSeen))
    ) {
      return true;
    }
  }
  for (const keyword of SCHEMA_LIST_KEYWORDS) {
    const value = node[keyword];
    if (
      Array.isArray(value) &&
      value.some((item) => containsEnforceableObject(item, root, nextSeen))
    ) {
      return true;
    }
  }
  for (const keyword of SCHEMA_KEYWORDS) {
    if (containsEnforceableObject(node[keyword], root, nextSeen)) return true;
  }
  return false;
}

function jsonPointer(path: readonly (string | number)[]): string {
  return path.map((part) => `/${String(part).replace(/~/g, "~0").replace(/\//g, "~1")}`).join("");
}
