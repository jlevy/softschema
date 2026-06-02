/**
 * Canonical JSON Schema profile shared with the Python implementation. Both compilers
 * run their raw output through this so a Pydantic-compiled and a Zod-compiled sidecar
 * converge to byte-identical output with the same schema_sha256.
 *
 * Transforms (schema-aware): drop auto-generated `title` keywords (never property
 * names), strip implicit `default: null`, rewrite `oneOf` nullable unions to `anyOf`.
 * Key ordering is handled at serialization time.
 */

type Json = unknown;

const NAME_MAP_KEYWORDS = new Set(["properties", "$defs", "definitions", "patternProperties"]);
const SCHEMA_LIST_KEYWORDS = new Set(["anyOf", "oneOf", "allOf", "prefixItems"]);
const SCHEMA_KEYWORDS = new Set([
  "items",
  "additionalProperties",
  "not",
  "if",
  "then",
  "else",
  "contains",
  "propertyNames",
]);

export function canonicalizeJsonSchema(schema: Record<string, Json>): Record<string, Json> {
  return canonicalizeSchema(schema) as Record<string, Json>;
}

function isPlainObject(value: Json): value is Record<string, Json> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function canonicalizeSchema(node: Json): Json {
  if (!isPlainObject(node)) {
    return node;
  }
  const normalized = normalizeNullableUnion(node);
  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(normalized)) {
    if (key === "title") continue;
    if (key === "default" && value === null) continue;
    if (NAME_MAP_KEYWORDS.has(key) && isPlainObject(value)) {
      const mapped: Record<string, Json> = {};
      for (const [name, sub] of Object.entries(value)) {
        mapped[name] = canonicalizeSchema(sub);
      }
      out[key] = mapped;
    } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
      out[key] = value.map(canonicalizeSchema);
    } else if (SCHEMA_KEYWORDS.has(key)) {
      out[key] = canonicalizeSchema(value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

function normalizeNullableUnion(node: Record<string, Json>): Record<string, Json> {
  const union = node.oneOf;
  if (!Array.isArray(union) || "anyOf" in node) {
    return node;
  }
  if (!isNullableUnion(union)) {
    return node;
  }
  const { oneOf: _oneOf, ...rest } = node;
  return { ...rest, anyOf: union };
}

function isNullableUnion(union: Json[]): boolean {
  if (union.length !== 2) return false;
  const hasNull = union.some((e) => isPlainObject(e) && e.type === "null");
  const hasOther = union.some((e) => isPlainObject(e) && e.type !== "null");
  return hasNull && hasOther;
}
