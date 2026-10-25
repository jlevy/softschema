/**
 * Compile a Zod schema to a canonical JSON Schema YAML file, mirroring the Python
 * `compile_model`. The schema_sha256 is computed over the canonical JSON (not the YAML
 * text), so it is the language-neutral fingerprint used for cross-implementation parity.
 *
 * Compiled schema *files* are content-identical across languages, not byte-identical: the YAML
 * writers differ in serialization style (indentation, quoting), so `--check` drift
 * compares parsed canonical content, and the schema_sha256 over the canonical JSON is
 * the cross-language fingerprint, independent of YAML formatting.
 */
import { existsSync } from "node:fs";
import { writeFileSync } from "atomically";
import { stringify as yamlStringify } from "yaml";
import { z } from "zod";
import {
  canonicalizeJsonSchema,
  NAME_MAP_KEYWORDS,
  SCHEMA_KEYWORDS,
  SCHEMA_LIST_KEYWORDS,
} from "./canonicalize.js";
import { isMapping } from "./guards.js";
import { checkRootId } from "./identity.js";
import { checkContractId } from "./models.js";
import { parsePortableYaml, readUtf8 } from "./portable.js";
import { canonicalJson, schemaSha256 } from "./settings.js";

export const JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema";

export interface CompileResult {
  outPath: string;
  schemaYaml: string;
  drift: boolean;
  driftDiff: string | null;
  schemaSha256: string;
}

export interface CompileOptions {
  contractId: string;
  schemaId?: string;
  checkOnly?: boolean;
}

function augmentSchema(
  schema: Record<string, unknown>,
  contractId: string,
  schemaId: string | undefined,
): Record<string, unknown> {
  if ("x-softschema" in schema || "$id" in schema) {
    throw new Error("model schema uses a compiler-reserved root identity key");
  }
  const out: Record<string, unknown> = { ...schema };
  out.$schema ??= JSON_SCHEMA_DRAFT;
  if (schemaId !== undefined) out.$id = schemaId;
  // Language-neutral: no `generated_from` provenance (would leak the implementation).
  out["x-softschema"] = {
    contract: contractId,
  };
  return out;
}

function addGeneratedTitles(schema: Record<string, unknown>, contractId: string): void {
  if (schema.title === undefined) {
    const qualified = contractId.split(":").at(-1) ?? contractId;
    schema.title = qualified.split("/")[0];
  }
  const stack = [schema];
  while (stack.length > 0) {
    const node = stack.pop() as Record<string, unknown>;
    for (const keyword of ["properties", "$defs", "definitions"] as const) {
      const named = node[keyword];
      if (!isMapping(named)) continue;
      for (const [name, child] of Object.entries(named)) {
        if (!isMapping(child)) continue;
        const referencesDefinition =
          typeof child.$ref === "string" ||
          (Array.isArray(child.anyOf) &&
            child.anyOf.some((branch) => isMapping(branch) && "$ref" in branch));
        if (!referencesDefinition)
          child.title ??= keyword === "properties" ? fieldTitle(name) : name;
        stack.push(child);
      }
    }
    for (const keyword of ["allOf", "anyOf", "oneOf", "prefixItems"] as const) {
      const children = node[keyword];
      if (Array.isArray(children)) stack.push(...children.filter(isMapping));
    }
    for (const keyword of ["items", "additionalProperties", "contains"] as const) {
      const child = node[keyword];
      if (isMapping(child)) stack.push(child);
    }
  }
}

/**
 * Visit every subschema of a raw JSON Schema, parents before children. Only subschema
 * positions are walked; `default`, `examples`, `const`, and `enum` values are data and are
 * never visited.
 */
function visitSubschemas(
  schema: Record<string, unknown>,
  visit: (node: Record<string, unknown>) => void,
): void {
  const stack: unknown[] = [schema];
  while (stack.length > 0) {
    const node = stack.pop();
    if (!isMapping(node)) continue;
    visit(node);
    for (const [key, value] of Object.entries(node)) {
      if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) stack.push(...Object.values(value));
      else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) stack.push(...value);
      else if (SCHEMA_KEYWORDS.has(key)) stack.push(value);
    }
  }
}

