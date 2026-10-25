import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as yamlParse } from "yaml";
import { z } from "zod";
import { buildCanonicalSchema, compileSchema } from "./compile.js";
import {
  collapseUndeclaredProperties,
  normalizeAjvError,
  renderStructuralMessage,
  structuralErrorRecord,
} from "./errors.js";
import {
  type Contract,
  checkContractId,
  contractToOutput,
  isSchemaStatus,
  metadataToOutput,
  parseSchemaMetadata,
  SchemaMetadataError,
} from "./models.js";
import { validateArtifact } from "./validate.js";

const HARDENING_VECTORS = join(import.meta.dir, "../../../tests/vectors/hardening.yaml");

function tmp(name: string, content: string): string {
  const dir = mkdtempSync(join(tmpdir(), "softschema-unit-"));
  const path = join(dir, name);
  writeFileSync(path, content);
  return path;
}

function contract(o: Partial<Contract> = {}): Contract {
  return {
    id: "x:S/v1",
    model: null,
    envelopeKey: null,
    status: "soft",
    profile: "frontmatter-md",
    schemaPath: null,
    ...o,
  };
}

describe("models", () => {
  test("parseSchemaMetadata shapes", () => {
    expect(parseSchemaMetadata(null)).toBeNull();
    expect(parseSchemaMetadata("a:B/v1")).toEqual({
      contractId: "a:B/v1",
      schema: null,
      envelope: null,
      status: null,
    });
    expect(
      parseSchemaMetadata({
        contract: "a:B/v1",
        schema: "a.schema.yaml",
        envelope: "data",
        status: "enforced",
      }),
    ).toEqual({
      contractId: "a:B/v1",
      schema: "a.schema.yaml",
      envelope: "data",
      status: "enforced",
    });
    expect(() => parseSchemaMetadata({ status: "enforced" })).toThrow(SchemaMetadataError);
    expect(() => parseSchemaMetadata({ contract: "a", status: "nope" })).toThrow(
      SchemaMetadataError,
    );
    expect(() => parseSchemaMetadata({ contract: "a", schema: "" })).toThrow(SchemaMetadataError);
    expect(() => parseSchemaMetadata({ contract: "a", schema: 7 })).toThrow(SchemaMetadataError);
    expect(() => parseSchemaMetadata({ contract: "a", envelope: "" })).toThrow(SchemaMetadataError);
    expect(() => parseSchemaMetadata(42)).toThrow(SchemaMetadataError);
  });
  test("contract-ID grammar: accepts valid ids (compact and expanded)", () => {
    for (const id of [
      "Name",
      "ns:Name",
      "ns:Name/v1",
      "ns_x:Na_me",
      "a.b.c:Name",
      "name",
      "com.acme.docs:IncidentReview/1.0",
    ]) {
      const expected = { contractId: id, schema: null, envelope: null, status: null };
      expect(parseSchemaMetadata(id)).toEqual(expected);
      expect(parseSchemaMetadata({ contract: id })).toEqual(expected);
    }
  });
  test("contract-ID grammar: rejects malformed ids", () => {
    for (const id of [
      " ",
      "bad id",
      "a : B",
      ":Name",
      "a::B",
      "Name/v1/v2",
      "Name/",
      "ns:",
      "My.Name",
    ]) {
      expect(() => parseSchemaMetadata(id)).toThrow(SchemaMetadataError);
      expect(() => parseSchemaMetadata({ contract: id })).toThrow(SchemaMetadataError);
    }
  });
  test("shared contract identity vectors", () => {
    const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
      string,
      Array<Record<string, unknown>>
    >;
    for (const item of vectors.identity ?? []) {
      if (item.valid) expect(checkContractId(item.contract)).toBe(item.contract as string);
      else expect(() => checkContractId(item.contract)).toThrow(SchemaMetadataError);
    }
  });
  test("status guard + output helpers", () => {
    expect(isSchemaStatus("enforced")).toBe(true);
    expect(isSchemaStatus("x")).toBe(false);
    expect(metadataToOutput(null)).toBeNull();
    expect(
      metadataToOutput({ contractId: "a", schema: null, envelope: null, status: null }),
    ).toEqual({
      contract: "a",
      envelope: null,
      schema: null,
      status: null,
    });
    expect(contractToOutput(contract({ envelopeKey: "movie", schemaPath: "s.yaml" }))).toEqual({
      envelope_key: "movie",
      id: "x:S/v1",
      model: null,
      profile: "frontmatter-md",
      schema_path: "s.yaml",
      status: "soft",
    });
  });
});

