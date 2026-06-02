import { describe, expect, test } from "bun:test";
import { canonicalizeJsonSchema } from "./canonicalize.js";
import { renderStructuralMessage, structuralErrorRecord } from "./errors.js";
import { canonicalJson, stableStringify } from "./settings.js";

describe("stableStringify", () => {
  test("sorts keys recursively with 2-space indent (matches Python json.dumps)", () => {
    expect(stableStringify({ b: 1, a: { d: 2, c: 3 } })).toBe(
      '{\n  "a": {\n    "c": 3,\n    "d": 2\n  },\n  "b": 1\n}',
    );
  });
  test("renders empty containers and null like Python", () => {
    expect(stableStringify({ a: {}, b: [], c: null })).toBe(
      '{\n  "a": {},\n  "b": [],\n  "c": null\n}',
    );
  });
});

describe("canonicalJson", () => {
  test("compact sorted keys for hashing", () => {
    expect(canonicalJson({ b: 1, a: 2 })).toBe('{"a":2,"b":1}');
  });
});

describe("renderStructuralMessage", () => {
  test("engine-neutral wording matches Python templates", () => {
    expect(renderStructuralMessage("minimum", 1888, 1500)).toBe(
      "value 1500 is less than the minimum of 1888",
    );
    expect(renderStructuralMessage("minItems", 1, [])).toBe(
      "array is shorter than the minimum of 1 items",
    );
    expect(renderStructuralMessage("exclusiveMinimum", 0, 0)).toBe(
      "value 0 is not greater than 0",
    );
    expect(renderStructuralMessage("enum", ["G", "PG"], "X")).toBe(
      "value 'X' is not one of ['G', 'PG']",
    );
  });
  test("record shape matches the neutral contract", () => {
    expect(
      structuralErrorRecord({ path: ["count"], validator: "maximum", validatorValue: 10, value: 11 }),
    ).toEqual({
      kind: "schema_violation",
      path: ["count"],
      validator: "maximum",
      validator_value: 10,
      value: 11,
      message: "value 11 is greater than the maximum of 10",
    });
  });
});

describe("canonicalizeJsonSchema", () => {
  test("drops title keyword but keeps a title-named property", () => {
    const out = canonicalizeJsonSchema({
      type: "object",
      title: "Movie",
      properties: { title: { type: "string", title: "Title" }, year: { type: "integer" } },
    });
    expect("title" in out).toBe(false);
    const props = out.properties as Record<string, Record<string, unknown>>;
    expect(Object.keys(props).sort()).toEqual(["title", "year"]);
    expect("title" in (props.title as object)).toBe(false);
  });
  test("strips implicit null default and rewrites oneOf nullable to anyOf", () => {
    const out = canonicalizeJsonSchema({
      properties: {
        a: { oneOf: [{ type: "string" }, { type: "null" }], default: null },
        b: { type: "integer", default: 0 },
      },
    });
    const props = out.properties as Record<string, Record<string, unknown>>;
    expect(props.a).toEqual({ anyOf: [{ type: "string" }, { type: "null" }] });
    expect((props.b as Record<string, unknown>).default).toBe(0);
  });
});
