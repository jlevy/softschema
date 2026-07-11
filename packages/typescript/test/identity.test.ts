import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { parse as yamlParse } from "yaml";
import { z } from "zod";
import { buildCanonicalSchema } from "../src/compile.js";
import {
  Contracts,
  SchemaView,
  compileSchema,
  defineContract,
  validateContractId,
  validateArtifact,
  validateSchemaId,
  validateStructural,
} from "../src/index.js";
import { loadYamlFixture } from "./yaml-fixture.js";

const Sample = z.strictObject({ name: z.string() });
const schemaIdVectors = loadYamlFixture<{ valid: string[]; invalid: string[] }>(
  join(import.meta.dir, "../../../tests/identity/schema-id-vectors.yaml"),
);
const nestedResourceVectors = loadYamlFixture<{
  schema_locations: string[];
  cases: Array<{
    id: string;
    schema: Record<string, unknown>;
    values: unknown;
    resources: Record<string, boolean | Record<string, unknown>>;
    expected: ReturnType<typeof validateStructural>;
  }>;
}>(join(import.meta.dir, "../../../tests/identity/nested-resource-vectors.yaml"));

function schemaAtLocation(pointer: string): Record<string, unknown> {
  const root: Record<string, unknown> = {};
  let current: Record<string, unknown> | unknown[] = root;
  const parts = pointer.replace(/^\//, "").split("/");
  for (const [index, part] of parts.entries()) {
    const last = index === parts.length - 1;
    const nextPart = last ? null : parts[index + 1];
    const value: Record<string, unknown> | unknown[] = last
      ? { $id: "child/" }
      : nextPart === "0"
        ? []
        : {};
    if (Array.isArray(current)) {
      if (part !== "0") throw new Error(`unsupported vector array index ${part}`);
      current.push(value);
    } else {
      current[part] = value;
    }
    current = value;
  }
  return root;
}

describe("contract identity", () => {
  test.each(["Name", "example.docs:Record/v1", "a_b:record/2026-07"])(
    "accepts %s at public boundaries",
    (contractId) => {
      expect(validateContractId(contractId)).toBe(contractId);
      expect(
        defineContract({
          id: contractId,
          model: null,
          envelopeKey: null,
          status: "soft",
          profile: "frontmatter-md",
          schemaPath: null,
        }).id,
      ).toBe(contractId);
    },
  );

  test.each(["", "bad id", "ns:", "a::B", "Name/v1/v2"])(
    "rejects %s in validators, registries, and compilers",
    (contractId) => {
      expect(() => validateContractId(contractId)).toThrow("contract ID");
      expect(() =>
        defineContract({
          id: contractId,
          model: null,
          envelopeKey: null,
          status: "soft",
          profile: "frontmatter-md",
          schemaPath: null,
        }),
      ).toThrow("contract ID");
      expect(() => new Contracts().resolve(contractId)).toThrow("contract ID");
      expect(() =>
        validateArtifact("must-not-be-read.md", {
          id: contractId,
          model: null,
          envelopeKey: null,
          status: "soft",
          profile: "frontmatter-md",
          schemaPath: null,
        }),
      ).toThrow("contract ID");
      expect(() => buildCanonicalSchema({} as z.ZodType, contractId)).toThrow("contract ID");
    },
  );

  test("registry identity is immutable after registration", () => {
    const input = {
      id: "example.docs:Record/v1",
      model: null,
      envelopeKey: null,
      status: "soft" as const,
      profile: "frontmatter-md" as const,
      schemaPath: null,
    };
    const registry = new Contracts();
    registry.register(input);

    input.id = "bad id";
    const stored = registry.resolve("example.docs:Record/v1");
    expect(stored?.id).toBe("example.docs:Record/v1");
    expect(Object.isFrozen(stored)).toBe(true);
  });
});

describe("compiled-schema identity", () => {
  test.each(schemaIdVectors.valid)("accepts canonical absolute identifier %s", (schemaId) => {
    expect(validateSchemaId(schemaId)).toBe(schemaId);
  });

  test.each(schemaIdVectors.invalid)(
    "rejects non-canonical identifier %s before generation or write",
    (schemaId) => {
      expect(() => validateSchemaId(schemaId)).toThrow("schema ID");
      expect(() =>
        buildCanonicalSchema({} as z.ZodType, "example.docs:Record/v1", schemaId),
      ).toThrow("schema ID");

      const out = join(mkdtempSync(join(tmpdir(), "softschema-identity-")), "must-not-exist.yaml");
      expect(() =>
        compileSchema({} as z.ZodType, out, {
          contractId: "example.docs:Record/v1",
          schemaId,
        }),
      ).toThrow("schema ID");
      expect(existsSync(out)).toBe(false);
    },
  );

  test("keeps logical contract and schema identity independent", () => {
    const out = join(mkdtempSync(join(tmpdir(), "softschema-identity-")), "schema.yaml");
    compileSchema(Sample, out, {
      contractId: "example.docs:Record/v1",
      schemaId: "https://schemas.example/softschema/record/v1",
    });

    const schema = yamlParse(readFileSync(out, "utf8")) as Record<string, unknown>;
    expect(schema.$id).toBe("https://schemas.example/softschema/record/v1");
    expect((schema["x-softschema"] as Record<string, unknown>).contract).toBe(
      "example.docs:Record/v1",
    );
  });

  test("does not derive $id from a logical contract ID", () => {
    const { schema } = buildCanonicalSchema(Sample, "example.docs:Record/v1");
    expect(schema.$id).toBeUndefined();
    expect((schema["x-softschema"] as Record<string, unknown>).contract).toBe(
      "example.docs:Record/v1",
    );
  });

  test("requires a contract before generation or write", () => {
    expect(() => buildCanonicalSchema({} as z.ZodType, null as unknown as string)).toThrow(
      "requires a contract ID",
    );
    const out = join(mkdtempSync(join(tmpdir(), "softschema-identity-")), "must-not-exist.yaml");
    expect(() =>
      compileSchema({} as z.ZodType, out, {} as Parameters<typeof compileSchema>[2]),
    ).toThrow("requires a contract ID");
    expect(existsSync(out)).toBe(false);
  });

  test("SchemaView never reports a schema URI as a contract ID", () => {
    const current = new SchemaView({ $id: "https://schemas.example/record/v1" });
    const legacy = new SchemaView({ $id: "example.docs:Record/v1" });

    expect(current.contractId).toBeNull();
    expect(current.schemaId).toBe("https://schemas.example/record/v1");
    expect(legacy.contractId).toBe("example.docs:Record/v1");
    expect(legacy.schemaId).toBeNull();
  });

  test.each(["relative/schema", "https://SCHEMAS.example/root", "urn:Example:root"])(
    "rejects invalid root schema identity %s",
    (schemaId) => {
      expect(
        validateStructural({}, {
          $schema: "https://json-schema.org/draft/2020-12/schema",
          $id: schemaId,
          type: "object",
        }).errors,
      ).toEqual([
        {
          kind: "schema_invalid",
          reason: "identity",
          message: "compiled schema resource identity is invalid",
          schema_path: "/$id",
          detail: "invalid_root_id",
        },
      ]);
    },
  );

  test("rejects an invalid supplied-resource registry key", () => {
    expect(
      validateStructural({}, { type: "object" }, { resources: { "relative/resource": true } })
        .errors,
    ).toEqual([
      {
        kind: "schema_invalid",
        reason: "identity",
        message: "compiled schema resource identity is invalid",
        schema_path: "",
        detail: "invalid_registry_key",
      },
    ]);
  });

  test.each(nestedResourceVectors.cases)("nested-resource vector $id", (vector) => {
    expect(
      validateStructural(vector.values, vector.schema, { resources: vector.resources }),
    ).toEqual(vector.expected);
  });

  test.each(nestedResourceVectors.schema_locations)(
    "indexes nested identities at schema-bearing location %s",
    (pointer) => {
      expect(validateStructural({}, schemaAtLocation(pointer)).errors).toEqual([
        {
          kind: "schema_invalid",
          reason: "identity",
          message: "compiled schema resource identity is invalid",
          schema_path: `${pointer}/$id`,
          detail: "invalid_nested_id",
        },
      ]);
    },
  );

  test("embedded resources count toward the exact resource limit", () => {
    const schemaWithNestedResources = (count: number): Record<string, unknown> => ({
      $schema: "https://json-schema.org/draft/2020-12/schema",
      $id: "https://schemas.example/root/",
      $defs: Object.fromEntries(
        Array.from({ length: count }, (_, index) => {
          const name = `resource${index.toString().padStart(3, "0")}`;
          return [name, { $id: name }];
        }),
      ),
      type: "object",
    });

    expect(
      validateStructural({}, schemaWithNestedResources(255), {
        validationLimits: { maxResources: 256 },
      }).ok,
    ).toBe(true);
    expect(
      validateStructural({}, schemaWithNestedResources(256), {
        validationLimits: { maxResources: 256 },
      }).errors,
    ).toEqual([
      {
        kind: "schema_invalid",
        reason: "value_domain",
        message: "compiled schema contains a non-portable YAML value",
        schema_path: "",
      },
    ]);
  });
});
