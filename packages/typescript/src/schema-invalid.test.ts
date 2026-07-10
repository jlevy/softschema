import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { z } from "zod";
import type { Contract } from "./models.js";
import { validateArtifact, validateStructural, validateValues } from "./validate.js";

const JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema";
const NameModel = z.strictObject({ name: z.string() });

function tempFile(name: string, content: string): string {
  const directory = mkdtempSync(join(tmpdir(), "softschema-schema-invalid-"));
  const path = join(directory, name);
  writeFileSync(path, content);
  return path;
}

function contract(schemaPath: string): Contract {
  return {
    id: "example:Name/v1",
    model: null,
    envelopeKey: "item",
    status: "soft",
    profile: "frontmatter-md",
    schemaPath,
  };
}

function validateFile(schemaText: string) {
  const schemaPath = tempFile("schema.yaml", schemaText);
  const artifact = tempFile("artifact.md", "---\nitem:\n  name: Ada\n---\n");
  const result = validateArtifact(artifact, contract(schemaPath));
  return (result.output.structural as { errors: Record<string, unknown>[] }).errors;
}

describe("stable schema_invalid results", () => {
  test("normalizes malformed syntax and every non-mapping root", () => {
    const cases: [string, Record<string, unknown>][] = [
      [
        "properties: [\n",
        {
          kind: "schema_invalid",
          reason: "syntax",
          message: "compiled schema is not valid YAML or JSON",
          schema_path: "",
        },
      ],
      [
        "null\n",
        {
          kind: "schema_invalid",
          reason: "root",
          message: "compiled schema root must be a mapping",
          schema_path: "",
        },
      ],
      [
        "- one\n- two\n",
        {
          kind: "schema_invalid",
          reason: "root",
          message: "compiled schema root must be a mapping",
          schema_path: "",
        },
      ],
      [
        "scalar\n",
        {
          kind: "schema_invalid",
          reason: "root",
          message: "compiled schema root must be a mapping",
          schema_path: "",
        },
      ],
    ];

    for (const [schema, expected] of cases) {
      expect(validateFile(schema)).toEqual([expected]);
    }
  });

  test("normalizes dialect, metaschema, compile, and reference failures", () => {
    const cases: [string, Record<string, unknown>][] = [
      [
        "$schema: http://json-schema.org/draft-07/schema#\ntype: object\n",
        {
          kind: "schema_invalid",
          reason: "dialect",
          message: "compiled schema uses an unsupported JSON Schema dialect",
          schema_path: "/$schema",
          dialect: "http://json-schema.org/draft-07/schema#",
        },
      ],
      [
        "$schema: 42\ntype: object\n",
        {
          kind: "schema_invalid",
          reason: "metaschema",
          message: "compiled schema does not conform to Draft 2020-12",
          schema_path: "/$schema",
        },
      ],
      [
        `$schema: ${JSON_SCHEMA_2020_12}\ntype: 42\n`,
        {
          kind: "schema_invalid",
          reason: "metaschema",
          message: "compiled schema does not conform to Draft 2020-12",
          schema_path: "/type",
        },
      ],
      [
        `$schema: ${JSON_SCHEMA_2020_12}\n$defs:\n  a/b~c:\n    type: 42\ntype: object\n`,
        {
          kind: "schema_invalid",
          reason: "metaschema",
          message: "compiled schema does not conform to Draft 2020-12",
          schema_path: "/$defs/a~1b~0c/type",
        },
      ],
      [
        `$schema: ${JSON_SCHEMA_2020_12}\ntype: string\npattern: '['\n`,
        {
          kind: "schema_invalid",
          reason: "compile",
          message: "compiled schema could not be compiled",
          schema_path: "/pattern",
        },
      ],
      [
        `$schema: ${JSON_SCHEMA_2020_12}\n$defs:\n  cycle: &cycle\n    type: object\n    properties:\n      child: *cycle\ntype: object\n`,
        {
          kind: "schema_invalid",
          reason: "compile",
          message: "compiled schema could not be compiled",
          schema_path: "/$defs/cycle/properties/child",
        },
      ],
      [
        `$schema: ${JSON_SCHEMA_2020_12}\n$ref: https://schemas.example/missing\n`,
        {
          kind: "schema_invalid",
          reason: "reference",
          message: "compiled schema reference is unavailable offline",
          schema_path: "/$ref",
          reference: "https://schemas.example/missing",
        },
      ],
      [
        `$schema: ${JSON_SCHEMA_2020_12}\n$ref: '#/$defs/missing'\n`,
        {
          kind: "schema_invalid",
          reason: "reference",
          message: "compiled schema reference is unavailable offline",
          schema_path: "/$ref",
          reference: "#/$defs/missing",
        },
      ],
    ];

    for (const [schema, expected] of cases) {
      expect(validateFile(schema)).toEqual([expected]);
    }
  });

  test("preserves legacy identity and validates supplied resources through one loader", () => {
    const legacy = {
      $schema: JSON_SCHEMA_2020_12,
      $id: "example:Name/v1",
      type: "object",
      properties: { name: { type: "string" } },
      "x-softschema": { contract: "example:Name/v1" },
    };
    expect(validateStructural({ name: "Ada" }, legacy).ok).toBe(true);

    const mismatch = {
      ...legacy,
      $id: "example:Wrong/v1",
    };
    expect(validateStructural({}, mismatch).errors).toEqual([
      {
        kind: "schema_invalid",
        reason: "profile",
        message: "compiled schema is outside the softschema profile",
        schema_path: "/$id",
        detail: "legacy_contract_id_mismatch",
      },
    ]);

    const root = {
      $schema: JSON_SCHEMA_2020_12,
      $ref: "https://schemas.example/name",
    };
    const resources = {
      "https://schemas.example/name": {
        $schema: JSON_SCHEMA_2020_12,
        type: "object",
        required: ["name"],
        properties: { name: { type: "string" } },
      },
    };
    expect(validateStructural({ name: "Ada" }, root, { resources }).ok).toBe(true);

    const invalidResources = {
      "https://schemas.example/name": {
        $schema: JSON_SCHEMA_2020_12,
        type: 42,
      },
    };
    expect(validateStructural({}, root, { resources: invalidResources }).errors).toEqual([
      {
        kind: "schema_invalid",
        reason: "metaschema",
        message: "compiled schema does not conform to Draft 2020-12",
        schema_path: "/type",
      },
    ]);

    const mismatchedResources = {
      "https://schemas.example/name": {
        $schema: JSON_SCHEMA_2020_12,
        $id: "https://schemas.example/other",
        type: "object",
      },
    };
    expect(validateStructural({}, root, { resources: mismatchedResources }).errors).toEqual([
      {
        kind: "schema_invalid",
        reason: "identity",
        message: "compiled schema resource identity is invalid",
        schema_path: "/$id",
        detail: "resource_id_mismatch",
      },
    ]);
  });

  test("runs the trusted semantic model independently of schema compilation", () => {
    const result = validateValues({ name: "Ada" }, { model: NameModel, schema: { type: 42 } });

    expect(result.structural.ok).toBe(false);
    expect(result.semantic.ok).toBe(true);
  });
});
