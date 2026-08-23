/**
 * Tests for the `status: enforced` strict-extras overlay (applyEnforcedExtras).
 * Mirrors packages/python/tests/test_enforced_extras.py case for case.
 */

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync as wf } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as yamlParse } from "yaml";
import { applyEnforcedExtras } from "./canonicalize.js";
import type { Contract } from "./models.js";
import { validateArtifact, validateStructural } from "./validate.js";

type Schema = Record<string, unknown>;
const HARDENING_VECTORS = join(import.meta.dir, "../../../tests/vectors/hardening.yaml");

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

// Envelope inference and pure-yaml metadata behaviors (mirrors Python test_core
// additions for ss-z3gy and ss-cke0).
function tmpDoc(name: string, content: string): string {
  const dir = mkdtempSync(join(tmpdir(), "softschema-env-"));
  const p = join(dir, name);
  wf(p, content);
  return p;
}

function mkContract(overrides: Partial<Contract> = {}): Contract {
  return {
    id: "t:X/v1",
    model: null,
    envelopeKey: null,
    status: "soft",
    profile: "frontmatter-md",
    schemaPath: null,
    ...overrides,
  };
}

describe("envelope inference (spec rules)", () => {
  test("multi-key root without envelopeKey is envelope_ambiguous", () => {
    const doc = tmpDoc("doc.md", "---\nname: hi\ndirection: up\n---\nbody\n");
    const result = validateArtifact(doc, mkContract());
    const structural = result.structural as { errors: { kind: string; message: string }[] };
    expect(structural.errors[0]?.kind).toBe("envelope_ambiguous");
    expect(structural.errors[0]?.message).toContain("name");
  });

  test("zero-key root without envelopeKey is envelope_missing", () => {
    const doc = tmpDoc("doc.md", "---\nsoftschema:\n  contract: t:X/v1\n---\nbody\n");
    const result = validateArtifact(doc, mkContract());
    const structural = result.structural as { errors: { kind: string }[] };
    expect(structural.errors[0]?.kind).toBe("envelope_missing");
  });
});

describe("pure-yaml metadata rules", () => {
  test("the softschema block is metadata, not payload", () => {
    const doc = tmpDoc("doc.yaml", "softschema:\n  contract: t:X/v1\nname: hello\ncount: 1\n");
    const result = validateArtifact(doc, mkContract({ profile: "pure-yaml" }));
    expect(result.ok).toBe(true);
    expect(result.values).toEqual({ name: "hello", count: 1 });
    expect(result.document_metadata).toEqual({
      contract: "t:X/v1",
      envelope: null,
      schema: null,
      status: null,
    });
  });

  test("a contract mismatch in the block is detected", () => {
    const doc = tmpDoc("doc.yaml", "softschema:\n  contract: t:X/v1\nname: hello\n");
    const result = validateArtifact(doc, mkContract({ id: "other:Y/v1", profile: "pure-yaml" }));
    const structural = result.structural as { errors: { kind: string }[] };
    expect(structural.errors[0]?.kind).toBe("document_contract_mismatch");
  });

  test("an explicit envelopeKey nests the payload", () => {
    const doc = tmpDoc("doc.yaml", "softschema:\n  contract: t:X/v1\npayload:\n  name: hi\n");
    const result = validateArtifact(
      doc,
      mkContract({ profile: "pure-yaml", envelopeKey: "payload" }),
    );
    expect(result.ok).toBe(true);
    expect(result.values).toEqual({ name: "hi" });
  });
});

describe("validateArtifact document (single read)", () => {
  test("uses a pre-parsed frontmatter root without reopening the file", () => {
    // A nonexistent path proves the document is not re-read when `document` is supplied.
    const result = validateArtifact("/does/not/exist.md", mkContract({ envelopeKey: "payload" }), {
      document: {
        hasFence: true,
        value: { softschema: { contract: "t:X/v1" }, payload: { name: "hi" } },
      },
    });
    expect(result.ok).toBe(true);
    expect(result.values).toEqual({ name: "hi" });
  });

  test("uses a pre-parsed pure-yaml root without reopening the file", () => {
    // No envelopeKey, so this also covers the rule that separates the profiles: the root
    // minus the metadata block IS the payload.
    const result = validateArtifact("/does/not/exist.yaml", mkContract({ profile: "pure-yaml" }), {
      document: {
        hasFence: false,
        value: { softschema: { contract: "t:X/v1" }, name: "hi" },
      },
    });
    expect(result.ok).toBe(true);
    expect(result.values).toEqual({ name: "hi" });
  });
});

