/**
 * Canonical JSON Schema profile shared with the Python implementation. Both compilers
 * run their raw output through this so a Pydantic-compiled and a Zod-compiled schema
 * converge to the same canonical schema content with an equal schema_sha256.
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

function isEmptyDefault(value: Json): boolean {
  if (value === null) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (isPlainObject(value)) return Object.keys(value).length === 0;
  return false;
}

function isStringKeyConstraint(value: Json): boolean {
  return isPlainObject(value) && Object.keys(value).length === 1 && value.type === "string";
}

function canonicalizeSchema(node: Json): Json {
  if (!isPlainObject(node)) {
    return node;
  }
  const normalized = normalizeNullableUnion(node);
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

/**
 * Return a copy of `schema` with the `status: enforced` strictness overlay: every object
 * schema that declares `properties` but is silent about `additionalProperties` is
 * validated as `additionalProperties: false`. An explicit `additionalProperties` always
 * wins, and object schemas without `properties` (free-form mappings) are unaffected.
 * Validation-time only; never changes compiled schemas. Mirrors the Python
 * `apply_enforced_extras` exactly.
 */
export function applyEnforcedExtras(schema: Record<string, Json>): Record<string, Json> {
  return applyEnforced(schema) as Record<string, Json>;
}

function applyEnforced(node: Json): Json {
  if (!isPlainObject(node)) {
    return node;
  }
  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(node)) {
    if (NAME_MAP_KEYWORDS.has(key) && isPlainObject(value)) {
      const mapped: Record<string, Json> = {};
      for (const [name, sub] of Object.entries(value)) {
        mapped[name] = applyEnforced(sub);
      }
      out[key] = mapped;
    } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
      out[key] = value.map(applyEnforced);
    } else if (SCHEMA_KEYWORDS.has(key)) {
      out[key] = applyEnforced(value);
    } else {
      out[key] = value;
    }
  }
  if (isPlainObject(out.properties) && !("additionalProperties" in out)) {
    out.additionalProperties = false;
  }
  return out;
}