describe("errors: every message template", () => {
  const cases: [string, unknown, unknown, string][] = [
    ["enum", ["G", "PG"], "X", "value 'X' is not one of ['G', 'PG']"],
    ["type", "integer", "x", "value 'x' is not of type 'integer'"],
    ["required", "name", null, "required property 'name' is missing"],
    ["minimum", 1, 0, "value 0 is less than the minimum of 1"],
    ["maximum", 9, 10, "value 10 is greater than the maximum of 9"],
    ["exclusiveMinimum", 0, 0, "value 0 is not greater than 0"],
    ["exclusiveMaximum", 1, 1, "value 1 is not less than 1"],
    ["minItems", 1, [], "array is shorter than the minimum of 1 items"],
    ["maxItems", 2, [1, 2, 3], "array is longer than the maximum of 2 items"],
    ["minLength", 2, "a", "string is shorter than the minimum length of 2"],
    ["maxLength", 3, "abcd", "string is longer than the maximum length of 3"],
    ["pattern", "^a$", "b", "value 'b' does not match pattern '^a$'"],
    ["additionalProperties", false, {}, "object has properties that are not allowed"],
    ["multipleOf", 5, 7, "value 7 is not a multiple of 5"],
    ["weird", 1, 2, "value 2 failed weird constraint 1"],
  ];
  for (const [validator, vv, value, expected] of cases) {
    test(validator, () => expect(renderStructuralMessage(validator, vv, value)).toBe(expected));
  }
  test("pyRepr edge cases (bool/null/string-with-quote)", () => {
    expect(renderStructuralMessage("type", "boolean", true)).toBe(
      "value True is not of type 'boolean'",
    );
    expect(renderStructuralMessage("type", "null", null)).toBe("value None is not of type 'null'");
    expect(renderStructuralMessage("pattern", "x", "a'b")).toBe(
      "value \"a'b\" does not match pattern 'x'",
    );
  });
  test("pyRepr renders objects Python-dict style (regression for [object Object])", () => {
    // Python: repr({'x': 1}) == "{'x': 1}"; an object supplied where a string is expected.
    expect(renderStructuralMessage("type", "string", { x: 1 })).toBe(
      "value {'x': 1} is not of type 'string'",
    );
    // Object-valued enum members, and an object instance, both render byte-identically.
    expect(renderStructuralMessage("enum", [{ a: 1 }, { b: 2 }], { c: 3 })).toBe(
      "value {'c': 3} is not one of [{'a': 1}, {'b': 2}]",
    );
    // Nested objects/arrays recurse like Python repr.
    expect(renderStructuralMessage("type", "string", { a: { b: 2 }, c: [1, 2] })).toBe(
      "value {'a': {'b': 2}, 'c': [1, 2]} is not of type 'string'",
    );
  });
  test("pyRepr number formatting matches the canonical (Python repr) ground truth", () => {
    // Ground-truth table verified against CPython 3.11 repr(), with whole-valued
    // numbers in softschema's canonical form (no trailing `.0`, no exponent below
    // 1e21; ss-wbnm). Python's canonical_number converts whole floats < 1e21 to int,
    // which serializes the same as JS's native String()/JSON.stringify():
    //   1e-7      -> '1e-07'
    //   0.0001    -> '0.0001'
    //   0.00001   -> '1e-05'
    //   inf / nan / -inf
    //   1e15      -> '1000000000000000'        (whole-valued, plain integer)
    //   1e16      -> '10000000000000000'       (whole-valued < 1e21 → plain integer)
    //   1.5e16    -> '15000000000000000'
    //   1e20      -> '100000000000000000000'
    //   1e21      -> '1e+21'                    (>= 1e21 → exponential on both sides)
    const cases: [number, string][] = [
      [1e-7, "1e-07"],
      // ss-wbnm: a whole-valued number below 1e21 renders as a plain integer (no `.0`,
      // no exponent) on both engines. JS does it natively; Python's canonical_number
      // converts the float to int so the two agree. 1e16 was the reviewer's divergence
      // (Python used to emit '1e+16' while JS emits the full integer).
      [1e15, "1000000000000000"],
      [1e16, "10000000000000000"],
      [1.5e16, "15000000000000000"],
      [1e20, "100000000000000000000"],
      // 1e21 is the boundary: JS switches String() to exponential here, and Python's
      // float repr does too, so canonical_number leaves it a float and both emit '1e+21'.
      [1e21, "1e+21"],
      [0.0001, "0.0001"],
      [0.00001, "1e-05"],
      [Infinity, "inf"],
      [NaN, "nan"],
      [-1e-7, "-1e-07"],
      [-Infinity, "-inf"],
      // Integer-valued in the safe range: plain string
      [42, "42"],
      [0, "0"],
      [-3, "-3"],
      // Non-integer normal range: plain string
      [3.14, "3.14"],
      [0.5, "0.5"],
      [-0.3, "-0.3"],
    ];
    for (const [input, expected] of cases) {
      // pyRepr is private, so exercise it through renderStructuralMessage
      const msg = renderStructuralMessage("minimum", input, 0);
      const reprInMsg = msg.replace("value 0 is less than the minimum of ", "");
      expect(reprInMsg).toBe(expected);
    }
  });
  test("normalizeAjvError reads validator_value from error.schema and value from error.data", () => {
    const rec = normalizeAjvError({
      instancePath: "/release_year",
      keyword: "minimum",
      params: { limit: 1888 },
      schema: 1888,
      data: 1500,
    } as never);
    expect(rec).toEqual(
      structuralErrorRecord({
        path: ["release_year"],
        validator: "minimum",
        validatorValue: 1888,
        value: 1500,
      }),
    );
  });

  test("normalizeAjvError uses error.schema for multipleOf (not params.limit)", () => {
    // Regression for ss-f4sc: multipleOf lived in params.multipleOf, not params.limit,
    // so the old mapping produced validator_value undefined and "multiple of None".
    const rec = normalizeAjvError({
      instancePath: "/step",
      keyword: "multipleOf",
      params: { multipleOf: 5 },
      schema: 5,
      data: 7,
    } as never);
    expect(rec.validator_value).toBe(5);
    expect(rec.message).toBe("value 7 is not a multiple of 5");
  });

  test("normalizeAjvError preserves the missing property beside the required list", () => {
    const rec = normalizeAjvError({
      instancePath: "",
      keyword: "required",
      params: { missingProperty: "title" },
      schema: ["title", "year"],
      data: { year: 2000 },
    } as never);
    expect(rec.validator_value).toEqual(["title", "year"]);
    expect(rec.property).toBe("title");
    expect(rec.message).toBe("required property 'title' is missing");
  });

  test("normalizeAjvError distinguishes array indexes from numeric object keys", () => {
    const arrayRecord = normalizeAjvError(
      {
        instancePath: "/0/name",
        keyword: "type",
        params: { type: "string" },
        schema: "string",
        data: 42,
      } as never,
      [{ name: 42 }],
    );
    const objectRecord = normalizeAjvError(
      {
        instancePath: "/0/name",
        keyword: "type",
        params: { type: "string" },
        schema: "string",
        data: 42,
      } as never,
      { "0": { name: 42 } },
    );

    expect(arrayRecord.path).toEqual([0, "name"]);
    expect(objectRecord.path).toEqual(["0", "name"]);
  });

  test("collapseUndeclaredProperties deduplicates by object path and property", () => {
    const base = structuralErrorRecord({
      path: [],
      validator: "additionalProperties",
      validatorValue: false,
      value: { a: 1, b: 2 },
      property: "a",
    });
    expect(collapseUndeclaredProperties([base, { ...base }])).toEqual([base]);
    const other = { ...base, property: "b", message: "property 'b' is not allowed" };
    expect(collapseUndeclaredProperties([base, other])).toEqual([base, other]);
    const req = structuralErrorRecord({
      path: [],
      validator: "required",
      validatorValue: ["x"],
      value: {},
    });
    // required duplicates are preserved (jsonschema also emits one per missing key).
    expect(collapseUndeclaredProperties([req, { ...req }])).toHaveLength(2);
  });
});

