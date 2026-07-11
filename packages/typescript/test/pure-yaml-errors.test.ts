/**
 * Pure-YAML malformed-YAML path: validateArtifact with a pure-yaml profile contract
 * on a file containing invalid YAML must return a structural result with kind
 * `parse_error` (not throw).
 */
import { afterEach, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { Contract } from "../src/models.js";
import { validateArtifact } from "../src/validate.js";

let tempDir: string;
function makeTempDir(): string {
  tempDir = mkdtempSync(join(tmpdir(), "softschema-pureyaml-test-"));
  return tempDir;
}

afterEach(() => {
  if (tempDir) {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

function pureYamlContract(schemaPath: string | null = null): Contract {
  return {
    id: "test:PureYaml/v1",
    model: null,
    envelopeKey: null,
    status: "soft",
    profile: "pure-yaml",
    schemaPath,
  };
}

describe("pure-yaml malformed YAML", () => {
  test("invalid YAML returns yaml_parse_error structural result", () => {
    const dir = makeTempDir();
    const yamlFile = join(dir, "bad.yaml");
    writeFileSync(yamlFile, "foo: [unclosed\nbar: 1\n");
    const contract = pureYamlContract();
    const result = validateArtifact(yamlFile, contract);
    expect(result.ok).toBe(false);
    const structural = result.output.structural as {
      ok: boolean;
      errors: { kind: string; message: string }[];
    };
    expect(structural.ok).toBe(false);
    expect(structural.errors.length).toBeGreaterThan(0);
    expect(structural.errors[0]!.kind).toBe("yaml_parse_error");
  });

  test("nonexistent YAML file returns artifact_unreadable", () => {
    const dir = makeTempDir();
    const yamlFile = join(dir, "does-not-exist.yaml");
    const contract = pureYamlContract();
    const result = validateArtifact(yamlFile, contract);
    expect(result.ok).toBe(false);
    const structural = result.output.structural as {
      ok: boolean;
      errors: { kind: string; message: string }[];
    };
    expect(structural.ok).toBe(false);
    expect(structural.errors[0]!.kind).toBe("artifact_unreadable");
  });

  test("valid pure-YAML file validates without errors", () => {
    const dir = makeTempDir();
    const yamlFile = join(dir, "good.yaml");
    writeFileSync(yamlFile, "title: hello\ncount: 42\n");
    const contract = pureYamlContract();
    const result = validateArtifact(yamlFile, contract);
    expect(result.ok).toBe(true);
  });
});
