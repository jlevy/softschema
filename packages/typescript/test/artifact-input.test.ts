import { expect, test } from "bun:test";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import type { Contract } from "../src/models.js";
import { artifactErrorRecord, readFrontmatter, validateArtifact } from "../src/validate.js";

interface Vector {
  id: string;
  profile: "frontmatter-md" | "pure-yaml";
  content: string;
  reason: string;
  message: string;
  path?: string;
}

const ROOT = resolve(import.meta.dir, "../../..");
const CLI = resolve(ROOT, "packages/typescript/src/cli.ts");
const VECTORS = JSON.parse(
  readFileSync(resolve(ROOT, "tests/parity/artifact-input.json"), "utf8"),
) as Vector[];

function contract(profile: Contract["profile"]): Contract {
  return {
    id: "example:Value/v1",
    model: null,
    envelopeKey: null,
    status: "soft",
    profile,
    schemaPath: null,
  };
}

function tempPath(name: string): string {
  return join(mkdtempSync(join(tmpdir(), "softschema-input-")), name);
}

test.each(VECTORS)("artifact parse vector $id is stable", (vector) => {
  const source = tempPath(vector.profile === "frontmatter-md" ? "artifact.md" : "artifact.yaml");
  writeFileSync(source, vector.content, "utf8");

  const result = validateArtifact(source, contract(vector.profile));
  const expected: Record<string, unknown> = {
    kind: "parse_error",
    reason: vector.reason,
    message: vector.message,
    source,
  };
  if (vector.path !== undefined) expected.path = vector.path;
  expect((result.output.structural as { errors: unknown[] }).errors).toEqual([expected]);
  expect((result.output.semantic as { skipped_reason: string }).skipped_reason).toBe("parse_error");
});

test.each([
  ["missing.md", "not_found", "artifact path does not exist"],
  ["directory", "directory_requires_recursive", "artifact directory requires --recursive"],
] as const)("artifact access record %s is stable", (name, reason, message) => {
  const source = tempPath(name);
  if (reason === "directory_requires_recursive") mkdirSync(source);

  const result = validateArtifact(source, contract("frontmatter-md"));

  expect((result.output.structural as { errors: unknown[] }).errors).toEqual([
    { kind: "input_error", reason, message, source },
  ]);
  expect((result.output.semantic as { skipped_reason: string }).skipped_reason).toBe("input_error");
});

test.each([
  "frontmatter-delimiter",
  "frontmatter-syntax",
  "frontmatter-list-root",
  "frontmatter-value-domain",
  "pure-yaml-syntax",
  "pure-yaml-list-root",
])("validate CLI emits discriminated parse record for %s", (vectorId) => {
  const vector = VECTORS.find((item) => item.id === vectorId) as Vector;
  const directory = mkdtempSync(join(tmpdir(), "softschema-input-cli-"));
  const source = join(directory, vector.profile === "frontmatter-md" ? "artifact.md" : "artifact.yaml");
  writeFileSync(source, vector.content, "utf8");

  const child = Bun.spawnSync({
    cmd: [
      process.execPath,
      CLI,
      "validate",
      source,
      "--profile",
      vector.profile,
      "--contract",
      "example:Value/v1",
    ],
    stderr: "pipe",
    stdout: "pipe",
  });

  expect(child.exitCode).toBe(1);
  expect(child.stderr.toString()).toBe("");
  const record = JSON.parse(child.stdout.toString()) as Record<string, unknown>;
  expect(record.kind).toBe("parse_error");
  expect(record.reason).toBe(vector.reason);
  expect(record.message).toBe(vector.message);
  expect(record.source).toBe(source);
  expect(record.line).toBeUndefined();
  expect(record.column).toBeUndefined();
});

test("validate CLI emits input_error and exit two", () => {
  const source = tempPath("missing.md");

  const child = Bun.spawnSync({
    cmd: [process.execPath, CLI, "validate", source, "--contract", "example:Value/v1"],
    stderr: "pipe",
    stdout: "pipe",
  });

  expect(child.exitCode).toBe(2);
  expect(child.stderr.toString()).toBe("");
  expect(JSON.parse(child.stdout.toString())).toEqual({
    kind: "input_error",
    reason: "not_found",
    message: "artifact path does not exist",
    source,
  });
});

test("artifact error normalizer retains locations for diagnostics", () => {
  const source = tempPath("syntax.md");
  writeFileSync(source, "---\nitem: [unclosed\n---\n", "utf8");

  try {
    readFrontmatter(source);
    throw new Error("expected syntax failure");
  } catch (error) {
    const record = artifactErrorRecord(source, error, { includeLocation: true });
    expect(record).toMatchObject({ reason: "syntax" });
    expect(typeof record?.line).toBe("number");
    expect(typeof record?.column).toBe("number");
  }
});

test("frontmatter limit locations include the document offset", () => {
  const source = tempPath("limit.md");
  writeFileSync(source, "---\nx: too\n---\n", "utf8");

  try {
    readFrontmatter(source, { maxScalarCodePoints: 2 });
    throw new Error("expected scalar limit failure");
  } catch (error) {
    const record = artifactErrorRecord(source, error, { includeLocation: true });
    expect(record).toMatchObject({
      reason: "value_domain",
      path: "/x",
      line: 2,
      column: 4,
    });
  }
});

test("artifact error normalizer covers unreadable and invalid UTF-8", () => {
  const source = tempPath("artifact.md");
  expect(artifactErrorRecord(source, Object.assign(new Error("platform prose"), { code: "EACCES" }))).toEqual({
    kind: "input_error",
    reason: "unreadable",
    message: "artifact path cannot be read",
    source,
  });

  writeFileSync(source, Uint8Array.from([0x2d, 0x2d, 0x2d, 0x0a, 0xff, 0x0a]));
  const result = validateArtifact(source, contract("frontmatter-md"));
  expect((result.output.structural as { errors: unknown[] }).errors).toEqual([
    {
      kind: "parse_error",
      reason: "syntax",
      message: "artifact is not valid YAML",
      source,
    },
  ]);
});