describe("compile: write mode + build", () => {
  const Sample = z.strictObject({ name: z.string() });
  test("write mode produces a file and a hash", () => {
    const out = join(mkdtempSync(join(tmpdir(), "softschema-c-")), "s.yaml");
    const r = compileSchema(Sample, out, { contractId: "x:S/v1" });
    expect(r.drift).toBe(false);
    expect(r.schemaSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(readFileSync(out, "utf8")).toContain("x-softschema");
  });
  test("check mode reports missing committed compiled schema", () => {
    const result = compileSchema(Sample, join(tmpdir(), "does-not-exist-xyz.yaml"), {
      contractId: "x:S/v1",
      checkOnly: true,
    });
    expect(result.drift).toBe(true);
  });
  test("buildCanonicalSchema sets schema_sha256 inside x-softschema", () => {
    const { schema, sha } = buildCanonicalSchema(Sample, "x:S/v1");
    expect((schema["x-softschema"] as Record<string, unknown>).schema_sha256).toBe(sha);
  });
  test("normalizes ISO formats and preserves authored patterns", () => {
    const model = z.strictObject({
      day: z
        .string()
        .regex(/^[0-9]{4}$/)
        .meta({ format: "date" }),
      isoDay: z.iso.date().regex(/^2026-/),
      isoDuration: z.iso.duration().regex(/^P1/),
      isoTime: z.iso.time().regex(/^12:/),
    });
    const { schema } = buildCanonicalSchema(model, "x:PatternDate/v1");
    const properties = schema.properties as Record<string, Record<string, unknown>>;

    expect(properties.day?.format).toBe("date");
    expect(properties.day?.pattern).toBe("^[0-9]{4}$");
    expect(properties.isoDay?.format).toBe("date");
    expect(properties.isoDay?.allOf).toEqual([{ pattern: "^2026-" }]);
    expect(properties.isoDuration?.format).toBe("duration");
    expect(properties.isoDuration?.allOf).toEqual([{ pattern: "^P1" }]);
    expect(properties.isoTime?.format).toBe("time");
    expect(properties.isoTime?.allOf).toEqual([{ pattern: "^12:" }]);
  });
  test("emits nullable and primitive unions as anyOf branches, as Pydantic does", () => {
    const model = z.strictObject({
      nickname: z.string().nullable(),
      choice: z.union([z.string(), z.int()]),
      nested: z.array(z.strictObject({ note: z.string().nullable() })),
      shaped: z
        .string()
        .nullable()
        .default("n/a")
        .meta({ examples: [{ type: ["kept"] }] }),
    });
    const { schema } = buildCanonicalSchema(model, "x:Unions/v1");
    const properties = schema.properties as Record<string, Record<string, unknown>>;
    const nullableString = [{ type: "string" }, { type: "null" }];

    expect(properties.nickname?.anyOf).toEqual(nullableString);
    expect(properties.nickname?.type).toBeUndefined();
    expect(properties.choice?.anyOf).toEqual([{ type: "string" }, { type: "integer" }]);
    const item = (properties.nested?.items as Record<string, unknown>).properties as Record<
      string,
      Record<string, unknown>
    >;
    expect(item.note?.anyOf).toEqual(nullableString);
    expect(properties.shaped?.anyOf).toEqual(nullableString);
    // Annotation values are data, not subschemas: a `type` array inside one is untouched.
    expect(properties.shaped?.examples).toEqual([{ type: ["kept"] }]);
  });
  test("emits .startsWith(), .endsWith(), and .includes() as plain patterns, as Pydantic does", () => {
    const compile = (schema: z.ZodType) =>
      buildCanonicalSchema(z.strictObject({ f: schema }), "x:Affix/v1");
    const field = (schema: z.ZodType) =>
      (compile(schema).schema.properties as { f: Record<string, unknown> }).f;
    const sha = (schema: z.ZodType) => compile(schema).sha;

    // The same canonical content and digest as the `.regex()` spelling and a Pydantic
    // `Field(pattern=...)` mirror: Zod 4.6 adds `format: "starts_with"` and friends.
    expect(field(z.string().startsWith("ab"))).toEqual({
      pattern: "^ab.*",
      title: "F",
      type: "string",
    });
    expect(sha(z.string().startsWith("ab"))).toBe(sha(z.string().regex(/^ab.*/)));
    expect(field(z.string().endsWith("z"))).toEqual({
      pattern: ".*z$",
      title: "F",
      type: "string",
    });
    expect(field(z.string().includes("q"))).toEqual({ pattern: "q", title: "F", type: "string" });
    expect(field(z.string().startsWith("ab").endsWith("z"))).toEqual({
      allOf: [{ pattern: "^ab.*" }, { pattern: ".*z$" }],
      title: "F",
      type: "string",
    });

    // A real format written by an earlier check survives the affix check written over it.
    expect(field(z.email().startsWith("a")).format).toBe("email");
    expect(field(z.url().endsWith("/")).format).toBe("uri");
    expect(field(z.string().lowercase().includes("q")).format).toBe("lowercase");
    expect(field(z.stringFormat("sku", /^[A-Z]+$/).startsWith("A")).format).toBe("sku");
    expect(field(z.string().regex(/^a/).startsWith("ab")).format).toBeUndefined();
    expect(field(z.iso.date().startsWith("2"))).toEqual({
      allOf: [{ pattern: "^2.*" }],
      format: "date",
      title: "F",
      type: "string",
    });

    // Wrappers copy the corrected node.
    expect(field(z.string().startsWith("a").nullable().default(null))).toEqual({
      anyOf: [{ pattern: "^a.*", type: "string" }, { type: "null" }],
      default: null,
      title: "F",
    });
    expect(field(z.array(z.string().includes("q")).optional())).toEqual({
      items: { pattern: "q", type: "string" },
      title: "F",
      type: "array",
    });
    // Only a format Zod generated is corrected: an authored one survives even when it is
    // spelled like an affix check and sits on a string with one, before or after it.
    expect(field(z.string().meta({ format: "includes" })).format).toBe("includes");
    expect(field(z.string().startsWith("a").meta({ format: "includes" })).format).toBe("includes");
    expect(field(z.string().meta({ format: "ends_with" }).startsWith("a")).format).toBe(
      "ends_with",
    );
    expect(field(z.string().startsWith("a").meta({ format: "date" }).describe("d")).format).toBe(
      "date",
    );
  });
  test("pins Zod's JSON Schema output for constructs the parity fixture does not cover", () => {
    // Each of these changed schema_sha256 between zod 4.4 and 4.6. Pinning them makes the
    // next Zod upgrade show any further change here, instead of in a downstream drift check.
    const compiled = (schema: z.ZodType) => {
      const { schema: out } = buildCanonicalSchema(z.strictObject({ f: schema }), "x:Pin/v1");
      return {
        f: (out.properties as Record<string, unknown>).f,
        required: out.required,
      };
    };
    const field = (schema: z.ZodType) => compiled(schema).f;
    const A = z.strictObject({ a: z.string() });
    const B = z.strictObject({ b: z.int() });

    // Closed tuples: Pydantic's `tuple[str, int]` form (Zod's redundant `items: false` dropped).
    expect(field(z.tuple([z.string(), z.int()]))).toEqual({
      maxItems: 2,
      minItems: 2,
      prefixItems: [{ type: "string" }, { type: "integer" }],
      title: "F",
      type: "array",
    });
    expect(field(z.tuple([z.string(), z.int().optional()]))).toEqual({
      maxItems: 2,
      minItems: 1,
      prefixItems: [{ type: "string" }, { type: "integer" }],
      title: "F",
      type: "array",
    });
    // A rest tuple keeps its rest schema and gains the prefix as minItems.
    expect(field(z.tuple([z.string()], z.int()))).toEqual({
      items: { type: "integer" },
      minItems: 1,
      prefixItems: [{ type: "string" }],
      title: "F",
      type: "array",
    });
    // Empty tuples drop `prefixItems: []`: Pydantic's `tuple[()]` and `tuple[int, ...]`.
    expect(field(z.tuple([]))).toEqual({ maxItems: 0, minItems: 0, title: "F", type: "array" });
    // Zod's types require a prefix element beside a rest schema; its runtime does not.
    const emptyRest = (z.tuple as (items: z.ZodType[], rest: z.ZodType) => z.ZodType)([], z.int());
    expect(field(emptyRest)).toEqual(field(z.array(z.int())));
    expect(field(emptyRest)).toEqual({
      items: { type: "integer" },
      title: "F",
      type: "array",
    });
    // An empty array bound is not a tuple and keeps Pydantic's `list` form.
    expect(field(z.array(z.int()).max(0))).toEqual({
      items: { type: "integer" },
      maxItems: 0,
      title: "F",
      type: "array",
    });
    // Intersections of inline objects fold into the one object they describe, as a merged
    // Pydantic model would; an `allOf` of two closed objects validated nothing.
    const folded = {
      additionalProperties: false,
      properties: { a: { title: "A", type: "string" }, b: { title: "B", type: "integer" } },
      required: ["a", "b"],
      title: "F",
      type: "object",
    };
    expect(field(z.intersection(A, B))).toEqual(folded);
    expect(field(A.and(B))).toEqual(folded);
    // Numeric record keys are constrained as the strings JSON keys are. Pydantic's
    // `dict[int, V]` emits no key constraint; matching it would drop one Zod enforces.
    expect(field(z.record(z.number(), z.string()))).toEqual({
      additionalProperties: { type: "string" },
      propertyNames: { pattern: "^-?\\d+(?:\\.\\d+)?$" },
      title: "F",
      type: "object",
    });
    expect(field(z.record(z.int(), z.string()))).toEqual({
      additionalProperties: { type: "string" },
      propertyNames: { pattern: "^-?\\d+$" },
      title: "F",
      type: "object",
    });
    // A key schema carries no `type: "string"`: an enum-keyed record with optional values
    // is Pydantic's `dict[Literal["a", "b"], int]`, a literal key `dict[Literal["a"], int]`,
    // and a constrained key `dict[Annotated[str, Field(min_length=2)], int]`.
    expect(field(z.record(z.enum(["a", "b"]), z.int().optional()))).toEqual({
      additionalProperties: { type: "integer" },
      propertyNames: { enum: ["a", "b"] },
      title: "F",
      type: "object",
    });
    expect(field(z.record(z.literal("a"), z.int().optional()))).toEqual({
      additionalProperties: { type: "integer" },
      propertyNames: { const: "a" },
      title: "F",
      type: "object",
    });
    expect(field(z.record(z.string().min(2), z.int()))).toEqual({
      additionalProperties: { type: "integer" },
      propertyNames: { minLength: 2 },
      title: "F",
      type: "object",
    });
    // A plain string key keeps no key schema at all.
    expect(field(z.record(z.string(), z.int()))).toEqual({
      additionalProperties: { type: "integer" },
      title: "F",
      type: "object",
    });
    // Duplicate and nested-nullable unions collapse to Pydantic's form.
    expect(field(z.union([z.string(), z.string()]))).toEqual({ title: "F", type: "string" });
    expect(field(z.string().nullable().nullable())).toEqual({
      anyOf: [{ type: "string" }, { type: "null" }],
      title: "F",
    });
    // A second `.multipleOf()` is kept instead of dropped.
    expect(field(z.number().multipleOf(0.5).multipleOf(2))).toEqual({
      allOf: [{ multipleOf: 2 }],
      multipleOf: 0.5,
      title: "F",
      type: "number",
    });
    // `.includes(text, { position })` allows any longer prefix, as String.includes does.
    expect(field(z.string().includes("q", { position: 2 }))).toEqual({
      pattern: "^.{2,}q",
      title: "F",
      type: "string",
    });
    // A `z.preprocess()` field is required, as a Pydantic `BeforeValidator` field is.
    expect(compiled(z.preprocess((value) => value, z.string())).required).toEqual(["f"]);
  });
  test("compiles a .catch() field as the defaulted field Pydantic and Zod 4.4 emit", () => {
    // Zod's runtime fills an absent key with the catch value, and the Pydantic mirror is
    // `f: str = "x"`; Zod 4.6 lists the field in `required` anyway.
    const sha = (field: z.ZodType) =>
      buildCanonicalSchema(z.strictObject({ f: field }), "x:Catch/v1").sha;
    const compiled = (model: z.ZodType) => buildCanonicalSchema(model, "x:Catch/v1").schema;

    expect(z.strictObject({ f: z.string().catch("x") }).safeParse({}).success).toBe(true);
    expect(compiled(z.strictObject({ f: z.string().catch("x") })).required).toBeUndefined();
    expect(sha(z.string().catch("x"))).toBe(sha(z.string().default("x")));
    expect(sha(z.string().catch("x").describe("d"))).toBe(
      sha(z.string().default("x").describe("d")),
    );
    expect(sha(z.preprocess((value) => value, z.string().catch("x")))).toBe(
      sha(z.string().default("x")),
    );
    // Other keys stay required, and a nested or `$defs` object is corrected too.
    expect(
      compiled(z.strictObject({ f: z.string().catch("x"), g: z.int(), h: z.int().optional() }))
        .required,
    ).toEqual(["g"]);
    const Inner = z.strictObject({ g: z.int().catch(0), h: z.int() }).meta({ id: "Inner" });
    const defs = compiled(z.strictObject({ f: Inner })).$defs as Record<
      string,
      Record<string, unknown>
    >;
    expect(defs.Inner?.required).toEqual(["h"]);
  });
  test("compiles .catch() in records, tuples, and over transforms as Pydantic mirrors do", () => {
    const field = (schema: z.ZodType) =>
      (
        buildCanonicalSchema(z.strictObject({ f: schema }), "x:Catch/v1").schema.properties as {
          f: Record<string, unknown>;
        }
      ).f;
    const sha = (schema: z.ZodType) =>
      buildCanonicalSchema(z.strictObject({ f: schema }), "x:Catch/v1").sha;

    // A record whose value catches requires no key, as a Pydantic `dict` never does; Zod's
    // runtime fills each absent key. The value keeps its catch value as `default`, as
    // `dict[Literal["a", "b"], Annotated[int, Field(default=0)]]` emits it.
    const record = z.record(z.enum(["a", "b"]), z.int().catch(0));
    expect(record.safeParse({}).data).toEqual({ a: 0, b: 0 });
    expect(field(record)).toEqual({
      additionalProperties: { default: 0, type: "integer" },
      propertyNames: { enum: ["a", "b"] },
      title: "F",
      type: "object",
    });
    expect(
      field(
        z.record(
          z.enum(["a", "b"]),
          z.preprocess((v) => v, z.int().catch(0)),
        ),
      ),
    ).toEqual(field(record));
    // A required value still requires every key.
    expect(field(z.record(z.enum(["a", "b"]), z.int())).required).toEqual(["a", "b"]);

    // Over a transform, Zod 4.6 drops the catch value; the Pydantic mirror,
    // `Annotated[str, AfterValidator(f)] = "x"`, keeps it as `default`, as Zod 4.4 did.
    expect(
      sha(
        z
          .string()
          .transform((text) => text)
          .catch("x"),
      ),
    ).toBe(sha(z.string().default("x")));
    expect(
      field(
        z
          .string()
          .transform((text) => text.length)
          .catch(0),
      ),
    ).toEqual({
      default: 0,
      title: "F",
      type: "string",
    });

    // A tuple element is left alone: Pydantic cannot default one, and its
    // `tuple[str, Annotated[int, Field(default=0)]]` also counts it toward `minItems`.
    expect(field(z.tuple([z.string(), z.int().catch(0)]))).toEqual({
      maxItems: 2,
      minItems: 2,
      prefixItems: [{ type: "string" }, { default: 0, type: "integer" }],
      title: "F",
      type: "array",
    });
  });
  test("compiles .default() over a transform or pipe as the Pydantic mirror does", () => {
    // In input mode Zod 4.4 and 4.6 drop the `default` of a schema that transforms. The
    // Pydantic mirror, `Annotated[str, AfterValidator(f)] = "x"` (or `BeforeValidator` for
    // `z.preprocess()`), keeps it and emits what the plain `.default("x")` field emits.
    const compiled = (model: z.ZodType) => buildCanonicalSchema(model, "x:Default/v1").schema;
    const field = (schema: z.ZodType) =>
      (compiled(z.strictObject({ f: schema })).properties as { f: Record<string, unknown> }).f;
    const sha = (schema: z.ZodType) =>
      buildCanonicalSchema(z.strictObject({ f: schema }), "x:Default/v1").sha;
    const same = (text: string) => text;
    const plain = sha(z.string().default("x"));

    // `.transform().default()`, also behind a wrapper or with a computed default.
    expect(
      sha(
        z
          .string()
          .transform((text) => text)
          .default("x"),
      ),
    ).toBe(plain);
    expect(sha(z.string().transform(same).default("x").optional())).toBe(plain);
    expect(
      sha(
        z
          .string()
          .transform(same)
          .default(() => "x"),
      ),
    ).toBe(plain);
    expect(sha(z.string().transform(same).default("x").describe("d"))).toBe(
      sha(z.string().default("x").describe("d")),
    );
    // The default fills an absent key without running the transform, in Zod and Pydantic
    // alike, so it is written as given even when it is not of the input type.
    const counted = z.string().transform((text) => text.length);
    expect(z.strictObject({ f: counted.default(0) }).parse({})).toEqual({ f: 0 });
    expect(field(counted.default(0))).toEqual({ default: 0, title: "F", type: "string" });

    // `.default()` over a pipe that transforms: `z.preprocess()` and `.pipe(z.transform())`.
    expect(sha(z.preprocess((value) => value, z.string()).default("x"))).toBe(plain);
    expect(sha(z.string().pipe(z.transform(same)).default("x"))).toBe(plain);
    expect(sha(z.string().pipe(z.string()).default("x"))).toBe(plain);

    // Inside an object: an object default whose fields transform, inline or in `$defs`
    // (Pydantic's `f: Inner = Inner(a="x")`), and a transforming field of a `$defs` object.
    const Transformed = z.strictObject({ a: z.string().transform(same) });
    expect(sha(Transformed.default({ a: "x" }))).toBe(
      sha(z.strictObject({ a: z.string() }).default({ a: "x" })),
    );
    expect(field(Transformed.meta({ id: "Defaulted" }).default({ a: "x" }))).toEqual({
      $ref: "#/$defs/Defaulted",
      default: { a: "x" },
    });
    const Nested = z
      .strictObject({ g: z.int().transform(Number).default(0), h: z.int() })
      .meta({ id: "Nested" });
    expect((compiled(z.strictObject({ f: Nested })).$defs as { Nested: unknown }).Nested).toEqual({
      additionalProperties: false,
      properties: {
        g: { default: 0, title: "G", type: "integer" },
        h: { title: "H", type: "integer" },
      },
      required: ["h"],
      title: "Nested",
      type: "object",
    });

    // Inside a record: the value keeps its default and requires no key, as
    // `dict[Literal["a", "b"], Annotated[str, AfterValidator(f), Field(default="x")]]` does.
    const record = z.record(z.enum(["a", "b"]), z.string().transform(same).default("x"));
    expect(record.parse({})).toEqual({ a: "x", b: "x" });
    expect(field(record)).toEqual({
      additionalProperties: { default: "x", type: "string" },
      propertyNames: { enum: ["a", "b"] },
      title: "F",
      type: "object",
    });
    expect(sha(record)).toBe(sha(z.record(z.enum(["a", "b"]), z.string().default("x"))));

    // Zod also omits a field's default when the `$defs` entry it references carries the same
    // value. A restored value is settled the same way, so an id'd default compiles alike
    // whether or not it transforms, for `.default()` and `.catch()`; a different value stays.
    const ids = (name: string) => ({
      plain: z
        .enum(["a", "b"])
        .default("a")
        .meta({ id: `${name}Plain` }),
      transformed: z
        .enum(["a", "b"])
        .transform(same)
        .default("a")
        .meta({ id: `${name}Mapped` }),
      caught: z
        .enum(["a", "b"])
        .catch("a")
        .meta({ id: `${name}Caught` }),
      caughtTransformed: z
        .enum(["a", "b"])
        .transform(same)
        .catch("a")
        .meta({ id: `${name}CaughtMapped` }),
    });
    for (const [kind, schema] of Object.entries(ids("Status"))) {
      const ref = `#/$defs/${(z.globalRegistry.get(schema) as { id: string }).id}`;
      expect([kind, field(schema.describe("d"))]).toEqual([kind, { $ref: ref, description: "d" }]);
      expect([kind, field(schema.default("a" as never))]).toEqual([kind, { $ref: ref }]);
      expect([kind, field(schema.default("b" as never))]).toEqual([
        kind,
        { $ref: ref, default: "b" },
      ]);
    }
    // A reference to the root has no `$defs` entry, so the value stays, as Zod keeps it.
    const Tree: z.ZodType = z.strictObject({
      name: z.string().transform(same),
      get child() {
        return Tree.default({ name: "leaf" });
      },
    });
    expect((compiled(Tree).properties as { child: unknown }).child).toEqual({
      $ref: "#",
      default: { name: "leaf" },
    });
  });
  test("restores an authored default or examples over a transform, as Pydantic keeps them", () => {
    // In input mode Zod also drops an authored `.meta({ default })` or `.meta({ examples })`
    // from a schema that transforms. The Pydantic mirror, `Annotated[str, AfterValidator(f),
    // Field(examples=[...])]` or `Field(json_schema_extra={"default": ...})`, keeps both, and
    // emits what the field without the validator emits.
    const compiled = (model: z.ZodType) => buildCanonicalSchema(model, "x:Meta/v1").schema;
    const field = (schema: z.ZodType) =>
      (compiled(z.strictObject({ f: schema })).properties as { f: Record<string, unknown> }).f;
    const same = (text: string) => text;
    const mapped = () => z.string().transform(same);

    for (const meta of [
      { examples: ["a", "b"] },
      { default: "m" },
      { default: "m", examples: ["a"] },
    ]) {
      const plain = field(z.string().meta(meta));
      expect(field(mapped().meta(meta))).toEqual(plain);
      expect(field(z.preprocess((value) => value, z.string()).meta(meta))).toEqual(plain);
      expect(plain).toEqual({ ...meta, title: "F", type: "string" });
    }
    // An authored default fills nothing, so the field stays required, as in Pydantic.
    expect(compiled(z.strictObject({ f: mapped().meta({ default: "m" }) })).required).toEqual([
      "f",
    ]);
    expect(
      field(
        mapped()
          .default("x")
          .meta({ examples: ["a"] }),
      ),
    ).toEqual({
      default: "x",
      examples: ["a"],
      title: "F",
      type: "string",
    });
    const Shape = z.strictObject({ a: z.string().transform(same) });
    expect(field(Shape.meta({ examples: [{ a: "x" }] })).examples).toEqual([{ a: "x" }]);

    // A node's own value wins over one it inherits from a transforming inner type, as it does
    // without a transform.
    const outer = (schema: z.ZodType) => field(schema).default;
    expect(outer(mapped().default("a").default("b"))).toBe("b");
    expect(outer(mapped().catch("a").catch("b"))).toBe("b");
    expect(outer(z.string().default("a").transform(same).default("b"))).toBe("b");
    expect(outer(mapped().default("x").meta({ default: "m" }))).toBe("m");
    expect(outer(mapped().prefault("p").meta({ default: "m" }))).toBe("m");
    expect(outer(mapped().meta({ default: "m" }).default("x"))).toBe("x");

    // An id'd schema compiles to the same shape whether or not it transforms.
    const ids = {
      Plain: z.string().meta({ id: "MetaPlain", examples: ["a"], default: "m" }),
      Mapped: mapped().meta({ id: "MetaMapped", examples: ["a"], default: "m" }),
    };
    const shapes = Object.entries(ids).map(([kind, schema]) => {
      const out = compiled(
        z.strictObject({
          d: schema.describe("d"),
          e: schema.meta({ examples: ["b"] }),
          n: schema.default("n"),
          s: schema.default("m"),
        }),
      );
      const entry = (out.$defs as Record<string, unknown>)[`Meta${kind}`];
      const named = JSON.stringify({ entry, fields: out.properties });
      return JSON.parse(named.replaceAll(`Meta${kind}`, "Meta")) as { fields: unknown };
    });
    expect(shapes[1]).toEqual(shapes[0]);
    expect(shapes[0]?.fields).toEqual({
      d: { $ref: "#/$defs/Meta", description: "d" },
      e: { $ref: "#/$defs/Meta", examples: ["b"] },
      n: { $ref: "#/$defs/Meta", default: "n" },
      s: { $ref: "#/$defs/Meta" },
    });

    // A restored authored default is checked like any other.
    expect(() => field(z.number().transform(Number).meta({ default: Number.NaN }))).toThrow(
      "canonical JSON requires finite numbers; the default at #/properties/f is NaN",
    );
  });
  test("keeps Zod's output for id'd aliases and wrappers without a transform", () => {
    // Only a key Zod dropped is restored or settled. These shapes carry no transform, so each
    // compiles as Zod writes it, though a `$ref` names an entry with the same default.
    const compiled = (schema: z.ZodType) => {
      const out = buildCanonicalSchema(z.strictObject({ f: schema }), "x:Alias/v1").schema;
      return {
        f: (out.properties as { f: unknown }).f,
        defs: out.$defs as Record<string, unknown>,
      };
    };
    const R = () => z.string().default("x").meta({ id: "AliasR" });
    const Rdef = { default: "x", title: "AliasR", type: "string" };
    const Q = () => R().describe("q").meta({ id: "AliasQ" });
    const Qdef = { $ref: "#/$defs/AliasR", default: "x", description: "q", type: "string" };

    // A wrapper between the field and its `$ref` keeps the field's own default.
    expect(compiled(R().optional().default("x"))).toEqual({
      f: { $ref: "#/$defs/AliasR", default: "x" },
      defs: { AliasR: Rdef },
    });
    // An alias without the default refers on to the entry that carries it.
    expect(compiled(R().default("x").meta({ id: "AliasP" }).describe("d"))).toEqual({
      f: { $ref: "#/$defs/AliasP", description: "d" },
      defs: { AliasP: { $ref: "#/$defs/AliasR" }, AliasR: Rdef },
    });
    // An alias that keeps the default keeps it in `$defs`, and the field leaves it out.
    expect(compiled(Q().describe("d"))).toEqual({
      f: { $ref: "#/$defs/AliasQ", description: "d" },
      defs: { AliasQ: Qdef, AliasR: Rdef },
    });
    expect(compiled(Q().default("x"))).toEqual({
      f: { $ref: "#/$defs/AliasQ" },
      defs: { AliasQ: Qdef, AliasR: Rdef },
    });
    // Three levels: the outer alias keeps its default because the one between does not.
    const C2 = R().default("x").meta({ id: "AliasC1" }).default("x").meta({ id: "AliasC2" });
    expect(compiled(C2.describe("b"))).toEqual({
      f: { $ref: "#/$defs/AliasC2", description: "b" },
      defs: {
        AliasC1: { $ref: "#/$defs/AliasR" },
        AliasC2: { $ref: "#/$defs/AliasC1", default: "x" },
        AliasR: Rdef,
      },
    });
  });
  test("rejects a default or catch value canonical JSON cannot carry, as Python does", () => {
    const compile = (field: z.ZodType) =>
      buildCanonicalSchema(z.strictObject({ f: field }), "x:NonJson/v1");
    const toNumber = (value: number) => value;
    const transformingCatch = (fallback: unknown) =>
      z
        .number()
        .transform(toNumber)
        .catch(fallback as number);

    // A restored fallback over a transform is checked: Zod's JSON copy would turn these into
    // `null` or fail without naming the field.
    for (const [fallback, shown] of [
      [Number.NaN, "NaN"],
      [Number.POSITIVE_INFINITY, "Infinity"],
      [Number.NEGATIVE_INFINITY, "-Infinity"],
    ] as const) {
      expect(() => compile(transformingCatch(fallback))).toThrow(
        `canonical JSON requires finite numbers; the .catch() value at #/properties/f is ${shown}`,
      );
    }
    expect(() => compile(transformingCatch(1n))).toThrow(
      "canonical JSON cannot represent a BigInt; the .catch() value at #/properties/f is 1n",
    );
    expect(() => compile(z.number().transform(toNumber).default(Number.NaN))).toThrow(
      "canonical JSON requires finite numbers; the .default() value at #/properties/f is NaN",
    );
    // So is every other default, which used to compile to `default: null`.
    expect(() => compile(z.number().catch(Number.NaN))).toThrow(
      "the .catch() value at #/properties/f is NaN",
    );
    expect(() => compile(z.number().default(Number.POSITIVE_INFINITY))).toThrow(
      "the .default() value at #/properties/f is Infinity",
    );
    expect(() => compile(z.number().prefault(Number.NaN))).toThrow(
      "the .prefault() value at #/properties/f is NaN",
    );
    expect(() => compile(z.number().meta({ default: Number.NaN }))).toThrow(
      "the default at #/properties/f is NaN",
    );
    // Authored examples are checked the same way, as Python's compiler checks them.
    expect(() => compile(z.number().meta({ examples: [Number.NaN] }))).toThrow(
      "canonical JSON requires finite numbers; the examples at #/properties/f is NaN",
    );
    expect(() =>
      compile(
        z
          .number()
          .transform(toNumber)
          .meta({ examples: [1n] }),
      ),
    ).toThrow("canonical JSON cannot represent a BigInt; the examples at #/properties/f is 1n");
    // A Date fallback or restored default is written as its ISO string, as a `.default()`
    // Date already is and as Pydantic writes a datetime default.
    const epoch = new Date(0);
    const toDate = z.string().transform((text) => new Date(text));
    const dateCatch = toDate.catch(epoch);
    expect((compile(dateCatch).schema.properties as { f: unknown }).f).toEqual({
      default: "1970-01-01T00:00:00.000Z",
      title: "F",
      type: "string",
    });
    expect(compile(dateCatch).sha).toBe(compile(z.string().default(epoch as never)).sha);
    expect(compile(toDate.default(epoch)).sha).toBe(compile(dateCatch).sha);
  });
  test("semantic datetime options do not change the structural schema digest", () => {
    const variants = [
      z.iso.datetime(),
      z.iso.datetime({ offset: true }),
      z.iso.datetime({ local: true }),
      z.iso.datetime({ precision: 3 }),
    ];
    const compiled = variants.map((variant) =>
      buildCanonicalSchema(z.strictObject({ at: variant }), "x:DateTimeOptions/v1"),
    );

    expect(new Set(compiled.map((result) => result.sha)).size).toBe(1);
    expect(
      compiled.map(
        (result) => (result.schema.properties as Record<string, Record<string, unknown>>).at,
      ),
    ).toEqual(variants.map(() => ({ format: "date-time", title: "At", type: "string" })));
  });
  test("shared generated-title vectors", () => {
    const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
      string,
      Array<Record<string, unknown>>
    >;
    for (const item of vectors.compiler_titles ?? []) {
      const model = z.strictObject({ camelCase: z.string() });
      const { schema } = buildCanonicalSchema(model, String(item.contract));
      expect(schema.title).toBe(item.expected_root);
      const properties = schema.properties as Record<string, Record<string, unknown>>;
      expect(properties[String(item.field)]?.title).toBe(item.expected_field);
    }
  });
  test("separates schema identity and rejects reserved root metadata", () => {
    const { schema } = buildCanonicalSchema(
      Sample,
      "x:S/v1",
      "https://example.com/schemas/sample-v1",
    );
    const xss = schema["x-softschema"] as Record<string, unknown>;
    expect(xss.contract).toBe("x:S/v1");
    expect(xss.schema_sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(schema.$id).toBe("https://example.com/schemas/sample-v1");
    const Reserved = Sample.meta({ "x-softschema": { custom: true } });
    expect(() => buildCanonicalSchema(Reserved, "x:S/v1")).toThrow("reserved root identity key");
  });
  test("drift comparison is portable and boolean-safe", () => {
    const out = join(mkdtempSync(join(tmpdir(), "softschema-drift-")), "s.yaml");
    compileSchema(Sample, out, { contractId: "x:S/v1" });
    writeFileSync(
      out,
      readFileSync(out, "utf8").replace("additionalProperties: false", "additionalProperties: 0"),
    );
    expect(compileSchema(Sample, out, { contractId: "x:S/v1", checkOnly: true }).drift).toBe(true);
    writeFileSync(out, Buffer.from([0xff]));
    expect(() => compileSchema(Sample, out, { contractId: "x:S/v1", checkOnly: true })).toThrow(
      "UTF-8",
    );
  });
});

describe("validate: frontmatter edge cases (ss-3iz5)", () => {
  test("empty frontmatter (---\\n---) returns no_frontmatter, matching Python fmf_read", () => {
    const r = validateArtifact(tmp("d.md", "---\n---\nbody\n"), contract());
    const errors = (r.structural as { errors: { kind: string; message: string }[] }).errors;
    expect(errors[0]?.kind).toBe("no_frontmatter");
    expect(errors[0]?.message).toContain("no frontmatter in ");
  });
  test("whitespace-only frontmatter returns yaml_parse_error", () => {
    const path = tmp("d.md", "---\n   \n---\nbody\n");
    const r = validateArtifact(path, contract());
    const errors = (r.structural as { errors: { kind: string; message: string }[] }).errors;
    expect(errors[0]?.kind).toBe("yaml_parse_error");
    expect(errors[0]?.message).toBe(
      `Expected YAML metadata to be a dict, got NoneType: \`${path}\``,
    );
  });
  test("unterminated fence returns yaml_parse_error", () => {
    const path = tmp("d.md", "---\nfoo: 1\n...no closing ---\n");
    const r = validateArtifact(path, contract());
    const errors = (r.structural as { errors: { kind: string; message: string }[] }).errors;
    expect(errors[0]?.kind).toBe("yaml_parse_error");
    expect(errors[0]?.message).toBe(
      `Delimiter \`---\` for end of frontmatter not found: \`${path}\``,
    );
  });
});

describe("models: parseSchemaMetadata uses Python type names (ss-3iz5)", () => {
  test("list (array) argument produces 'got list' not 'got object'", () => {
    expect(() => parseSchemaMetadata([1, 2, 3])).toThrow(
      "softschema metadata must be a string or mapping, got list",
    );
  });
  test("number argument produces 'got int' or 'got float'", () => {
    expect(() => parseSchemaMetadata(42)).toThrow(
      "softschema metadata must be a string or mapping, got int",
    );
    expect(() => parseSchemaMetadata(3.14)).toThrow(
      "softschema metadata must be a string or mapping, got float",
    );
  });
  test("boolean argument produces 'got bool'", () => {
    expect(() => parseSchemaMetadata(true)).toThrow(
      "softschema metadata must be a string or mapping, got bool",
    );
  });
});

describe("validate: artifact error kinds + advisory warning", () => {
  test("no_frontmatter", () => {
    const r = validateArtifact(tmp("d.md", "no fence here\n"), contract());
    expect((r.structural as { errors: { kind: string }[] }).errors[0]?.kind).toBe("no_frontmatter");
  });
  test("document_softschema_invalid", () => {
    const r = validateArtifact(
      tmp("d.md", "---\nsoftschema:\n  status: enforced\nx: 1\n---\n"),
      contract(),
    );
    expect((r.structural as { errors: { kind: string }[] }).errors[0]?.kind).toBe(
      "document_softschema_invalid",
    );
  });
  test("document_contract_mismatch (enforced) vs warning (advisory)", () => {
    const doc = tmp("d.md", "---\nsoftschema:\n  contract: other:Z/v1\nmovie:\n  a: 1\n---\n");
    const enforced = validateArtifact(doc, contract({ id: "x:S/v1", envelopeKey: "movie" }));
    expect((enforced.structural as { errors: { kind: string }[] }).errors[0]?.kind).toBe(
      "document_contract_mismatch",
    );
    const advisory = validateArtifact(doc, contract({ id: "x:S/v1", envelopeKey: "movie" }), {
      metadataMode: "advisory",
    });
    expect((advisory.warnings as { code: string }[])[0]?.code).toBe("document-contract-mismatch");
  });
  test("envelope_mismatch + schema_missing", () => {
    const em = validateArtifact(
      tmp("d.md", "---\nwrong:\n  a: 1\n---\n"),
      contract({ envelopeKey: "movie" }),
    );
    expect((em.structural as { errors: { kind: string }[] }).errors[0]?.kind).toBe(
      "envelope_mismatch",
    );
    const sm = validateArtifact(
      tmp("d.md", "---\nmovie:\n  a: 1\n---\n"),
      contract({ envelopeKey: "movie", schemaPath: "/no/such/schema.yaml" }),
    );
    expect((sm.structural as { errors: { kind: string }[] }).errors[0]?.kind).toBe(
      "schema_missing",
    );
  });
});