/**
 * Undo Zod's rewrite of a union of bare type branches into a `type` array.
 *
 * Since 4.5, `z.toJSONSchema` turns `anyOf: [{ type: "string" }, { type: "null" }]` (what
 * `.nullable()` and a union of plain primitives emit) into `type: ["string", "null"]`.
 * The two forms validate identically, but Pydantic emits the `anyOf` form and the shared
 * canonical profile does not reconcile them, so the rewrite alone changed the canonical
 * content and schema_sha256 of every model with a nullable field. That rewrite is the only
 * place Zod produces a `type` array, so expanding each one back into bare `anyOf` branches,
 * in order, restores the form both compilers emit.
 */
function expandTypeArray(node: Record<string, unknown>): void {
  if (Array.isArray(node.type) && node.anyOf === undefined) {
    node.anyOf = node.type.map((type) => ({ type }));
    delete node.type;
  }
}

/**
 * Rewrite a Zod 4.6 tuple into the form Pydantic's `tuple[...]` emits. Each rewrite
 * changes no verdict.
 *
 * `z.tuple([z.string(), z.int()])` emits `prefixItems`, `items: false`, `minItems: 2`, and
 * `maxItems: 2`; Pydantic's `tuple[str, int]` emits the same without `items: false`. With
 * `maxItems` at most the number of `prefixItems`, no array that satisfies `maxItems` has an
 * element `items` would apply to, so `items: false` is dropped. A rest tuple (`items` is a
 * schema) keeps it.
 *
 * An empty tuple also emits `prefixItems: []`, which constrains nothing and which Pydantic
 * omits: `z.tuple([])` then matches `tuple[()]`, which also spells out `minItems: 0`, and
 * `z.tuple([], z.int())` matches `tuple[int, ...]`.
 */
function normalizeTuple(node: Record<string, unknown>): void {
  if (!Array.isArray(node.prefixItems)) return;
  if (
    node.items === false &&
    typeof node.maxItems === "number" &&
    node.maxItems <= node.prefixItems.length
  ) {
    delete node.items;
  }
  if (node.prefixItems.length === 0) {
    delete node.prefixItems;
    if (node.maxItems === 0) node.minItems ??= 0;
  }
}

/**
 * Drop `type: "string"` from a record's key schema, which Pydantic never emits there.
 *
 * Every JSON object key is a string, so the keyword is always satisfied. The shared
 * canonical profile drops a key schema that is only `{type: "string"}`; this drops the
 * keyword beside other key constraints. Then `z.record(z.enum(["a", "b"]), V)` emits
 * `propertyNames: {enum: ["a", "b"]}` as Pydantic's `dict[Literal["a", "b"], V]` does,
 * and a constrained key such as `z.string().min(2)` matches
 * `dict[Annotated[str, Field(min_length=2)], V]`.
 */
function dropStringKeyType(node: Record<string, unknown>): void {
  const keys = node.propertyNames;
  if (isMapping(keys) && keys.type === "string" && Object.keys(keys).length > 1) {
    delete keys.type;
  }
}

/**
 * Whether an object field or record value fills an absent key through `.catch()`,
 * possibly behind a `z.preprocess()` transform, which is how Zod 4.6 resolves input
 * optionality.
 *
 * Zod's runtime accepts the missing key and substitutes the catch value. An object
 * field's Pydantic mirror is a defaulted field, which is not required, and a Pydantic
 * `dict` never requires its keys. Zod 4.6 still requires the key because the inner type
 * is required. A tuple element is left alone: Pydantic cannot default one, and its
 * `tuple[...]` counts every element toward `minItems`, as Zod 4.6 does.
 */
