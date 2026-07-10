import { expect, test } from "bun:test";
import { readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { metadataToOutput, parseSchemaMetadata } from "./models.js";
import { validateArtifact } from "./validate.js";

interface Vector {
  id: string;
  raw: unknown;
  output?: Record<string, unknown>;
  error?: boolean;
}

const ROOT = resolve(import.meta.dir, "../../..");
const VECTORS = JSON.parse(
  readFileSync(resolve(ROOT, "tests/parity/artifact-format.json"), "utf8"),
) as Vector[];

test.each(VECTORS)("artifact format vector $id", (vector) => {
  if (vector.error === true) {
    expect(() => parseSchemaMetadata(vector.raw), vector.id).toThrow();
    return;
  }

  expect(metadataToOutput(parseSchemaMetadata(vector.raw)), vector.id).toEqual(
    vector.output as Record<string, unknown>,
  );
});

test("format 1 extensions round-trip through artifact validation", () => {
  const artifact = resolve(import.meta.dir, ".tmp-format-1-artifact.md");
  writeFileSync(
    artifact,
    "---\n" +
      "softschema:\n" +
      '  format: "1"\n' +
      "  contract: example.docs:Record/v1\n" +
      "  extensions:\n" +
      "    com.example.review:\n" +
      "      labels: [ready, 2, null]\n" +
      "record:\n" +
      "  title: Example\n" +
      "---\n",
    "utf8",
  );
  try {
    const result = validateArtifact(artifact, {
      id: "example.docs:Record/v1",
      model: null,
      envelopeKey: "record",
      status: "soft",
      profile: "frontmatter-md",
      schemaPath: null,
    });

    expect(result.ok).toBe(true);
    expect((result.output.document_metadata as Record<string, unknown>).extensions).toEqual({
      "com.example.review": { labels: ["ready", 2, null] },
    });
  } finally {
    unlinkSync(artifact);
  }
});

test("duplicate extension namespaces fail at the portable YAML boundary", () => {
  const artifact = resolve(import.meta.dir, ".tmp-duplicate-extension.md");
  writeFileSync(
    artifact,
    "---\n" +
      "softschema:\n" +
      '  format: "1"\n' +
      "  contract: example.docs:Record/v1\n" +
      "  extensions:\n" +
      "    com.example.review: first\n" +
      "    com.example.review: second\n" +
      "record:\n" +
      "  title: Example\n" +
      "---\n",
    "utf8",
  );
  try {
    const result = validateArtifact(artifact, {
      id: "example.docs:Record/v1",
      model: null,
      envelopeKey: "record",
      status: "soft",
      profile: "frontmatter-md",
      schemaPath: null,
    });

    expect((result.output.structural as { errors: unknown[] }).errors).toEqual([
      {
        kind: "parse_error",
        reason: "value_domain",
        message: "artifact contains a non-portable YAML value",
        source: artifact,
        path: "/softschema/extensions/com.example.review",
      },
    ]);
  } finally {
    unlinkSync(artifact);
  }
});

test("materialized extension values must be portable", () => {
  const cyclic: Record<string, unknown> = {};
  cyclic.self = cyclic;

  expect(() =>
    parseSchemaMetadata({
      format: "1",
      contract: "example.docs:Record/v1",
      extensions: { "com.example.review": cyclic },
    }),
  ).toThrow("softschema metadata extensions are not portable");
});
