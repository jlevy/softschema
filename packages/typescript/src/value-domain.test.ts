import { expect, test } from "bun:test";
import { readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { Composer, CST, Parser } from "yaml";
import { validateArtifact, validateStructural } from "./validate.js";
import {
  DEFAULT_VALIDATION_LIMITS,
  type JsonValue,
  normalizePortableValue,
  PortableValueError,
  PortableYamlSyntaxError,
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

test("YAML node limits stop CST construction during token iteration", () => {
  const originalNext = Parser.prototype.next;
  Parser.prototype.next = function* guardedNext(
    this: Parser,
    source: string,
  ): Generator<CST.Token, void> {
    yield* originalNext.call(this, source);
    const allocatedItems = this.stack.reduce(
      (total, token) => total + (CST.isCollection(token) ? token.items.length : 0),
      0,
    );
    if (allocatedItems > 150) throw new Error("CST construction crossed the test sentinel");
  };

  const caught: unknown[] = [];
  try {
    for (const source of ["- 0\n".repeat(1000), `[${"0,".repeat(1000)}0]`]) {
      try {
        parsePortableYaml(source, { maxNodesPerResource: 100 });
      } catch (error) {
        caught.push(error);
      }
    }
  } finally {
    Parser.prototype.next = originalNext;
  }

  expect(caught).toHaveLength(2);
  for (const error of caught) {
    expect(error).toBeInstanceOf(PortableValueError);
    expect((error as PortableValueError).message).toBe("maximum node count exceeded");
  }
});

test("YAML construction limits retain global syntax precedence", () => {
  const cases = [
    ["- a\n- b\n- c\n- [\n", { maxNodesPerResource: 3 }, 5, 1],
    ["- a\n- b\n- [\n", { maxNodesPerResource: 1 }, 4, 1],
    [`[${"0,".repeat(100)}[\n`, { maxNodesPerResource: 10 }, 2, 1],
    [`["a" "b",${"0,".repeat(100)}0]\n`, { maxNodesPerResource: 10 }, 1, 6],
  ] as const;

  for (const [source, limits, line, column] of cases) {
    try {
      parsePortableYaml(source, limits);
      throw new Error("expected syntax failure");
    } catch (error) {
      expect(error).toBeInstanceOf(PortableYamlSyntaxError);
      expect((error as PortableYamlSyntaxError).message).toBe("invalid YAML syntax");
      expect((error as PortableYamlSyntaxError).line).toBe(line);
      expect((error as PortableYamlSyntaxError).column).toBe(column);
    }
  }
});

test("YAML limits use Python event paths and source locations", () => {
  const cases = [
    ["{a:1,b:2}", { maxNodesPerResource: 1 }, "maximum node count exceeded", "", 1, 2],
    ["[a: [b: [c: [d: 1]]]]", { maxDepth: 3 }, "maximum depth exceeded", "/0/a/0", 1, 6],
  ] as const;

  for (const [source, limits, message, path, line, column] of cases) {
    try {
      parsePortableYaml(source, limits);
      throw new Error("expected value-domain limit failure");
    } catch (error) {
      expect(error).toBeInstanceOf(PortableValueError);
      expect((error as PortableValueError).message).toBe(message);
      expect((error as PortableValueError).path).toBe(path);
      expect((error as PortableValueError).line).toBe(line);
      expect((error as PortableValueError).column).toBe(column);
    }
  }
});

test("empty multi-document floods do not accumulate CST documents", () => {
  const source = "---\n...\n".repeat(1000);
  expect(() => parsePortableYaml(source, { maxNodesPerResource: 100 })).toThrow(
    PortableYamlSyntaxError,
  );
});

test("discarded multi-document directives stay bounded per document", () => {
  const originalCompose = Composer.prototype.compose;
  Composer.prototype.compose = function* guardedCompose(
    this: Composer,
    tokens: Iterable<CST.Token>,
    forceDoc?: boolean,
    endOffset?: number,
  ) {
    const materialized = [...tokens];
    if (materialized.length > 3) {
      throw new Error("directives accumulated across discarded documents");
    }
    yield* originalCompose.call(this, materialized, forceDoc, endOffset);
  };

  try {
    const source = "%YAML 1.2\n---\nvalue\n...\n".repeat(1000);
    expect(() => parsePortableYaml(source)).toThrow(PortableYamlSyntaxError);
  } finally {
    Composer.prototype.compose = originalCompose;
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
  let accessorCalls = 0;
  Object.defineProperty(withAccessor, "unsafe", {
    enumerable: true,
    get: () => {
      accessorCalls += 1;
      return "must not run";
    },
  });
  expect(() => normalizePortableValue(withAccessor)).toThrow(PortableValueError);
  expect(accessorCalls).toBe(0);

  const sparse = new Array(1);
  const inherited = new Array(1);
  const inheritedPrototype = Object.create(Array.prototype) as Record<string, unknown>;
  inheritedPrototype[0] = "must not materialize";
  Object.setPrototypeOf(inherited, inheritedPrototype);
  const accessorArray: unknown[] = [];
  Object.defineProperty(accessorArray, "0", {
    enumerable: true,
    get: () => {
      accessorCalls += 1;
      return "must not run";
    },
  });
  for (const value of [sparse, inherited, accessorArray]) {
    expect(() => normalizePortableValue(value)).toThrow(PortableValueError);
  }
  expect(accessorCalls).toBe(0);

  for (const invalidScalar of ["\ud800", "\udc00", "\ud800x"]) {
    expect(() => normalizePortableValue(invalidScalar)).toThrow(PortableValueError);
    expect(() => parsePortableYaml(`value: "${invalidScalar}"\n`)).toThrow(PortableValueError);
    expect(() => normalizePortableValue({ [invalidScalar]: true })).toThrow(PortableValueError);
  }

  try {
    normalizePortableValue({ "😀": new Date(0), "\uE000": new Date(0) });
    throw new Error("expected a materialized-value failure");
  } catch (error) {
    expect(error).toBeInstanceOf(PortableValueError);
    expect((error as PortableValueError).path).toBe("/\uE000");
  }
});
