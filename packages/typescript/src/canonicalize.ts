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

/**
 * Applicators whose subschemas each contribute *part* of one instance's constraints
 * rather than describing it completely. A fragment is never closed internally: its
 * `properties` is a partial contribution (or, for `if`, a matcher rather than a
 * declaration), so closing it would reject keys a sibling fragment declares, or stop a
 * conditional from firing at all. Their contributions are closed at the composition
 * root instead, with annotation-aware `unevaluatedProperties`.
 *
 * `anyOf`/`oneOf` are deliberately absent: an alternative branch describes the instance
 * completely, so it closes on its own terms (the compiled shape of an optional model
 * field is `anyOf: [{$ref: ...}, {"type": "null"}]`).
 */
const FRAGMENT_APPLICATORS = new Set(["allOf", "if", "then", "else", "not", "dependentSchemas"]);

/**
 * Definition keywords reset the fragment flag: a definition is a complete declaration
 * reached by `$ref`, so it closes on its own terms even when the reference sits inside a
 * fragment.
 */
const DEFINITION_KEYWORDS = new Set(["$defs", "definitions"]);
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
 * Return a copy of `schema` with the `status: enforced` strictness overlay.
 *
 * Under `enforced` the schema is authoritative at the boundary: an object schema that
 * declares properties but is silent about closure is validated as closed. Three clauses
 * decide where and how, because a schema that *composes* constraints cannot be closed
 * the same way as one that declares them in a single place:
 *
 * 1. Closure is never injected inside a fragment subtree
 *    (`allOf`/`if`/`then`/`else`/`not`/`dependentSchemas`). A fragment contributes part
 *    of an instance's constraints, so closing it would reject keys a sibling fragment
 *    declares; closing an `if` matcher would silently stop the conditional from firing.
 *    `$defs` resets this — a definition is a complete declaration reached by `$ref`.
 * 2. A node declares properties if it carries `properties`, *or* if a fragment
 *    applicator under it does. The second half matters: a schema may declare every
 *    property inside its `allOf` branches, and would otherwise be enforced nowhere.
 * 3. Such a node is closed with `unevaluatedProperties: false` when it carries a
 *    fragment applicator, and `additionalProperties: false` otherwise.
 *    `unevaluatedProperties` is annotation-aware, so properties evaluated by
 *    `properties`, by an `allOf` branch, by a successful `if`, by `then`, `else`,
 *    `dependentSchemas`, or through `$ref` all count as declared, and only genuinely
 *    undeclared keys fail.
 *
 * An explicit `additionalProperties` or `unevaluatedProperties` always wins, and object
 * schemas that declare no properties anywhere (free-form mappings) are unaffected.
 * Validation-time only; never changes compiled schemas. Mirrors the Python
 * `apply_enforced_extras` exactly.
 */
export function applyEnforcedExtras(schema: Record<string, Json>): Record<string, Json> {
  return applyEnforced(schema, false) as Record<string, Json>;
}

function applyEnforced(node: Json, inFragment: boolean): Json {
  if (!isMapping(node)) {
    return node;
  }

  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(node)) {
    // A definition is a complete declaration, so it closes even inside a fragment.
    const childFragment =
      (DEFINITION_KEYWORDS.has(key) ? false : inFragment) || FRAGMENT_APPLICATORS.has(key);
    if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
      const mapped: Record<string, Json> = {};
      for (const [name, sub] of Object.entries(value)) {
        mapped[name] = applyEnforced(sub, childFragment);
      }
      out[key] = mapped;
    } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
      out[key] = value.map((item) => applyEnforced(item, childFragment));
    } else if (SCHEMA_KEYWORDS.has(key)) {
      out[key] = applyEnforced(value, childFragment);
    } else {
      out[key] = value;
    }
  }

  if (inFragment) return out;
  if ("additionalProperties" in out || "unevaluatedProperties" in out) return out;
  const hasFragment = Object.keys(out).some((key) => FRAGMENT_APPLICATORS.has(key));
  if (isMapping(out.properties)) {
    out[hasFragment ? "unevaluatedProperties" : "additionalProperties"] = false;
  } else if (hasFragment && fragmentDeclaresProperties(out)) {
    out.unevaluatedProperties = false;
  }
  return out;
}

/**
 * Whether a fragment applicator under `node` declares `properties`. Recurses through
 * fragment applicators only. A `$ref` is not followed: it is not a lexical declaration,
 * and the definition it names closes on its own terms.
 */
function fragmentDeclaresProperties(node: Record<string, Json>): boolean {
  return Object.entries(node).some(
    ([key, value]) => FRAGMENT_APPLICATORS.has(key) && declaresProperties(value),
  );
}

function declaresProperties(node: Json): boolean {
  if (Array.isArray(node)) return node.some(declaresProperties);
  if (!isMapping(node)) return false;
  if (isMapping(node.properties)) return true;
  return fragmentDeclaresProperties(node);
}
