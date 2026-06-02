import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { z } from "zod";
import type { Contract } from "./models.js";
import { validateArtifact, validateValues } from "./validate.js";

const Sample = z.strictObject({ name: z.string(), count: z.int().min(0) });
const SAMPLE_SCHEMA = z.toJSONSchema(Sample) as Record<string, unknown>;

function tmpFile(name: string, content: string): string {
  const dir = mkdtempSync(join(tmpdir(), "softschema-vx-"));
  const path = join(dir, name);
  writeFileSync(path, content);
  return path;
}

function contract(overrides: Partial<Contract> = {}): Contract {
  return {
    id: "x:Sample/v1",
    model: null,
    envelopeKey: null,
    status: "soft",
    profile: "frontmatter-md",
    schemaPath: null,
    ...overrides,
  };
}

describe("validateValues", () => {
  test("requires a model or schema", () => {
    expect(() => validateValues({ name: "a" })).toThrow("requires at least one");
  });
  test("runs structural + semantic", () => {
    const r = validateValues({ name: "hi", count: 1 }, { model: Sample, schema: SAMPLE_SCHEMA });
    expect(r.structural.ok).toBe(true);
    expect(r.semantic.ok).toBe(true);
  });
  test("reports a structural failure", () => {
    const r = validateValues({ name: "hi", count: -1 }, { schema: SAMPLE_SCHEMA });
    expect(r.structural.ok).toBe(false);
    expect(r.structural.errors[0]?.validator).toBe("minimum");
  });
});

describe("validateArtifact: pure-yaml profile", () => {
  test("validates the YAML root as the payload", () => {
    const doc = tmpFile("sample.yaml", "name: hello\ncount: 3\n");
    const result = validateArtifact(doc, contract({ profile: "pure-yaml", model: "Sample" }), {
      semanticModel: Sample,
    });
    expect(result.ok).toBe(true);
    expect(result.output.profile).toBe("pure-yaml");
    expect(result.output.values).toEqual({ name: "hello", count: 3 });
  });
  test("non-mapping YAML root is yaml_not_mapping", () => {
    const doc = tmpFile("bad.yaml", "- a\n- b\n");
    const result = validateArtifact(doc, contract({ profile: "pure-yaml" }), { semanticModel: Sample });
    expect(result.ok).toBe(false);
    const err = result.output.structural as { errors: { kind: string }[] };
    expect(err.errors[0]?.kind).toBe("yaml_not_mapping");
  });
});

describe("validateArtifact: frontmatter_not_mapping", () => {
  test("frontmatter that parses to a non-mapping is rejected", () => {
    const doc = tmpFile("doc.md", "---\n- a\n- b\n---\nbody\n");
    const result = validateArtifact(doc, contract({ envelopeKey: "sample" }));
    expect(result.ok).toBe(false);
    const err = result.output.structural as { errors: { kind: string }[] };
    expect(err.errors[0]?.kind).toBe("frontmatter_not_mapping");
  });
});
