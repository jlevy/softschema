import { expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import {
  constants,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  symlinkSync,
  truncateSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { z } from "zod";
import { fileOpenFlags, readBoundedBytes } from "../src/bounded-file.js";
import { compileSchema, renderSchemaWithinLimit } from "../src/compile.js";
import {
  DEFAULT_VALIDATION_LIMITS,
  normalizePortableValue,
  PortableValueError,
} from "../src/core/value-domain.js";
import type { Contract } from "../src/models.js";
import { SchemaView } from "../src/schemaView.js";
import {
  captureValidatedSchemaSource,
  readFrontmatterWithLocations,
  readPureYamlArtifactWithLocations,
  takeValidatedSchemaSource,
  validateArtifact,
} from "../src/validate.js";

test("file-backed YAML readers stop at one byte beyond the configured limit", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-read-"));
  const source = join(directory, "oversized.yaml");
  writeFileSync(source, "value", "utf8");

  expect(() => readBoundedBytes(source, 4)).toThrow(PortableValueError);
  expect(() => readFrontmatterWithLocations(source, { maxResourceBytes: 4 })).toThrow(
    "maximum resource size exceeded",
  );
  expect(() => readPureYamlArtifactWithLocations(source, { maxResourceBytes: 4 })).toThrow(
    "maximum resource size exceeded",
  );
  expect(() => SchemaView.load(source, { maxResourceBytes: 4 })).toThrow(
    "maximum resource size exceeded",
  );
});

test("bounded reader returns an exact initialized backing allocation", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-exact-buffer-"));
  const source = join(directory, "one-byte.yaml");
  try {
    writeFileSync(source, "x", "utf8");
    const encoded = readBoundedBytes(source, 1);
    expect(encoded.byteLength).toBe(1);
    expect(encoded.buffer.byteLength).toBe(1);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("bounded reader uses only Node-supported Windows open flags", () => {
  expect(fileOpenFlags("win32")).toBe(constants.O_RDONLY);
  expect(fileOpenFlags("linux")).not.toBe(fileOpenFlags("win32"));
});

test("compile drift reads reject an oversized committed schema", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-compile-read-"));
  const output = join(directory, "oversized.schema.yaml");
  const schema = z.strictObject({ value: z.string() });
  try {
    compileSchema(schema, output, { contractId: "example:BoundedSchema/v1" });
    expect(
      compileSchema(schema, output, {
        contractId: "example:BoundedSchema/v1",
        checkOnly: true,
      }).drift,
    ).toBe(false);
    truncateSync(output, DEFAULT_VALIDATION_LIMITS.maxResourceBytes + 1);

    expect(() =>
      compileSchema(schema, output, {
        contractId: "example:BoundedSchema/v1",
        checkOnly: true,
      }),
    ).toThrow(PortableValueError);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("compile drift decodes committed schemas as strict UTF-8", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-compile-utf8-"));
  const output = join(directory, "invalid.schema.yaml");
  const schema = z.strictObject({ value: z.string() });
  try {
    writeFileSync(output, Uint8Array.of(0xff));
    expect(() =>
      compileSchema(schema, output, {
        contractId: "example:BoundedSchema/v1",
        checkOnly: true,
      }),
    ).toThrow(TypeError);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("compile drift applies the portable YAML boundary", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-compile-portable-yaml-"));
  const output = join(directory, "nonportable.schema.yaml");
  const schema = z.strictObject({ value: z.string() });
  try {
    for (const committed of [
      ".nan\n",
      "&shared [*shared]\n",
      `${"[".repeat(130)}0${"]".repeat(130)}\n`,
    ]) {
      writeFileSync(output, committed, "utf8");
      expect(() =>
        compileSchema(schema, output, {
          contractId: "example:BoundedSchema/v1",
          checkOnly: true,
        }),
      ).toThrow(PortableValueError);
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("compile drift treats a directory as missing", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-compile-directory-"));
  const schema = z.strictObject({ value: z.string() });
  try {
    const result = compileSchema(schema, directory, {
      contractId: "example:BoundedSchema/v1",
      checkOnly: true,
    });
    expect(result.drift).toBe(true);
    expect(result.driftDiff).toBe(`missing committed compiled schema at ${directory}`);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("compile drift distinguishes a JSON boolean from an integer", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-compile-json-type-drift-"));
  const output = join(directory, "const.schema.yaml");
  const schema = z.literal(1);
  try {
    compileSchema(schema, output, { contractId: "example:ConstOne/v1" });
    const committed = readFileSync(output, "utf8");
    expect(committed).toContain("const: 1");
    writeFileSync(output, committed.replace("const: 1", "const: true"), "utf8");
    expect(
      compileSchema(schema, output, {
        contractId: "example:ConstOne/v1",
        checkOnly: true,
      }).drift,
    ).toBe(true);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("compiler charges digest metadata against the final node budget", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-compile-final-node-budget-"));
  const output = join(directory, "too-many-final-nodes.schema.yaml");
  const values = Array.from({ length: 99_987 }, (_value, index) => `v${index}`);
  try {
    expect(() =>
      compileSchema(z.enum(values as [string, ...string[]]), output, {
        contractId: "example:FinalNodeBudget/v1",
      }),
    ).toThrow("maximum node count exceeded");
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("compiler falls back to canonical JSON when YAML exceeds its reader limit", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-render-fallback-"));
  const limit = DEFAULT_VALIDATION_LIMITS.maxResourceBytes;
  const description = "x\n".repeat(DEFAULT_VALIDATION_LIMITS.maxScalarCodePoints / 2);
  const schema = {
    type: "object",
    properties: {
      p0: { type: "string", description },
      p1: { type: "string", description },
    },
  };
  const normalized = normalizePortableValue(schema);
  expect(normalized.sizeBytes).toBeLessThan(limit);
  const rendered = renderSchemaWithinLimit(normalized.value as Record<string, unknown>);
  expect(rendered.startsWith("{")).toBe(true);
  expect(Buffer.byteLength(rendered, "utf8")).toBeLessThan(limit);
  try {
    const output = join(directory, "fallback.schema.yaml");
    writeFileSync(output, rendered, "utf8");
    expect(SchemaView.load(output).raw).toEqual(schema);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("compiler accepts the shared near-limit no-wrap shape", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-render-near-limit-"));
  const description = "x ".repeat(Math.floor(1_047_500 / 2));
  const properties: Record<string, unknown> = {};
  for (let index = 0; index < 8; index += 1) {
    properties[`p${index}`] = { type: "string", description };
  }
  const schema = { type: "object", properties };
  const normalized = normalizePortableValue(schema);
  const rendered = renderSchemaWithinLimit(normalized.value as Record<string, unknown>);
  expect(Buffer.byteLength(rendered, "utf8")).toBe(8_380_369);
  try {
    const output = join(directory, "near-limit.schema.yaml");
    writeFileSync(output, rendered, "utf8");
    expect(SchemaView.load(output).raw).toEqual(schema);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("bounded readers reject special files and bind symlinks to a stable target", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-special-read-"));
  const target = join(directory, "schema.yaml");
  const linkedDirectory = join(directory, "linked");
  writeFileSync(target, "type: object\n", "utf8");
  try {
    let linked = false;
    try {
      symlinkSync(directory, linkedDirectory, "dir");
      linked = true;
    } catch {
      linked = false;
    }
    if (linked) {
      const encoded = readBoundedBytes(join(linkedDirectory, "schema.yaml"), 1024);
      expect(Buffer.from(encoded).toString()).toBe("type: object\n");
    }

    if (process.platform !== "win32") {
      const fifo = join(directory, "schema.fifo");
      const created = spawnSync("mkfifo", [fifo], { encoding: "utf8" });
      expect(created.status, created.stderr).toBe(0);
      const modulePath = join(import.meta.dir, "../src/bounded-file.ts");
      const script = [
        `import { readBoundedBytes } from ${JSON.stringify(modulePath)};`,
        "try {",
        `  readBoundedBytes(${JSON.stringify(fifo)}, 4);`,
        "  process.exit(2);",
        "} catch (error) {",
        '  if (error && typeof error === "object" && "code" in error && error.code === "EINVAL") process.exit(0);',
        "  throw error;",
        "}",
      ].join("\n");
      const checked = spawnSync(process.execPath, ["-e", script], {
        encoding: "utf8",
        timeout: 5_000,
      });
      expect(checked.status, `${checked.error?.message ?? ""}\n${checked.stderr}`).toBe(0);
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("bounded reader rejects a symlink loop as a filesystem error", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-symlink-loop-"));
  const first = join(directory, "first.yaml");
  const second = join(directory, "second.yaml");
  try {
    try {
      symlinkSync("second.yaml", first);
      symlinkSync("first.yaml", second);
    } catch {
      return;
    }
    expect(() => readBoundedBytes(first, 16)).toThrow();
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("bounded reader rejects parent substitution during canonical resolution", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-bounded-parent-race-"));
  const authorized = join(root, "authorized");
  const parked = join(root, "authorized-original");
  const outside = join(root, "outside");
  mkdirSync(authorized);
  mkdirSync(outside);
  const source = join(authorized, "schema.yaml");
  writeFileSync(source, "type: object\n", "utf8");
  writeFileSync(join(outside, "schema.yaml"), "outside\n", "utf8");
  const probe = join(root, "symlink-probe");
  try {
    symlinkSync(outside, probe, "dir");
    unlinkSync(probe);
  } catch {
    rmSync(root, { recursive: true, force: true });
    return;
  }

  const originalNative = realpathSync.native;
  let swapped = false;
  realpathSync.native = ((path: string) => {
    const resolved = originalNative(path) as string;
    if (path === source && !swapped) {
      renameSync(authorized, parked);
      symlinkSync(outside, authorized, "dir");
      swapped = true;
    }
    return resolved;
  }) as typeof realpathSync.native;
  try {
    expect(() => readBoundedBytes(source, 1024)).toThrow(
      "bounded input changed before it could be opened",
    );
  } finally {
    realpathSync.native = originalNative;
    rmSync(root, { recursive: true, force: true });
  }
});

test("metadata schema authorization survives parent substitution", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-bounded-metadata-race-"));
  const documents = join(root, "documents");
  const parked = join(root, "documents-original");
  const outside = join(root, "outside");
  mkdirSync(documents);
  mkdirSync(outside);
  const schema = join(documents, "record.schema.yaml");
  writeFileSync(schema, "type: object\n", "utf8");
  writeFileSync(join(outside, "record.schema.yaml"), "type: object\n", "utf8");
  const artifact = join(documents, "record.md");
  const artifactText = [
    "---",
    "softschema:",
    "  contract: example:BoundedRecord/v1",
    "  schema: record.schema.yaml",
    "  envelope: record",
    "record:",
    "  value: accepted",
    "---",
    "body",
    "",
  ].join("\n");
  writeFileSync(artifact, artifactText, "utf8");
  writeFileSync(join(outside, "record.md"), artifactText, "utf8");
  const probe = join(root, "symlink-probe");
  try {
    symlinkSync(outside, probe, "dir");
    unlinkSync(probe);
  } catch {
    rmSync(root, { recursive: true, force: true });
    return;
  }

  const contract: Contract = {
    id: "example:BoundedRecord/v1",
    model: null,
    envelopeKey: "record",
    status: "soft",
    profile: "frontmatter-md",
    schemaPath: null,
  };
  const located = readFrontmatterWithLocations(artifact);
  let result: ReturnType<typeof validateArtifact>;
  renameSync(documents, parked);
  symlinkSync(outside, documents, "dir");
  try {
    result = validateArtifact(artifact, contract, {
      preParsed: { hasFence: located.hasFence, value: located.value },
      preParsedSource: located.sourceFile,
    });
  } finally {
    unlinkSync(documents);
    renameSync(parked, documents);
    rmSync(root, { recursive: true, force: true });
  }

  expect(result.output.structural.ok).toBe(false);
  expect(result.output.structural.errors[0]).toMatchObject({
    kind: "schema_missing",
  });
});

test("missing metadata schema through an escaping symlink reports escape", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-missing-schema-escape-"));
  const documents = join(root, "documents");
  const outside = join(root, "outside");
  mkdirSync(documents);
  mkdirSync(outside);
  try {
    try {
      symlinkSync(outside, join(documents, "escape"), "dir");
    } catch {
      return;
    }
    const artifact = join(documents, "record.md");
    writeFileSync(
      artifact,
      [
        "---",
        "softschema:",
        "  contract: example:BoundedRecord/v1",
        "  schema: escape/missing.schema.yaml",
        "  envelope: record",
        "record:",
        "  value: accepted",
        "---",
        "",
      ].join("\n"),
      "utf8",
    );
    const contract: Contract = {
      id: "example:BoundedRecord/v1",
      model: null,
      envelopeKey: "record",
      status: "soft",
      profile: "frontmatter-md",
      schemaPath: null,
    };

    const result = validateArtifact(artifact, contract);

    expect(result.output.structural.ok).toBe(false);
    expect(result.output.structural.errors[0]).toMatchObject({
      kind: "schema_missing",
      message: expect.stringContaining("escapes the document directory"),
    });
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("missing metadata schema through a symlink with a missing target prefix reports escape", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-dangling-schema-escape-"));
  const documents = join(root, "documents");
  const missingTarget = join(root, "outside-missing", "nested");
  mkdirSync(documents);
  try {
    try {
      symlinkSync(missingTarget, join(documents, "escape"), "dir");
    } catch {
      return;
    }
    const artifact = join(documents, "record.md");
    writeFileSync(
      artifact,
      [
        "---",
        "softschema:",
        "  contract: example:BoundedRecord/v1",
        "  schema: escape/missing.schema.yaml",
        "  envelope: record",
        "record: {}",
        "---",
        "",
      ].join("\n"),
      "utf8",
    );
    const result = validateArtifact(artifact, {
      id: "example:BoundedRecord/v1",
      model: null,
      envelopeKey: "record",
      status: "soft",
      profile: "frontmatter-md",
      schemaPath: null,
    });

    expect(result.output.structural.errors[0]).toMatchObject({
      kind: "schema_missing",
      message: expect.stringContaining("escapes the document directory"),
    });
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("schema diagnostics retain the exact validated source map", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-schema-source-map-"));
  const schema = join(directory, "record.schema.yaml");
  const artifact = join(directory, "record.md");
  try {
    writeFileSync(schema, "type: 7\n", "utf8");
    writeFileSync(artifact, "---\nrecord:\n  value: accepted\n---\n", "utf8");
    const contract: Contract = {
      id: "example:BoundedRecord/v1",
      model: null,
      envelopeKey: "record",
      status: "soft",
      profile: "frontmatter-md",
      schemaPath: schema,
    };
    const ordinaryResult = validateArtifact(artifact, contract);
    expect(ordinaryResult.output.structural.ok).toBe(false);
    expect(takeValidatedSchemaSource(ordinaryResult.output.structural)).toBeUndefined();

    const result = captureValidatedSchemaSource(() =>
      captureValidatedSchemaSource(() => validateArtifact(artifact, contract)),
    );

    writeFileSync(schema, "type: object\n", "utf8");
    const validatedSource = takeValidatedSchemaSource(result.output.structural);

    expect(validatedSource?.path).toBe(realpathSync(schema));
    expect(validatedSource?.sourceMap.span("/type")).toBeDefined();
    expect(takeValidatedSchemaSource(result.output.structural)).toBeUndefined();
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("failed schema reads retain an explicit empty exact source", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-schema-failure-source-"));
  const schema = join(directory, "record.schema.yaml");
  const artifact = join(directory, "record.md");
  try {
    writeFileSync(artifact, "---\nrecord: {}\n---\n", "utf8");
    const contract: Contract = {
      id: "example:BoundedRecord/v1",
      model: null,
      envelopeKey: "record",
      status: "soft",
      profile: "frontmatter-md",
      schemaPath: schema,
    };
    const cases: readonly {
      readonly contents: string | Uint8Array;
      readonly readCompleted: boolean;
    }[] = [
      {
        contents: "x".repeat(DEFAULT_VALIDATION_LIMITS.maxResourceBytes + 1),
        readCompleted: false,
      },
      { contents: Uint8Array.of(0xff), readCompleted: true },
      { contents: "type: [\n", readCompleted: true },
    ];
    for (const { contents, readCompleted } of cases) {
      writeFileSync(schema, contents);
      const result = captureValidatedSchemaSource(() => validateArtifact(artifact, contract));
      expect(result.output.structural.ok).toBe(false);

      writeFileSync(schema, "type: 7\n", "utf8");
      const source = takeValidatedSchemaSource(result.output.structural);
      expect({ path: source?.path, span: source?.sourceMap.span("/type") }).toEqual({
        path: readCompleted ? realpathSync(schema) : resolve(schema),
        span: undefined,
      });
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("document-controlled control-character schema paths use the shared failure", () => {
  const vectors = JSON.parse(
    readFileSync(
      resolve(import.meta.dir, "../../../tests/parity/metadata-schema-paths.json"),
      "utf8",
    ),
  ) as {
    document_schema_path: { rejected_code_points: number[]; expected_kind: "schema_missing" };
  };
  const directory = mkdtempSync(join(tmpdir(), "softschema-schema-control-path-"));
  const artifact = join(directory, "record.md");
  try {
    for (const codePoint of vectors.document_schema_path.rejected_code_points) {
      const schemaPath = `missing-${String.fromCodePoint(codePoint)}.schema.yaml`;
      writeFileSync(
        artifact,
        [
          "---",
          "softschema:",
          "  contract: example:BoundedRecord/v1",
          `  schema: ${JSON.stringify(schemaPath)}`,
          "  envelope: record",
          "record: {}",
          "---",
          "",
        ].join("\n"),
        "utf8",
      );
      const result = validateArtifact(artifact, {
        id: "example:BoundedRecord/v1",
        model: null,
        envelopeKey: "record",
        status: "soft",
        profile: "frontmatter-md",
        schemaPath: null,
      });

      expect({ codePoint, kind: result.output.structural.errors[0]?.kind }).toEqual({
        codePoint,
        kind: vectors.document_schema_path.expected_kind,
      });
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
