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

/**
 * Reference keywords are in-place applicators: the referenced schema applies to the same
 * instance location, and its annotations flow to the referring node. A node that
 * declares properties *and* references another schema therefore needs the
 * annotation-aware keyword, exactly as a fragment does — `additionalProperties` there
 * would reject the keys the reference contributes.
 */
const REFERENCE_KEYWORDS = new Set(["$ref", "$dynamicRef"]);
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
 * declares properties but is silent about closure is validated as closed. Four clauses
 * decide where and how, because a schema that *composes* constraints cannot be closed
 * the same way as one that declares them in a single place:
 *
 * 1. Closure is never injected inside a fragment subtree
 *    (`allOf`/`if`/`then`/`else`/`not`/`dependentSchemas`). A fragment contributes part
 *    of an instance's constraints, so closing it would reject keys a sibling fragment
 *    declares; closing an `if` matcher would silently stop the conditional from firing.
 * 2. A definition closes on its own terms *unless every path to it runs through a
 *    fragment*. A definition reached only from fragment context is itself acting as a
 *    fragment — the classic `allOf: [{$ref: Base}, {properties: {...}}]` extension
 *    idiom — so closing it lexically would reject the keys its sibling branch declares.
 *    Such a definition is left open and the composition root closes over it instead,
 *    which annotations make correct. A definition also reached from non-fragment
 *    context still closes, since something must enforce it there.
 * 3. A node declares properties if it carries `properties`, or if a fragment applicator
 *    under it does, following local `$ref` targets. `not` is excluded — the properties
 *    under it are prohibitions, not declarations, and it contributes no annotations, so
 *    counting them would close the schema to nothing.
 * 4. Such a node is closed with `unevaluatedProperties: false` when it carries a
 *    fragment applicator, and `additionalProperties: false` otherwise.
 *
 * An explicit `additionalProperties` or `unevaluatedProperties` always wins, and object
 * schemas that declare no properties anywhere (free-form mappings) are unaffected. An
 * object declared inline *inside* a fragment is never closed; declare it in `$defs` and
 * `$ref` it to restore strictness. Validation-time only; never changes compiled
 * schemas. Mirrors the Python `apply_enforced_extras` exactly.
 */
export function applyEnforcedExtras(schema: Record<string, Json>): Record<string, Json> {
  const openDefinitions = composedOnlyDefinitions(schema);
  const definitions = localDefinitions(schema);
  return applyEnforced(schema, false, openDefinitions, definitions, "") as Record<string, Json>;
}

/** Map `#/$defs/Name` pointers to their subschemas, for local `$ref` following. */
function localDefinitions(schema: Record<string, Json>): Record<string, Json> {
  const definitions: Record<string, Json> = {};
  for (const keyword of DEFINITION_KEYWORDS) {
    const entries = schema[keyword];
    if (isMapping(entries)) {
      for (const [name, sub] of Object.entries(entries)) {
        definitions[`#/${keyword}/${name}`] = sub;
      }
    }
  }
  return definitions;
}

/**
 * Definitions every reference to which is *composed* rather than standalone.
 *
 * A reference is composed when the referring node contributes constraints of its own
 * alongside it — it declares sibling `properties`, carries a fragment applicator, or
 * sits inside a fragment. In every such case the referring node (or its composition
 * root) is itself closed with annotation-aware `unevaluatedProperties`, which already
 * covers the definition's keys; closing the definition lexically as well would reject
 * whatever the siblings declare.
 *
 * A standalone reference — a bare `{"$ref": ...}` in non-fragment position, such as a
 * property value — has nothing else covering that instance location, so the definition
 * must close on its own terms. One standalone reference is enough to keep it closed.
 *
 * A definition with no references at all is not included: nothing applies it, so closing
 * it is harmless and keeps the common case unchanged.
 */
function composedOnlyDefinitions(schema: Record<string, Json>): Set<string> {
  const contexts = new Map<string, { composed: boolean; standalone: boolean }>();
  collectRefContexts(schema, false, contexts);
  const composedOnly = new Set<string>();
  for (const [pointer, seen] of contexts) {
    if (seen.composed && !seen.standalone) composedOnly.add(pointer);
  }
  return composedOnly;
}

function isComposedReference(node: Record<string, Json>, inFragment: boolean): boolean {
  if (inFragment) return true;
  if (isMapping(node.properties)) return true;
  return Object.keys(node).some((key) => FRAGMENT_APPLICATORS.has(key));
}

