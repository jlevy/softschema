/**
 * Tests for the `status: enforced` strict-extras overlay (applyEnforcedExtras).
 * Mirrors packages/python/tests/test_enforced_extras.py case for case.
 */

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync as wf } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as yamlParse } from "yaml";
import { applyEnforcedExtras, EnforcementUnsupportedError } from "./canonicalize.js";
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

describe("validateArtifact preParsed (single read)", () => {
  test("uses pre-parsed frontmatter without reopening the file", () => {
    // A nonexistent path proves the document is not re-read when preParsed is supplied.
    const result = validateArtifact("/does/not/exist.md", mkContract({ envelopeKey: "payload" }), {
      preParsed: {
        hasFence: true,
        value: { softschema: { contract: "t:X/v1" }, payload: { name: "hi" } },
      },
    });
    expect(result.ok).toBe(true);
    expect(result.values).toEqual({ name: "hi" });
  });
});

test("shared enforcement vectors", () => {
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  for (const item of vectors.enforcement ?? []) {
    if (item.supported) {
      expect(applyEnforcedExtras(item.schema as Schema).additionalProperties).toBe(false);
    } else {
      expect(() => applyEnforcedExtras(item.schema as Schema)).toThrow(EnforcementUnsupportedError);
    }
  }
});

test("structural validation reports unsupported enforcement", () => {
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  const item = (vectors.enforcement ?? []).find((candidate) => !candidate.supported);
  const result = validateStructural(
    { first: "Ada", last: "Lovelace" },
    item?.schema as Record<string, unknown>,
    { strictExtras: true },
  );
  expect(result.errors[0]?.kind).toBe("enforcement_unsupported");
});
