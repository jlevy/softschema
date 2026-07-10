import { expect, test } from "bun:test";
import { readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { validateArtifact, validateStructural } from "./validate.js";
import {
  DEFAULT_VALIDATION_LIMITS,
  type JsonValue,
  normalizePortableValue,
  PortableValueError,
  parsePortableYaml,
} from "./yaml-value-domain.js";

interface ValueDomainVector {
  id: string;
  yaml: string;
  value?: JsonValue;
  error_path?: string;
  line?: number;
  column?: number;
}

const ROOT = resolve(import.meta.dir, "../../..");
const VECTORS = JSON.parse(
  readFileSync(resolve(ROOT, "tests/value-domain/vectors.json"), "utf8"),
) as ValueDomainVector[];
const JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema";

function firstReason(result: ReturnType<typeof validateStructural>): unknown {
  const first = result.errors[0];
  return first !== undefined && "reason" in first ? first.reason : undefined;
}

test("shared YAML value-domain vectors", () => {
  for (const vector of VECTORS) {
    if ("value" in vector) {
      expect(parsePortableYaml(vector.yaml), vector.id).toEqual(vector.value as JsonValue);
    } else {
      try {
        parsePortableYaml(vector.yaml);
        throw new Error(`expected ${vector.id} to fail`);
      } catch (error) {
        expect(error, vector.id).toBeInstanceOf(PortableValueError);
        expect((error as PortableValueError).path, vector.id).toBe(vector.error_path as string);
        if (vector.line !== undefined) {
          expect((error as PortableValueError).line, vector.id).toBe(vector.line);
          expect((error as PortableValueError).column, vector.id).toBe(vector.column ?? null);
        }
      }
    }
  }
});

test("default validation limits are the portable profile", () => {
  expect(DEFAULT_VALIDATION_LIMITS).toEqual({
    maxResourceBytes: 8 * 1024 * 1024,
    maxBundleBytes: 64 * 1024 * 1024,
    maxResources: 256,
    maxNodesPerResource: 100_000,
    maxDepth: 128,
    maxScalarCodePoints: 1024 * 1024,
  });
});

test("each parser resource limit can be overridden", () => {
  const cases = [
    ["a: b\n", { maxResourceBytes: 3 }, ""],
    ["a: b\n", { maxNodesPerResource: 2 }, "/a"],
    ["a: [b]\n", { maxDepth: 2 }, "/a/0"],
    ["a: two\n", { maxScalarCodePoints: 2 }, "/a"],
  ] as const;
  for (const [yaml, validationLimits, path] of cases) {
    try {
      parsePortableYaml(yaml, validationLimits);
      throw new Error("expected limit failure");
    } catch (error) {
      expect(error).toBeInstanceOf(PortableValueError);
      expect((error as PortableValueError).path).toBe(path);
    }
  }
});

test("adversarial depth fails before JavaScript recursion", () => {
  const yaml = `value: ${"[".repeat(5000)}0${"]".repeat(5000)}\n`;
  try {
    parsePortableYaml(yaml);
    throw new Error("expected depth failure");
  } catch (error) {
    expect(error).toBeInstanceOf(PortableValueError);
    expect((error as PortableValueError).path.startsWith("/value")).toBe(true);
  }
});

test("default byte and scalar limits reject oversized input", () => {
  expect(() =>
    parsePortableYaml("x".repeat(DEFAULT_VALIDATION_LIMITS.maxResourceBytes + 1)),
  ).toThrow(PortableValueError);

  const oversizedScalar = "x".repeat(DEFAULT_VALIDATION_LIMITS.maxScalarCodePoints + 1);
  try {
    parsePortableYaml(`value: ${oversizedScalar}\n`);
    throw new Error("expected scalar limit failure");
  } catch (error) {
    expect(error).toBeInstanceOf(PortableValueError);
    expect((error as PortableValueError).path).toBe("/value");
  }
});

test("materialized resources use canonical JSON bundle and count limits", () => {
  const schema = {
    $schema: JSON_SCHEMA_2020_12,
    $ref: "https://schemas.example/value",
  };
  const rootBytes = Buffer.byteLength(JSON.stringify(schema));
  const resources = { "https://schemas.example/value": true };

  expect(
    validateStructural({}, schema, {
      resources,
      validationLimits: { maxBundleBytes: rootBytes + 3 },
    }).errors,
  ).toEqual([
    {
      kind: "schema_invalid",
      reason: "value_domain",
      message: "compiled schema contains a non-portable YAML value",
      schema_path: "",
    },
  ]);
  expect(
    validateStructural({}, schema, {
      resources,
      validationLimits: { maxBundleBytes: rootBytes + 4 },
    }).ok,
  ).toBe(true);
  expect(
    firstReason(
      validateStructural({}, schema, {
        resources,
        validationLimits: { maxResources: 1 },
      }),
    ),
  ).toBe("value_domain");
});

test.each([
  [{ x: 0.00001 }, 11],
  [{ x: "😀" }, 12],
  [{ x: 1.0 }, 7],
  [{ z: false, a: [null, 1.2345e-5] }, 33],
] as const)("canonical JSON sizing is portable", (value, expectedSize) => {
  expect(normalizePortableValue(value).sizeBytes).toBe(expectedSize);
});

test("schema and artifact boundaries return portable value-domain records", () => {
  const schemaResult = validateStructural(
    {},
    {
      $schema: JSON_SCHEMA_2020_12,
      type: "object",
      maximum: 1e20,
    },
  );
  expect(schemaResult.errors).toEqual([
    {
      kind: "schema_invalid",
      reason: "value_domain",
      message: "compiled schema contains a non-portable YAML value",
      schema_path: "/maximum",
    },
  ]);

  const artifactPath = resolve(import.meta.dir, ".tmp-value-domain-artifact.md");
  writeFileSync(
    artifactPath,
    "---\nsoftschema:\n  contract: example:Value/v1\nitem:\n  value: .nan\n---\n",
    "utf8",
  );
  try {
    const artifactResult = validateArtifact(
      artifactPath,
      {
        id: "example:Value/v1",
        model: null,
        envelopeKey: "item",
        status: "enforced",
        profile: "frontmatter-md",
        schemaPath: null,
      },
      {},
    );
    expect((artifactResult.output.structural as { errors: unknown[] }).errors).toEqual([
      {
        kind: "parse_error",
        reason: "value_domain",
        message: "artifact contains a non-portable YAML value",
        source: artifactPath,
        path: "/item/value",
      },
    ]);

    const purePath = resolve(import.meta.dir, ".tmp-value-domain-artifact.yaml");
    writeFileSync(purePath, "item:\n  value: .nan\n", "utf8");
    try {
      const pureResult = validateArtifact(purePath, {
        id: "example:Value/v1",
        model: null,
        envelopeKey: "item",
        status: "enforced",
        profile: "pure-yaml",
        schemaPath: null,
      });
      const error = (pureResult.output.structural as { errors: Record<string, unknown>[] })
        .errors[0];
      expect(error?.reason).toBe("value_domain");
      expect(error?.path).toBe("/item/value");
    } finally {
      unlinkSync(purePath);
    }
  } finally {
    unlinkSync(artifactPath);
  }
});

test("materialized values reject cycles, non-JSON types, and unsafe integers", () => {
  const schema = {
    $schema: JSON_SCHEMA_2020_12,
    $ref: "https://schemas.example/value",
  };
  const cyclic: Record<string, unknown> = {};
  cyclic.self = cyclic;
  for (const resource of [
    cyclic,
    { value: new Date("2026-01-01T00:00:00Z") },
    { value: 9007199254740992 },
  ]) {
    expect(
      firstReason(
        validateStructural({}, schema, {
          resources: { "https://schemas.example/value": resource },
        }),
      ),
    ).toBe("value_domain");
  }

  const withHiddenMetadata = { type: "object" } as Record<string, unknown>;
  Object.defineProperty(withHiddenMetadata, "~metadata", {
    enumerable: false,
    value: new Date("2026-01-01T00:00:00Z"),
  });
  expect(normalizePortableValue(withHiddenMetadata).value).toEqual({ type: "object" });

  const withAccessor = { type: "object" } as Record<string, unknown>;
  Object.defineProperty(withAccessor, "unsafe", {
    enumerable: true,
    get: () => "must not run",
  });
  expect(() => normalizePortableValue(withAccessor)).toThrow(PortableValueError);
});
