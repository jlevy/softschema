import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as yamlParse } from "yaml";
import { z } from "zod";
import type { Contract } from "./models.js";
import {
  readFrontmatter,
  validateArtifact,
  validateStructural,
  validateValues,
  YamlParseError,
} from "./validate.js";

const Sample = z.strictObject({ name: z.string(), count: z.int().min(0) });
const SAMPLE_SCHEMA = z.toJSONSchema(Sample) as Record<string, unknown>;
const HARDENING_VECTORS = join(import.meta.dir, "../../../tests/vectors/hardening.yaml");

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
    expect(result.profile).toBe("pure-yaml");
    expect(result.values).toEqual({ name: "hello", count: 3 });
  });
  test("non-mapping YAML root is yaml_not_mapping", () => {
    const doc = tmpFile("bad.yaml", "- a\n- b\n");
    const result = validateArtifact(doc, contract({ profile: "pure-yaml" }), {
      semanticModel: Sample,
    });
    expect(result.ok).toBe(false);
    const err = result.structural as { errors: { kind: string }[] };
    expect(err.errors[0]?.kind).toBe("yaml_not_mapping");
  });
});

describe("validateArtifact: frontmatter_not_mapping", () => {
  test("a pre-parsed non-mapping frontmatter is rejected as frontmatter_not_mapping", () => {
    // Reading a non-mapping document from disk is a parse_error (see the ss-7cbb tests
    // below, matching Python's fmf_read). The frontmatter_not_mapping kind is reached
    // only when a caller supplies an already-parsed non-mapping value (Python parity:
    // validate_artifact(..., frontmatter=[...]) → frontmatter_not_mapping).
    const doc = tmpFile("doc.md", "---\n- a\n- b\n---\nbody\n");
    const result = validateArtifact(doc, contract({ envelopeKey: "sample" }), {
      preParsed: { hasFence: true, value: [1, 2, 3] },
    });
    expect(result.ok).toBe(false);
    const err = result.structural as { errors: { kind: string }[] };
    expect(err.errors[0]?.kind).toBe("frontmatter_not_mapping");
  });
});

describe("compiled schema invalid root", () => {
  test("scalar YAML root in the compiled schema yields schema_invalid", () => {
    const compiledSchema = tmpFile("schema.yaml", "just a string\n");
    const doc = tmpFile("doc.md", "---\nsample:\n  name: hi\n---\nbody\n");
    const result = validateArtifact(doc, contract({ schemaPath: compiledSchema }));
    expect(result.ok).toBe(false);
    const error = result.structural.errors[0] as Record<string, unknown>;
    expect(result.structural.ok).toBe(false);
    expect(error.kind).toBe("schema_invalid");
    expect(error.message).toContain("str");
    expect(error.message).toContain("expected mapping");
    expect(error.reason).toBe("syntax");
  });

  test("array YAML root in the compiled schema yields schema_invalid", () => {
    const compiledSchema = tmpFile("schema.yaml", "- a\n- b\n");
    const doc = tmpFile("doc.md", "---\nsample:\n  name: hi\n---\nbody\n");
    const result = validateArtifact(doc, contract({ schemaPath: compiledSchema }));
    expect(result.ok).toBe(false);
    const error = result.structural.errors[0] as Record<string, unknown>;
    expect(result.structural.ok).toBe(false);
    expect(error.kind).toBe("schema_invalid");
    expect(error.message).toContain("list");
    expect(error.message).toContain("expected mapping");
    expect(error.reason).toBe("syntax");
  });

  test("malformed compiled YAML includes a stable schema_invalid reason", () => {
    const compiledSchema = tmpFile("schema.yaml", "type: [\n");
    const doc = tmpFile("doc.md", "---\nsample:\n  name: hi\n---\nbody\n");
    const result = validateArtifact(doc, contract({ schemaPath: compiledSchema }));
    expect(result.structural.errors[0]).toMatchObject({
      kind: "schema_invalid",
      reason: "syntax",
    });
  });
});

describe("validateArtifact: missing/unreadable document file", () => {
  test("nonexistent frontmatter-md file returns an input error", () => {
    const missingPath = "/tmp/softschema-nonexistent-doc-12345.md";
    const result = validateArtifact(missingPath, contract());
    expect(result.ok).toBe(false);
    const structural = result.structural as { ok: boolean; errors: { kind: string }[] };
    expect(structural.ok).toBe(false);
    expect(structural.errors[0]?.kind).toBe("artifact_unreadable");
  });

  test("nonexistent pure-yaml file returns an input error", () => {
    const missingPath = "/tmp/softschema-nonexistent-doc-12345.yaml";
    const result = validateArtifact(missingPath, contract({ profile: "pure-yaml" }));
    expect(result.ok).toBe(false);
    const structural = result.structural as { ok: boolean; errors: { kind: string }[] };
    expect(structural.ok).toBe(false);
    expect(structural.errors[0]?.kind).toBe("artifact_unreadable");
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

  test("validateArtifact returns yaml_parse_error for non-mapping frontmatter", () => {
    const doc = tmpFile("doc.md", "---\n- a\n- b\n---\nbody\n");
    const result = validateArtifact(doc, contract());
    expect(result.ok).toBe(false);
    const structural = result.structural as { ok: boolean; errors: { kind: string }[] };
    expect(structural.errors[0]?.kind).toBe("yaml_parse_error");
  });
});

test("shared portable YAML and artifact-input vectors", () => {
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  const portableContract = contract({ profile: "pure-yaml" });
  for (const item of vectors.portable_values ?? []) {
    const text =
      item.generated === "deep_sequence"
        ? `value: ${"[".repeat(1_000)}0${"]".repeat(1_000)}`
        : String(item.text);
    const path = tmpFile(`${String(item.id)}.yaml`, text);
    const result = validateArtifact(path, portableContract);
    expect(result.ok).toBe(item.valid as boolean);
    if (!item.valid) {
      const structural = result.structural as { errors: { kind: string }[] };
      expect(structural.errors[0]?.kind).toBe(item.code as string);
    }
  }
  for (const item of vectors.artifact_input ?? []) {
    const path = join(mkdtempSync(join(tmpdir(), "softschema-input-")), `${String(item.id)}.yaml`);
    if (item.source === "invalid_utf8") writeFileSync(path, Buffer.from([0xff]));
    if (item.source === "too_large") writeFileSync(path, Buffer.alloc(1_048_577, 0x78));
    if (item.text !== undefined) writeFileSync(path, String(item.text));
    const result = validateArtifact(path, portableContract);
    const structural = result.structural as { errors: { kind: string }[] };
    expect(result.outcome).toBe(item.outcome as typeof result.outcome);
    expect(structural.errors[0]?.kind).toBe(item.code as string);
  }
});

test("shared structural vectors", () => {
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<Record<string, unknown>>
  >;
  for (const item of vectors.structural ?? []) {
    const result = validateStructural(item.value, item.schema as Record<string, unknown>, {
      resources: item.resources as Record<string, Record<string, unknown>> | undefined,
    });
    expect(result.ok).toBe(item.valid as boolean);
    if (!item.valid) expect(result.errors[0]?.kind).toBe(item.code as string);
  }
});