const CLOSURE_KEYWORDS = ["additionalProperties", "unevaluatedProperties"];

const THEN = "then";

/** One engine's expected record for a documented cross-implementation deviation. */
type DeviationRecord = { code: unknown; validator: unknown; path: unknown };

/** Read one nested mapping out of an overlay result, for assertions below. */
function mapping(node: unknown, ...keys: string[]): Record<string, unknown> {
  let current = node as Record<string, unknown>;
  for (const key of keys) {
    current = current[key] as Record<string, unknown>;
  }
  return current;
}

test("fragments are never closed internally", () => {
  // Closing a fragment is the failure this rule exists to prevent: an `allOf` branch
  // would reject keys its sibling declares, and an `if` matcher would stop firing.
  // `then` is set through a computed key: biome's noThenProperty rule guards against
  // accidentally thenable objects, and the JSON Schema keyword of that name trips it.
  const conditional: Record<string, unknown> = {
    if: { properties: { kind: { const: "special" } } },
  };
  conditional[THEN] = { properties: { extra: { type: "string" } } };
  const out = applyEnforcedExtras({
    type: "object",
    properties: { kind: { type: "string" } },
    allOf: [{ properties: { first: { type: "string" } } }],
    ...conditional,
  } as Schema);

  expect(out.unevaluatedProperties).toBe(false);
  const fragments = [(out.allOf as unknown[])[0], out.if, out[THEN]];
  for (const fragment of fragments) {
    expect(fragment).not.toHaveProperty("additionalProperties");
    expect(fragment).not.toHaveProperty("unevaluatedProperties");
  }
});

test("a definition reached only through a fragment stays open", () => {
  // The `allOf: [{$ref: Base}, {properties: ...}]` extension idiom. Closing Address
  // lexically rejects `extra`, which the sibling branch declares.
  const out = applyEnforcedExtras({
    allOf: [{ $ref: "#/$defs/Address" }, { properties: { extra: { type: "string" } } }],
    $defs: { Address: { type: "object", properties: { street: { type: "string" } } } },
  } as Schema);

  expect(mapping(out, "$defs", "Address")).not.toHaveProperty("additionalProperties");
  expect(mapping(out, "$defs", "Address")).not.toHaveProperty("unevaluatedProperties");
  // The root closes over the definition instead; annotations make that correct.
  expect(out.unevaluatedProperties).toBe(false);
});

test("a definition reached outside a fragment still closes", () => {
  const out = applyEnforcedExtras({
    type: "object",
    properties: { addr: { $ref: "#/$defs/Address" } },
    allOf: [{ $ref: "#/$defs/Address" }],
    $defs: { Address: { type: "object", properties: { street: { type: "string" } } } },
  } as Schema);

  expect(mapping(out, "$defs", "Address").additionalProperties).toBe(false);
});

test("a fragment $ref to a free-form definition does not close the root", () => {
  // Treating any `$ref` as a declaration would close this schema against every key.
  const out = applyEnforcedExtras({
    allOf: [{ $ref: "#/$defs/Anything" }],
    $defs: { Anything: { type: "object" } },
  } as Schema);

  expect(out).not.toHaveProperty("additionalProperties");
  expect(out).not.toHaveProperty("unevaluatedProperties");
});

test("cyclic local references terminate", () => {
  applyEnforcedExtras({
    allOf: [{ $ref: "#/$defs/A" }],
    $defs: { A: { $ref: "#/$defs/B" }, B: { $ref: "#/$defs/A" } },
  } as Schema);
});

test("properties under not are prohibitions, not declarations", () => {
  // `not` contributes no annotations, so closing over its properties would leave the
  // schema admitting nothing at all.
  const out = applyEnforcedExtras({
    type: "object",
    not: { properties: { b: { type: "string" } }, required: ["b"] },
  } as Schema);

  expect(out).not.toHaveProperty("additionalProperties");
  expect(out).not.toHaveProperty("unevaluatedProperties");
});

test("explicit unevaluatedProperties always wins", () => {
  const out = applyEnforcedExtras({
    properties: { a: { type: "string" } },
    allOf: [{ properties: { b: { type: "string" } } }],
    unevaluatedProperties: true,
  } as Schema);
  expect(out.unevaluatedProperties).toBe(true);
});

