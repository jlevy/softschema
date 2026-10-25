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
import { Document, Scalar, visit } from "yaml";
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
import {
  checkPortableText,
  escapeNonPortableCharacters,
  findNonPortableCharacter,
  PortableInputError,
  readYamlFile,
} from "./portable.js";
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

/**
 * Render the canonical schema as YAML the portable reader accepts.
 *
 * A string carrying a character the reader rejects raw (U+0085, U+2028, U+2029, a C1
 * control) is forced into double-quoted style and the character is written as the escape
 * both engines decode (`\N`, `\L`, `\P`, `\x85`). The `yaml` package would otherwise
 * emit it raw in a plain or double-quoted scalar, and the sidecar it just wrote would fail
 * every later read as `schema_invalid`. Keys are scalars too, so a property name is
 * covered the same way; once every such string is double-quoted, every raw occurrence
 * left in the text sits inside a double-quoted scalar, where the textual escape is exact.
 *
 * Two more strings take the double-quoted path because the `yaml` package writes them as
 * plain scalars that ruamel refuses: one holding a tab (ruamel reads a raw tab in a plain
 * scalar as a scanner error) and the string `=` (the YAML 1.1 `!!value` key). The Python
 * writer quotes both on its own.
 */
export function renderYaml(schema: Record<string, unknown>): string {
  const document = new Document(schema, { sortMapEntries: true });
  visit(document, {
    Scalar(_key, node) {
      if (
        typeof node.value === "string" &&
        (findNonPortableCharacter(node.value) !== null ||
          node.value.includes("\t") ||
          node.value === "=")
      ) {
        node.type = Scalar.QUOTE_DOUBLE;
      }
    },
  });
  const rendered = escapeNonPortableCharacters(document.toString({ lineWidth: 0 }));
  // The writer's output must pass the reader's preflight: a gap here fails once, at write
  // time, rather than on every later read of the schema.
  try {
    checkPortableText(rendered);
  } catch (error) {
    if (error instanceof PortableInputError) {
      throw new Error(`compile produced YAML the portable reader rejects: ${error.message}`);
    }
    throw error;
  }
  return rendered;
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
      if (source instanceof z.core.$ZodDefault) {
        jsonDefault(source._zod.def.defaultValue, `the .default() value at ${at}`);
      } else if (source instanceof z.core.$ZodPrefault) {
        jsonDefault(source._zod.def.defaultValue, `the .prefault() value at ${at}`);
      } else if (source instanceof z.core.$ZodCatch) {
        const catchValue = jsonDefault(
          source._zod.def.catchValue(undefined as never),
          `the .catch() value at ${at}`,
        );
        // Zod 4.6 drops the `default` of a transforming schema in input mode, the catch
        // value included. Zod 4.4 kept it, and so does the Pydantic mirror, a defaulted field
        // with an `AfterValidator`, so put it back.
        if (!("default" in jsonSchema) && catchValue !== undefined) {
          jsonSchema.default = catchValue;
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
    // Python's) is not treated as drift; only a genuine schema change is. A committed file
    // the portable reader refuses (not UTF-8, a raw character the preflight rejects) is
    // drift too: `--check` asks whether the committed output still stands, and it does not.
    let existing: unknown;
    try {
      existing = readYamlFile(outPath);
    } catch (error) {
      if (!(error instanceof PortableInputError)) throw error;
      // The message names the file once, whichever step refused it.
      return {
        outPath,
        schemaYaml: rendered,
        drift: true,
        driftDiff: `committed compiled schema is not portable YAML: ${error.message}`,
        schemaSha256: sha,
      };
    }
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
