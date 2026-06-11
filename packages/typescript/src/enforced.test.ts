/**
 * Tests for the `status: enforced` strict-extras overlay (applyEnforcedExtras).
 * Mirrors packages/python/tests/test_enforced_extras.py case for case.
 */
import { describe, expect, test } from "bun:test";
import { applyEnforcedExtras } from "./canonicalize.js";

type Schema = Record<string, unknown>;

function baseSchema(): Schema {
  return {
    type: "object",
    properties: {
      name: { type: "string" },
      meta: {
        type: "object",
        properties: { source: { type: "string" } },
      },
      scores: { type: "object" },
      primary: { $ref: "#/$defs/Address" },
      secondary: {
        anyOf: [{ $ref: "#/$defs/Address" }, { type: "null" }],
      },
    },
    $defs: {
      Address: {
        type: "object",
        properties: { street: { type: "string" } },
      },
    },
  };
}

describe("applyEnforcedExtras", () => {
  test("injects closed objects where properties are present", () => {
    const out = applyEnforcedExtras(baseSchema()) as {
      additionalProperties: unknown;
      properties: { meta: Schema };
      $defs: { Address: Schema };
    };
    expect(out.additionalProperties).toBe(false);
    expect(out.properties.meta.additionalProperties).toBe(false);
    expect(out.$defs.Address.additionalProperties).toBe(false);
  });

  test("free-form objects without properties are untouched", () => {
    const out = applyEnforcedExtras(baseSchema()) as { properties: { scores: Schema } };
    expect("additionalProperties" in out.properties.scores).toBe(false);
  });

  test("explicit additionalProperties always wins", () => {
    const schema = baseSchema();
    schema.additionalProperties = true;
    (schema.properties as { meta: Schema }).meta.additionalProperties = { type: "string" };

    const out = applyEnforcedExtras(schema) as {
      additionalProperties: unknown;
      properties: { meta: Schema };
    };
    expect(out.additionalProperties).toBe(true);
    expect(out.properties.meta.additionalProperties).toEqual({ type: "string" });
  });

  test("recurses into anyOf branches", () => {
    const out = applyEnforcedExtras({
      anyOf: [{ type: "object", properties: { a: { type: "string" } } }, { type: "null" }],
    }) as { anyOf: Schema[] };
    expect(out.anyOf[0]?.additionalProperties).toBe(false);
    expect("additionalProperties" in out).toBe(false);
  });

  test("a field named 'properties' is a name, not the keyword", () => {
    const out = applyEnforcedExtras({
      type: "object",
      properties: {
        properties: { type: "object", properties: { x: { type: "integer" } } },
      },
    }) as { additionalProperties: unknown; properties: { properties: Schema } };
    expect(out.additionalProperties).toBe(false);
    expect(out.properties.properties.additionalProperties).toBe(false);
  });

  test("input schema is not mutated", () => {
    const schema = baseSchema();
    const snapshot = JSON.parse(JSON.stringify(schema));
    applyEnforcedExtras(schema);
    expect(schema).toEqual(snapshot);
  });
});