function catchesAbsentKey(field: z.core.$ZodType | undefined): boolean {
  if (field instanceof z.core.$ZodPipe && field._zod.def.in instanceof z.core.$ZodTransform) {
    return catchesAbsentKey(field._zod.def.out);
  }
  return field instanceof z.core.$ZodCatch;
}

/**
 * The JSON form of a default value, as Zod writes a `.default()` value: a `Date` becomes
 * its ISO string. Throws for what canonical JSON cannot carry, as the Python compiler
 * does. Zod's final JSON copy of the schema would otherwise turn NaN or ±Infinity into
 * `null` and fail on a BigInt with an error that names no field.
 */
function jsonDefault(value: unknown, what: string): unknown {
  const serialized = JSON.stringify(value, (_key, item: unknown) => {
    if (typeof item === "number" && !Number.isFinite(item)) {
      throw new TypeError(`canonical JSON requires finite numbers; ${what} is ${item}`);
    }
    if (typeof item === "bigint") {
      throw new TypeError(`canonical JSON cannot represent a BigInt; ${what} is ${item}n`);
    }
    return item;
  });
  return serialized === undefined ? undefined : JSON.parse(serialized);
}

/**
 * Holds the `default` and `examples` a `$ref` node writes until `$defs` is complete. Never
 * emitted: `settleRefAnnotations` removes it from every node.
 */
const REF_ANNOTATIONS = "\u0000softschema:ref-annotations";

/** Whether two JSON values are equal as Zod compares them when it deduplicates a key. */
function sameJson(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

/**
 * Settle the `default` and `examples` of a node that references a `$defs` entry, as Zod
 * settles them without a transform: it leaves a key out of such a node when the entry
 * carries the same value, and otherwise the node's own value wins. So `X.describe("d")`
 * compiles to a bare `$ref` whether or not `X` transforms.
 */
function settleRefAnnotations(node: Record<string, unknown>, defs: unknown): void {
  const own = node[REF_ANNOTATIONS];
  if (!isMapping(own)) return;
  delete node[REF_ANNOTATIONS];
  const name =
    typeof node.$ref === "string" && node.$ref.startsWith("#/$defs/")
      ? node.$ref.slice("#/$defs/".length).replaceAll("~1", "/").replaceAll("~0", "~")
      : undefined;
  const entry = isMapping(defs) && name !== undefined ? defs[name] : undefined;
  if (isMapping(entry)) settleRefAnnotations(entry, defs);
  for (const [key, value] of Object.entries(own)) {
    if (isMapping(entry) && key in entry && sameJson(entry[key], value)) delete node[key];
    else node[key] = value;
  }
}

/**
 * Zod's names for its `.startsWith()`, `.endsWith()`, and `.includes()` string checks.
 *
 * Since 4.6, `z.toJSONSchema` writes the name of a string schema's last format-like check
 * as `format`, and these three now count. They are constraints, not formats: `pattern`
 * already carries each one, no JSON Schema vocabulary or Pydantic `Field(pattern=...)`
 * mirror emits them, and the name replaces a real format written by an earlier check, as
 * in `z.email().startsWith("a")`. Only a format Zod generated is corrected: an authored
 * `.meta({ format })` is kept whatever its name.
 */
const AFFIX_CHECK_FORMATS = new Set(["starts_with", "ends_with", "includes"]);

function isAffixCheck(check: z.core.$ZodCheck<never>): boolean {
  const def = check._zod.def as Partial<z.core.$ZodCheckStringFormatDef>;
  return def.check === "string_format" && AFFIX_CHECK_FORMATS.has(def.format ?? "");
}

/**
 * The `format` Zod emits for `source` without its affix checks, which is the format Zod
 * 4.4 emitted for the whole schema. Zod derives it from the remaining checks itself, so its
 * own spelling rules still apply (`z.url()` is `uri`, `.regex()` sets none).
 */
function formatWithoutAffixChecks(source: z.core.$ZodType): string | undefined {
  const def = source._zod.def;
  const withoutAffixes = z.core.util.clone(source, {
    ...def,
    checks: (def.checks ?? []).filter((check) => !isAffixCheck(check)),
  });
  return z.toJSONSchema(withoutAffixes, { target: "draft-2020-12", io: "input" }).format;
}

function fieldTitle(name: string): string {
  return name
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/gu, (letter) => letter.toUpperCase());
}

