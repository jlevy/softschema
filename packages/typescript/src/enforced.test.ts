/**
 * Tests for the `status: enforced` strict-extras overlay (applyEnforcedExtras).
 * Mirrors packages/python/tests/test_enforced_extras.py case for case.
 */

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync as wf } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import { loadYamlFixture } from "../test/yaml-fixture.js";
import {
  applyEnforcedExtras,
  ENFORCEMENT_UNSUPPORTED_MESSAGE,
  EnforcementUnsupportedError,
} from "./canonicalize.js";
import type { Contract } from "./models.js";
import { validateArtifact, validateStructural } from "./validate.js";

type Schema = Record<string, unknown>;

interface EnforcementVector {
  id: string;
  input: Schema;
  expected: Schema;
}

interface UnsupportedEnforcementVector {
  id: string;
  input: Schema;
  schema_path: string;
}

interface EnforcementValidationVector {
  enforcement_id: string;
  valid: unknown[];
  invalid: unknown[];
}

const sharedEnforcementVectors = loadYamlFixture<{
  enforcement: EnforcementVector[];
  enforcement_unsupported: UnsupportedEnforcementVector[];
  enforcement_validation: EnforcementValidationVector[];
}>(resolve(import.meta.dir, "../../../tests/parity/canonicalization-enforcement.yaml"));

const enforcementVectors = (sharedEnforcementVectors as { enforcement: EnforcementVector[] })
  .enforcement;

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
      properties: { meta: Schema; primary: Schema; secondary: Schema };
      $defs: { Address: Schema };
    };
    expect(out.additionalProperties).toBe(false);
    expect(out.properties.meta.additionalProperties).toBe(false);
    expect(out.properties.primary.unevaluatedProperties).toBe(false);
    expect(out.properties.secondary.unevaluatedProperties).toBe(false);
    expect("additionalProperties" in out.$defs.Address).toBe(false);
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

  test("closes anyOf at the shared evaluation boundary", () => {
    const out = applyEnforcedExtras({
      anyOf: [{ type: "object", properties: { a: { type: "string" } } }, { type: "null" }],
    }) as { anyOf: Schema[]; unevaluatedProperties: unknown };
    expect("additionalProperties" in (out.anyOf[0] as Schema)).toBe(false);
    expect(out.unevaluatedProperties).toBe(false);
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

  test("matches the shared language-neutral vectors", () => {
    for (const vector of enforcementVectors) {
      expect({ id: vector.id, output: applyEnforcedExtras(vector.input) }).toEqual({
        id: vector.id,
        output: vector.expected,
      });
    }
  });

  test("returns stable unsupported failures for unsafe overlays", () => {
    for (const vector of sharedEnforcementVectors.enforcement_unsupported) {
      try {
        applyEnforcedExtras(vector.input);
        throw new Error(`expected ${vector.id} to be unsupported`);
      } catch (error) {
        expect(error).toBeInstanceOf(EnforcementUnsupportedError);
        const unsupported = error as EnforcementUnsupportedError;
        expect({
          id: vector.id,
          message: unsupported.message,
          schema_path: unsupported.schemaPath,
        }).toEqual({
          id: vector.id,
          message: ENFORCEMENT_UNSUPPORTED_MESSAGE,
          schema_path: vector.schema_path,
        });
      }
    }
  });

  test("enforces the shared instance vectors", () => {
    const schemas = new Map(enforcementVectors.map((vector) => [vector.id, vector.input]));
    for (const vector of sharedEnforcementVectors.enforcement_validation) {
      const schema = schemas.get(vector.enforcement_id);
      if (schema === undefined) throw new Error(`missing schema vector ${vector.enforcement_id}`);
      const validate = new Ajv2020({ strict: false }).compile(applyEnforcedExtras(schema));
      expect({
        id: vector.enforcement_id,
        invalid: vector.invalid.map((value) => validate(value)),
        valid: vector.valid.map((value) => validate(value)),
      }).toEqual({
        id: vector.enforcement_id,
        invalid: vector.invalid.map(() => false),
        valid: vector.valid.map(() => true),
      });
    }
  });

  test("reports a missing reference before checking enforcement support", () => {
    const result = validateStructural(
      {},
      { $ref: "https://example.com/missing.schema.json" },
      { strictExtras: true },
    );
    expect(result.errors[0]).toEqual({
      kind: "schema_invalid",
      message: "compiled schema reference is unavailable offline",
      reason: "reference",
      reference: "https://example.com/missing.schema.json",
      schema_path: "/$ref",
    });
  });

  test("returns enforcement_unsupported for an available external reference", () => {
    const uri = "https://example.com/external.schema.json";
    const result = validateStructural(
      {},
      { $ref: uri },
      {
        resources: {
          [uri]: { $id: uri, type: "object", properties: { name: { type: "string" } } },
        },
        strictExtras: true,
      },
    );
    expect(result.errors).toEqual([
      {
        kind: "enforcement_unsupported",
        message: ENFORCEMENT_UNSUPPORTED_MESSAGE,
        schema_path: "/$ref",
      },
    ]);
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
    const structural = result.output.structural as { errors: { kind: string; message: string }[] };
    expect(structural.errors[0]?.kind).toBe("envelope_ambiguous");
    expect(structural.errors[0]?.message).toContain("name");
  });

  test("zero-key root without envelopeKey is envelope_missing", () => {
    const doc = tmpDoc("doc.md", "---\nsoftschema:\n  contract: t:X/v1\n---\nbody\n");
    const result = validateArtifact(doc, mkContract());
    const structural = result.output.structural as { errors: { kind: string }[] };
    expect(structural.errors[0]?.kind).toBe("envelope_missing");
  });
});

describe("pure-yaml metadata rules", () => {
  test("the softschema block is metadata, not payload", () => {
    const doc = tmpDoc("doc.yaml", "softschema:\n  contract: t:X/v1\nname: hello\ncount: 1\n");
    const result = validateArtifact(doc, mkContract({ profile: "pure-yaml" }));
    expect(result.ok).toBe(true);
    expect(result.output.values).toEqual({ name: "hello", count: 1 });
    expect(result.output.document_metadata).toEqual({
      contract: "t:X/v1",
      envelope: null,
      schema: null,
      status: null,
    });
  });

  test("a contract mismatch in the block is detected", () => {
    const doc = tmpDoc("doc.yaml", "softschema:\n  contract: t:X/v1\nname: hello\n");
    const result = validateArtifact(doc, mkContract({ id: "other:Y/v1", profile: "pure-yaml" }));
    const structural = result.output.structural as { errors: { kind: string }[] };
    expect(structural.errors[0]?.kind).toBe("document_contract_mismatch");
  });

  test("an explicit envelopeKey nests the payload", () => {
    const doc = tmpDoc("doc.yaml", "softschema:\n  contract: t:X/v1\npayload:\n  name: hi\n");
    const result = validateArtifact(
      doc,
      mkContract({ profile: "pure-yaml", envelopeKey: "payload" }),
    );
    expect(result.ok).toBe(true);
    expect(result.output.values).toEqual({ name: "hi" });
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
    expect(result.output.values).toEqual({ name: "hi" });
  });
});
