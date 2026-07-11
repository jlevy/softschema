/**
 * Canonical JSON Schema profile shared with the Python implementation. Both compilers
 * run their raw output through this so a Pydantic-compiled and a Zod-compiled schema
 * converge to the same canonical schema content with an equal schema_sha256.
 *
 * Transforms are schema-aware: preserve annotations and unknown data, rewrite only an
 * exact nullable `oneOf` to `anyOf`, and sort set-like arrays. Key ordering is handled
 * at serialization time.
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

export function canonicalizeJsonSchema(schema: Record<string, Json>): Record<string, Json> {
  return canonicalizeSchema(schema) as Record<string, Json>;
}

function isStringKeyConstraint(value: Json): boolean {
  return isMapping(value) && Object.keys(value).length === 1 && value.type === "string";
}

function canonicalizeSchema(node: Json): Json {
  if (!isMapping(node)) {
    return node;
  }
  const normalized = normalizeNullableUnion(node);
  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(normalized)) {
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
  const hasNull = union.some((e) => isMapping(e) && e.type === "null");
  const hasOther = union.some((e) => isMapping(e) && e.type !== "null");
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

export class EnforcementUnsupportedError extends Error {}

function applyEnforced(node: Json): Json {
  if (!isMapping(node)) {
    return node;
  }
  if (Array.isArray(node.allOf) && node.allOf.some(containsOpenProperties)) {
    throw new EnforcementUnsupportedError(
      "enforced closure is unsupported for allOf object composition",
    );
  }
  if (
    isMapping(node.dependentSchemas) &&
    Object.values(node.dependentSchemas).some(containsOpenProperties)
  ) {
    throw new EnforcementUnsupportedError(
      "enforced closure is unsupported for dependent object composition",
    );
  }
  if ([node.if, node.then, node.else, node.not].some(containsOpenProperties)) {
    throw new EnforcementUnsupportedError(
      "enforced closure is unsupported for conditional object composition",
    );
  }
  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(node)) {
    if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
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
  if (isMapping(out.properties) && !("additionalProperties" in out)) {
    out.additionalProperties = false;
  }
  return out;
}

function containsOpenProperties(node: Json): boolean {
  if (!isMapping(node)) return false;
  if (isMapping(node.properties) && !("additionalProperties" in node)) return true;
  for (const [key, value] of Object.entries(node)) {
    if (SCHEMA_KEYWORDS.has(key) && containsOpenProperties(value)) return true;
    if (
      SCHEMA_LIST_KEYWORDS.has(key) &&
      Array.isArray(value) &&
      value.some(containsOpenProperties)
    ) {
      return true;
    }
    if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
      if (Object.values(value).some(containsOpenProperties)) return true;
    }
  }
  return false;
}