function renderYaml(schema: Record<string, unknown>): string {
  return yamlStringify(schema, { sortMapEntries: true, lineWidth: 0 });
}

/**
 * Build the canonical schema object (with schema_sha256 set), without serializing or
 * writing. Exposed so conformance tests can compare the content directly to the
 * committed reference, independent of YAML formatting.
 */
export function buildCanonicalSchema(
  zodSchema: z.ZodType,
  contractId: string,
  schemaId?: string,
): { schema: Record<string, unknown>; sha: string } {
  checkContractId(contractId);
  // The id becomes the root `$id`; refuse one validation would refuse.
  if (schemaId !== undefined) checkRootId(schemaId);
  const raw = z.toJSONSchema(zodSchema, {
    target: "draft-2020-12",
    io: "input",
    // Only id-registered named objects (Address, Event) belong in $defs; primitives stay
    // inline. "inline" extracts by id, not by repetition, matching Pydantic's $defs shape.
    reused: "inline",
    unrepresentable: "throw",
    // Zod-specific output must not leak into the canonical cross-language sidecar. Zod's
    // overrides run on a wrapped schema before its wrapper copies the result, so fixing
    // the node that carries the checks fixes every copy.
    override: ({ zodSchema: source, jsonSchema, path }) => {
      if (
        typeof jsonSchema.format === "string" &&
        AFFIX_CHECK_FORMATS.has(jsonSchema.format) &&
        (source._zod.def.checks ?? []).some(isAffixCheck) &&
        // Metadata is applied after the processor, so an authored format is what was emitted.
        z.globalRegistry.get(source)?.format === undefined
      ) {
        const format = formatWithoutAffixChecks(source);
        if (format === undefined) delete jsonSchema.format;
        else jsonSchema.format = format;
      }
      if (source instanceof z.core.$ZodObject && Array.isArray(jsonSchema.required)) {
        const shape = source._zod.def.shape;
        const required = jsonSchema.required.filter((key) => !catchesAbsentKey(shape[key]));
        if (required.length > 0) jsonSchema.required = required;
        else delete jsonSchema.required;
      }
      if (source instanceof z.core.$ZodRecord && catchesAbsentKey(source._zod.def.valueType)) {
        delete jsonSchema.required;
      }
      // A default the canonical sidecar cannot carry fails here, as it does in Python. By
      // now Zod has already turned a `.default()` NaN into `null`, so check the source value.
      const at = `#/${path.join("/")}`;
      let fillValue: unknown;
      if (source instanceof z.core.$ZodDefault) {
        fillValue = jsonDefault(source._zod.def.defaultValue, `the .default() value at ${at}`);
      } else if (source instanceof z.core.$ZodPrefault) {
        jsonDefault(source._zod.def.defaultValue, `the .prefault() value at ${at}`);
      } else if (source instanceof z.core.$ZodCatch) {
        fillValue = jsonDefault(
          source._zod.def.catchValue(undefined as never),
          `the .catch() value at ${at}`,
        );
      }
      // The node's own `default` and `examples`, as Zod writes them: an authored `.meta()`
      // value, else the value of its `.default()` or `.catch()`.
      const meta = z.globalRegistry.get(source);
      const own: Record<string, unknown> = {};
      if (meta?.default !== undefined) {
        own.default = jsonDefault(meta.default, `the default at ${at}`);
      } else if (fillValue !== undefined) {
        own.default = fillValue;
      }
      if (meta?.examples !== undefined) own.examples = meta.examples;
      // In input mode Zod drops both keys from a schema that transforms: a `.default()` over
      // `.transform()` or `z.preprocess()` (zod 4.4 and 4.6), a catch value (since zod 4.6),
      // and an authored `default` or `examples`. The Pydantic mirror, a field with an
      // `AfterValidator` or `BeforeValidator` and the same `default` or `Field(examples=...)`,
      // keeps them, so put them back. A value the node inherits from a transforming inner
      // type gives way to its own, as without a transform. Zod also leaves a key out of a
      // `$ref` node whose `$defs` entry carries the same value, which only the finished
      // `$defs` shows, so such a node settles there.
      if ("$ref" in jsonSchema) {
        if (Object.keys(own).length > 0) jsonSchema[REF_ANNOTATIONS] = own;
      } else {
        for (const [key, value] of Object.entries(own)) {
          if (!sameJson(jsonSchema[key], value)) jsonSchema[key] = value;
        }
      }
      if ("default" in jsonSchema) jsonDefault(jsonSchema.default, `the default at ${at}`);
      // Pydantic temporal fields emit a format annotation without a pattern. Zod ISO nodes
      // validate semantically with an intrinsic regex; drop it and keep the format.
      if (
        source instanceof z.ZodISODate ||
        source instanceof z.ZodISODateTime ||
        source instanceof z.ZodISODuration ||
        source instanceof z.ZodISOTime
      ) {
        const format =
          source instanceof z.ZodISODate
            ? "date"
            : source instanceof z.ZodISODateTime
              ? "date-time"
              : source instanceof z.ZodISODuration
                ? "duration"
                : "time";
        const intrinsicPattern = source.def.pattern?.source;
        jsonSchema.format = format;
        if (intrinsicPattern !== undefined && jsonSchema.pattern === intrinsicPattern) {
          delete jsonSchema.pattern;
        }
        if (intrinsicPattern !== undefined && Array.isArray(jsonSchema.allOf)) {
          const authoredAssertions = jsonSchema.allOf.filter(
            (entry) => !isMapping(entry) || entry.pattern !== intrinsicPattern,
          );
          if (authoredAssertions.length > 0) jsonSchema.allOf = authoredAssertions;
          else delete jsonSchema.allOf;
        }
      }
    },
  }) as Record<string, unknown>;
  visitSubschemas(raw, (node) => {
    settleRefAnnotations(node, raw.$defs);
    expandTypeArray(node);
    normalizeTuple(node);
    dropStringKeyType(node);
  });
  addGeneratedTitles(raw, contractId);
  const schema = canonicalizeJsonSchema(augmentSchema(raw, contractId, schemaId));
  const sha = schemaSha256(schema);
  (schema["x-softschema"] as Record<string, unknown>).schema_sha256 = sha;
  return { schema, sha };
}

export function compileSchema(
  zodSchema: z.ZodType,
  outPath: string,
  options: CompileOptions,
): CompileResult {
  const { schema, sha } = buildCanonicalSchema(zodSchema, options.contractId, options.schemaId);
  const rendered = renderYaml(schema);

  if (options.checkOnly) {
    if (!existsSync(outPath)) {
      return {
        outPath,
        schemaYaml: rendered,
        drift: true,
        driftDiff: `missing committed compiled schema at ${outPath}`,
        schemaSha256: sha,
      };
    }
    // Compare parsed content, not raw bytes, so YAML formatting (a different writer than
    // Python's) is not treated as drift; only a genuine schema change is.
    const existing = parsePortableYaml(readUtf8(outPath));
    const drift = canonicalJson(existing) !== canonicalJson(schema);
    return {
      outPath,
      schemaYaml: rendered,
      drift,
      driftDiff: drift ? `committed schema at ${outPath} differs from compile output` : null,
      schemaSha256: sha,
    };
  }

  writeFileSync(outPath, rendered, { encoding: "utf8" });
  return { outPath, schemaYaml: rendered, drift: false, driftDiff: null, schemaSha256: sha };
}