function collectRefContexts(
  node: Json,
  inFragment: boolean,
  contexts: Map<string, { composed: boolean; standalone: boolean }>,
): void {
  if (Array.isArray(node)) {
    for (const item of node) collectRefContexts(item, inFragment, contexts);
    return;
  }
  if (!isMapping(node)) return;
  for (const keyword of REFERENCE_KEYWORDS) {
    const ref = node[keyword];
    if (typeof ref !== "string") continue;
    const seen = contexts.get(ref) ?? { composed: false, standalone: false };
    if (isComposedReference(node, inFragment)) seen.composed = true;
    else seen.standalone = true;
    contexts.set(ref, seen);
  }
  for (const [key, value] of Object.entries(node)) {
    // A definition body is reached by reference, so its own lexical position says
    // nothing about the context its references are used in; start it fresh.
    const childFragment =
      (DEFINITION_KEYWORDS.has(key) ? false : inFragment) || FRAGMENT_APPLICATORS.has(key);
    if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
      for (const sub of Object.values(value)) collectRefContexts(sub, childFragment, contexts);
    } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
      collectRefContexts(value, childFragment, contexts);
    } else if (SCHEMA_KEYWORDS.has(key)) {
      collectRefContexts(value, childFragment, contexts);
    }
  }
}

function applyEnforced(
  node: Json,
  inFragment: boolean,
  openDefs: Set<string>,
  definitions: Record<string, Json>,
  pointer: string,
): Json {
  if (!isMapping(node)) {
    return node;
  }

  const out: Record<string, Json> = {};
  for (const [key, value] of Object.entries(node)) {
    // A definition is a complete declaration, so it closes even inside a fragment —
    // unless clause 2 says otherwise, which the pointer check below decides.
    const childFragment =
      (DEFINITION_KEYWORDS.has(key) ? false : inFragment) || FRAGMENT_APPLICATORS.has(key);
    const recurse = (sub: Json, childPointer: string) =>
      applyEnforced(sub, childFragment, openDefs, definitions, childPointer);
    if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
      const mapped: Record<string, Json> = {};
      for (const [name, sub] of Object.entries(value)) {
        mapped[name] = recurse(sub, DEFINITION_KEYWORDS.has(key) ? `#/${key}/${name}` : "");
      }
      out[key] = mapped;
    } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
      out[key] = value.map((item) => recurse(item, ""));
    } else if (SCHEMA_KEYWORDS.has(key)) {
      out[key] = recurse(value, "");
    } else {
      out[key] = value;
    }
  }

  if (inFragment || openDefs.has(pointer)) return out;
  if ("additionalProperties" in out || "unevaluatedProperties" in out) return out;
  const hasFragment = Object.keys(out).some((key) => FRAGMENT_APPLICATORS.has(key));
  const hasReference = Object.keys(out).some((key) => REFERENCE_KEYWORDS.has(key));
  if (isMapping(out.properties)) {
    const needsAnnotations = hasFragment || hasReference;
    out[needsAnnotations ? "unevaluatedProperties" : "additionalProperties"] = false;
  } else if (hasFragment && fragmentDeclaresProperties(out, definitions, new Set())) {
    out.unevaluatedProperties = false;
  }
  return out;
}

/**
 * Fragment applicators that *declare* what an instance may contain. `not` is a
 * prohibition: the properties under it name what must be absent, and it contributes no
 * annotations, so treating them as declarations would close the schema to nothing.
 */
const DECLARING_FRAGMENTS = new Set(
  [...FRAGMENT_APPLICATORS].filter((keyword) => keyword !== "not"),
);

function fragmentDeclaresProperties(
  node: Record<string, Json>,
  definitions: Record<string, Json>,
  seen: Set<string>,
): boolean {
  return Object.entries(node).some(
    ([key, value]) => DECLARING_FRAGMENTS.has(key) && declaresProperties(value, definitions, seen),
  );
}

function declaresProperties(
  node: Json,
  definitions: Record<string, Json>,
  seen: Set<string>,
): boolean {
  if (Array.isArray(node)) return node.some((item) => declaresProperties(item, definitions, seen));
  if (!isMapping(node)) return false;
  if (isMapping(node.properties)) return true;
  // Follow a local `$ref`: a fragment that carries only a reference still contributes
  // the target's properties to the composition root. Resolving it (rather than assuming
  // any `$ref` declares something) keeps a reference to a free-form mapping from closing
  // the root against every key.
  const ref = node.$ref;
  if (typeof ref === "string" && ref in definitions && !seen.has(ref)) {
    if (declaresProperties(definitions[ref] as Json, definitions, new Set([...seen, ref]))) {
      return true;
    }
  }
  return fragmentDeclaresProperties(node, definitions, seen);
}
