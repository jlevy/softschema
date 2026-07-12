import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as yamlParse } from "yaml";
import { z } from "zod";
import { buildCanonicalSchema, compileSchema } from "./compile.js";
import {
  collapseAdditionalProperties,
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

  test("normalizeAjvError uses the full required list for required (matching jsonschema)", () => {
    // Regression for ss-l9ng: Python's validator_value is the whole required array.
    const rec = normalizeAjvError({
      instancePath: "",
      keyword: "required",
      params: { missingProperty: "title" },
      schema: ["title", "year"],
      data: { year: 2000 },
    } as never);
    expect(rec.validator_value).toEqual(["title", "year"]);
    expect(rec.message).toBe("required property ['title', 'year'] is missing");
  });

  test("collapseAdditionalProperties keeps one record per object path", () => {
    // Regression for ss-b1l9: ajv emits one additionalProperties error per extra key.
    const base = structuralErrorRecord({
      path: [],
      validator: "additionalProperties",
      validatorValue: false,
      value: { a: 1, b: 2 },
    });
    expect(collapseAdditionalProperties([base, { ...base }])).toEqual([base]);
    const req = structuralErrorRecord({
      path: [],
      validator: "required",
      validatorValue: ["x"],
      value: {},
    });
    // required duplicates are preserved (jsonschema also emits one per missing key).
    expect(collapseAdditionalProperties([req, { ...req }])).toHaveLength(2);
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
      `Expected YAML metadata to be a dict, got <class 'NoneType'>: \`${path}\``,
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
