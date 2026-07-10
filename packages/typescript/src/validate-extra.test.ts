import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { z } from "zod";
import type { Contract } from "./models.js";
import { readFrontmatter, validateArtifact, validateValues, YamlParseError } from "./validate.js";

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
  test("non-mapping YAML root is a root parse error", () => {
    const doc = tmpFile("bad.yaml", "- a\n- b\n");
    const result = validateArtifact(doc, contract({ profile: "pure-yaml" }), {
      semanticModel: Sample,
    });
    expect(result.ok).toBe(false);
    const err = result.output.structural as { errors: { kind: string }[] };
    expect(err.errors[0]).toMatchObject({ kind: "parse_error", reason: "root" });
  });
});

describe("validateArtifact: non-mapping frontmatter", () => {
  test("a pre-parsed non-mapping frontmatter is rejected as a root parse error", () => {
    // Reading a non-mapping document from disk is a parse_error (see the ss-7cbb tests
    // below, matching Python's fmf_read). The frontmatter_not_mapping kind is reached
    // only when a caller supplies an already-parsed non-mapping value (Python parity:
    // validate_artifact(..., frontmatter=[...]) → frontmatter_not_mapping).
    const doc = tmpFile("doc.md", "---\n- a\n- b\n---\nbody\n");
    const result = validateArtifact(doc, contract({ envelopeKey: "sample" }), {
      preParsed: { hasFence: true, value: [1, 2, 3] },
    });
    expect(result.ok).toBe(false);
    const err = result.output.structural as { errors: { kind: string }[] };
    expect(err.errors[0]).toMatchObject({ kind: "parse_error", reason: "root" });
  });
});

describe("validateArtifact: missing/unreadable document file", () => {
  test("nonexistent frontmatter-md file returns input_error, does not throw", () => {
    const missingPath = "/tmp/softschema-nonexistent-doc-12345.md";
    const result = validateArtifact(missingPath, contract());
    expect(result.ok).toBe(false);
    const structural = result.output.structural as { ok: boolean; errors: { kind: string }[] };
    expect(structural.ok).toBe(false);
    expect(structural.errors[0]).toMatchObject({ kind: "input_error", reason: "not_found" });
  });

  test("nonexistent pure-yaml file returns input_error, does not throw", () => {
    const missingPath = "/tmp/softschema-nonexistent-doc-12345.yaml";
    const result = validateArtifact(missingPath, contract({ profile: "pure-yaml" }));
    expect(result.ok).toBe(false);
    const structural = result.output.structural as { ok: boolean; errors: { kind: string }[] };
    expect(structural.ok).toBe(false);
    expect(structural.errors[0]).toMatchObject({ kind: "input_error", reason: "not_found" });
  });
});

describe("non-mapping frontmatter is rejected per entrypoint (ss-7cbb)", () => {
  test("readFrontmatter throws YamlParseError on a list frontmatter", () => {
    const doc = tmpFile("doc.md", "---\n- a\n- b\n---\nbody\n");
    expect(() => readFrontmatter(doc)).toThrow(YamlParseError);
    expect(() => readFrontmatter(doc)).toThrow("got <class 'list'>");
  });

  test("readFrontmatter throws YamlParseError on a scalar frontmatter", () => {
    const doc = tmpFile("doc.md", "---\njust a string\n---\nbody\n");
    expect(() => readFrontmatter(doc)).toThrow(YamlParseError);
    expect(() => readFrontmatter(doc)).toThrow("got <class 'str'>");
  });

  test("validateArtifact returns parse_error for non-mapping frontmatter", () => {
    const doc = tmpFile("doc.md", "---\n- a\n- b\n---\nbody\n");
    const result = validateArtifact(doc, contract());
    expect(result.ok).toBe(false);
    const structural = result.output.structural as { ok: boolean; errors: { kind: string }[] };
    expect(structural.errors[0]?.kind).toBe("parse_error");
  });
});