test("shared enforcement vectors", () => {
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  for (const item of vectors.enforcement ?? []) {
    const out = applyEnforcedExtras(item.schema as Schema);
    const injected = CLOSURE_KEYWORDS.filter((keyword) => keyword in out);
    const expected = item.closure === "none" ? [] : [item.closure as string];
    expect(injected, item.id as string).toEqual(expected);
    const defsClosure = (item.defs_closure ?? {}) as Record<string, string>;
    for (const [name, keyword] of Object.entries(defsClosure)) {
      const definition = mapping(out, "$defs", name);
      if (keyword === "none") {
        expect(
          CLOSURE_KEYWORDS.filter((closure) => closure in definition),
          `${item.id}/${name}`,
        ).toEqual([]);
      } else {
        expect(definition[keyword], `${item.id}/${name}`).toBe(false);
      }
    }
  }
});

test("composed schemas validate instead of refusing", () => {
  // The shape the refusal was built for. Both documents were `invalid` with an
  // `enforcement_unsupported` record before the applicator split.
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  const item = (vectors.enforcement ?? []).find((candidate) => candidate.id === "composed_object");
  const schema = item?.schema as Record<string, unknown>;

  const ok = validateStructural({ first: "Ada", last: "Lovelace" }, schema, {
    strictExtras: true,
  });
  expect(ok.ok, JSON.stringify(ok.errors)).toBe(true);

  const rejected = validateStructural({ first: "Ada", last: "Lovelace", bogus: 1 }, schema, {
    strictExtras: true,
  });
  expect(rejected.ok).toBe(false);
  expect(rejected.errors.map((error) => error.code)).toEqual(["undeclared_property"]);
  expect(rejected.errors[0]?.validator).toBe("unevaluatedProperties");
});

test("a conditional reports the real violation", () => {
  // Issue #41 case (b): the conditional must fire and name the missing property,
  // rather than being masked by a generic message about `allOf`.
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  const item = (vectors.enforcement ?? []).find(
    (candidate) => candidate.id === "conditional_object",
  );
  const schema = item?.schema as Record<string, unknown>;

  expect(validateStructural({ kind: "plain" }, schema, { strictExtras: true }).ok).toBe(true);

  const violation = validateStructural({ kind: "special" }, schema, { strictExtras: true });
  expect(violation.ok).toBe(false);
  // ajv also emits an `if` wrapper restating the cause; normalization drops it so the
  // record set matches Python's.
  expect(violation.errors.map((error) => error.code)).toEqual(["missing_property"]);
  expect(violation.errors[0]?.message).toBe("required property ['extra'] is missing");
});

test("documented engine deviations", () => {
  // Each runtime asserts its own listed record set exactly, so a documented deviation
  // passes while drift on either side fails. See the section comment in the vectors.
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  for (const item of vectors.engine_deviations ?? []) {
    const result = validateStructural(item.value, item.schema as Record<string, unknown>, {
      strictExtras: item.strict_extras as boolean,
    });
    expect(result.ok, item.id as string).toBe(item.verdict === "valid");
    const actual = result.errors.map((error) => ({
      code: error.code,
      validator: error.validator,
      path: error.path,
    }));
    expect(actual, item.id as string).toEqual(item.typescript as DeviationRecord[]);
  }
});

test("documented enforcement gaps", () => {
  // Shapes enforced deliberately does not close. Pinned as document outcomes so the gap
  // stays visible and any later change is loud rather than silent.
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  for (const item of vectors.enforcement_gaps ?? []) {
    const result = validateStructural(item.value, item.schema as Record<string, unknown>, {
      strictExtras: true,
    });
    expect(result.ok, `${item.id}: ${JSON.stringify(result.errors)}`).toBe(
      item.verdict === "valid",
    );
  }
});

test("multiple undeclared keys collapse to one record", () => {
  // ajv emits one closure error per key; jsonschema emits one per object. With two
  // undeclared keys the collapse is observable — with one it is indistinguishable from
  // no collapse at all.
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  const item = (vectors.enforcement ?? []).find((candidate) => candidate.id === "composed_object");

  const result = validateStructural(
    { first: "Ada", last: "Lovelace", bogus: 1, other: 2 },
    item?.schema as Record<string, unknown>,
    { strictExtras: true },
  );

  expect(result.errors.map((error) => error.code)).toEqual(["undeclared_property"]);
});
