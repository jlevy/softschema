import { afterEach, beforeEach, expect, test } from "bun:test";
import {
  existsSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { main } from "../src/cli.js";
import { DISCOVERY_MAX_DEPTH } from "../src/artifact-discovery.js";

const argv = (...args: string[]) => ["node", "cli.js", ...args];
const ROOT = resolve(import.meta.dir, "../../..");
const SOURCE_SEPARATOR_VECTORS = JSON.parse(
  readFileSync(resolve(ROOT, "tests/value-domain/source-separator-vectors.json"), "utf8"),
) as {
  artifact_error: { reason: string; message: string; path: string };
  literal_cases: { yaml: string; line: number; column: number }[];
};
const EXTRA_PROPERTY_VECTORS = JSON.parse(
  readFileSync(resolve(ROOT, "tests/diagnostics/extra-property-location-vectors.json"), "utf8"),
) as {
  contract: string;
  envelope: string;
  artifact: string;
  expected: { path: string; line: number; column: number; message: string };
  cases: { id: string; validator: string; schema: string }[];
};

interface CapturedBatchResult {
  readonly input: unknown;
}

interface CapturedBatchAggregate {
  readonly results: readonly CapturedBatchResult[];
}

let originalCwd: string;
let originalWrite: typeof process.stdout.write;
let originalErrorWrite: typeof process.stderr.write;
let chunks: string[];
let errorChunks: string[];

beforeEach(() => {
  originalCwd = process.cwd();
  originalWrite = process.stdout.write.bind(process.stdout);
  originalErrorWrite = process.stderr.write.bind(process.stderr);
  chunks = [];
  errorChunks = [];
  process.stdout.write = ((chunk: string | Uint8Array) => {
    chunks.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk));
    return true;
  }) as typeof process.stdout.write;
  process.stderr.write = ((chunk: string | Uint8Array) => {
    errorChunks.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk));
    return true;
  }) as typeof process.stderr.write;
});

afterEach(() => {
  process.chdir(originalCwd);
  process.stdout.write = originalWrite;
  process.stderr.write = originalErrorWrite;
});

function captured(): string {
  return chunks.join("");
}

function capturedErrors(): string {
  return errorChunks.join("");
}

function artifact(path: string, payload: string, contract = false): void {
  const metadata = contract ? "softschema: test.batch:Record/v1\n" : "";
  writeFileSync(path, `---\n${metadata}record:\n${payload}---\nbody\n`, "utf8");
}

function schema(path: string): void {
  writeFileSync(
    path,
    `$schema: https://json-schema.org/draft/2020-12/schema
type: object
required: [name, count]
properties:
  name: {type: string}
  count: {type: integer}
additionalProperties: false
`,
    "utf8",
  );
}

function batchArgs(directory: string, schemaPath: string, ...extra: string[]): string[] {
  return [
    "validate",
    directory,
    "--recursive",
    "--contract",
    "test.batch:Record/v1",
    "--envelope",
    "record",
    "--schema",
    schemaPath,
    ...extra,
  ];
}

test("batch JSON reports partial success and source-positioned payload failures", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const schemaPath = join(directory, "record.schema.yaml");
  const artifacts = join(directory, "artifacts");
  mkdirSync(artifacts);
  schema(schemaPath);
  artifact(join(artifacts, "a-valid.md"), "  name: Valid\n  count: 2\n");
  artifact(join(artifacts, "b-invalid.md"), "  name: Invalid\n  count: nope\n");
  process.chdir(directory);

  expect(await main(argv(...batchArgs("artifacts", schemaPath)))).toBe(1);

  expect(capturedErrors()).toBe("");
  const aggregate = JSON.parse(captured()) as Record<string, any>;
  expect(aggregate.format).toBe("diagnostic-v1");
  expect(aggregate.summary).toEqual({
    exit_code: 1,
    input_failed: 0,
    passed: 1,
    total: 2,
    validation_failed: 1,
  });
  expect(aggregate.results.map((result: any) => result.input.source)).toEqual([
    "artifacts/a-valid.md",
    "artifacts/b-invalid.md",
  ]);
  expect(aggregate.results[1].diagnostics[0]).toMatchObject({
    path: "/record/count",
    line: 4,
    column: 10,
  });
});

test("JSONL emits one self-describing line per result and no summary", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const schemaPath = join(directory, "record.schema.yaml");
  const artifacts = join(directory, "artifacts");
  mkdirSync(artifacts);
  schema(schemaPath);
  artifact(join(artifacts, "a.md"), "  name: A\n  count: 1\n");
  artifact(join(artifacts, "b.md"), "  name: B\n  count: no\n");
  process.chdir(directory);

  expect(await main(argv(...batchArgs("artifacts", schemaPath, "--format", "jsonl")))).toBe(1);

  const jsonl = captured();
  expect(jsonl.endsWith("\n")).toBe(true);
  const records = jsonl
    .slice(0, -1)
    .split("\n")
    .map((line) => JSON.parse(line) as Record<string, unknown>);
  expect(records).toHaveLength(2);
  expect(records.every((record) => record.format === "diagnostic-v1")).toBe(true);
  expect(records.every((record) => "result" in record && !("summary" in record))).toBe(true);
});

test("JSONL reports the shared nonportable source-separator location", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const vector = SOURCE_SEPARATOR_VECTORS.literal_cases[1];
  if (vector === undefined) throw new Error("source-separator vector missing");
  writeFileSync(join(directory, "artifact.yaml"), new TextEncoder().encode(vector.yaml));
  process.chdir(directory);

  expect(
    await main(argv("validate", "artifact.yaml", "--profile", "pure-yaml", "--format", "jsonl")),
  ).toBe(1);

  expect(capturedErrors()).toBe("");
  const result = (JSON.parse(captured()) as Record<string, any>).result;
  const expected = SOURCE_SEPARATOR_VECTORS.artifact_error;
  expect(result.input).toEqual({
    kind: "parse_error",
    reason: expected.reason,
    message: expected.message,
    source: "artifact.yaml",
    path: expected.path,
    line: vector.line,
    column: vector.column,
  });
  expect(result.diagnostics[0]).toEqual({
    category: "parse",
    rule_id: "softschema.parse_error.value_domain",
    severity: "error",
    message: expected.message,
    source: "artifact.yaml",
    path: expected.path,
    line: vector.line,
    column: vector.column,
  });
});

test.each(EXTRA_PROPERTY_VECTORS.cases)(
  "extra-property diagnostic anchors the shared escaped key: $id",
  async (vector) => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
    writeFileSync(join(directory, "artifact.yaml"), EXTRA_PROPERTY_VECTORS.artifact, "utf8");
    writeFileSync(join(directory, "schema.yaml"), vector.schema, "utf8");
    process.chdir(directory);

    expect(
      await main(
        argv(
          "validate",
          "artifact.yaml",
          "--profile",
          "pure-yaml",
          "--contract",
          EXTRA_PROPERTY_VECTORS.contract,
          "--envelope",
          EXTRA_PROPERTY_VECTORS.envelope,
          "--schema",
          "schema.yaml",
          "--format",
          "jsonl",
        ),
      ),
    ).toBe(1);

    const record = (JSON.parse(captured()) as Record<string, any>).result;
    const error = record.validation.structural.errors[0];
    expect(Object.keys(error).sort()).toEqual(
      ["kind", "path", "validator", "validator_value", "value", "message"].sort(),
    );
    const expected = EXTRA_PROPERTY_VECTORS.expected;
    expect(record.diagnostics).toEqual([
      {
        category: "structural",
        rule_id: `softschema.schema_violation.${vector.validator.toLowerCase()}`,
        severity: "error",
        message: expected.message,
        source: "artifact.yaml",
        path: expected.path,
        line: expected.line,
        column: expected.column,
      },
    ]);
  },
);

test("recursive no-match is a fail-closed input error", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  mkdirSync(join(directory, "artifacts"));
  process.chdir(directory);

  expect(await main(argv("validate", "artifacts", "--recursive"))).toBe(2);

  const aggregate = JSON.parse(captured()) as Record<string, any>;
  expect(aggregate.summary.exit_code).toBe(2);
  expect(aggregate.results[0].input).toEqual({
    kind: "input_error",
    message: "artifact directory contains no matching files",
    reason: "no_matches",
    source: "artifacts",
  });
});

test("recursive discovery limits discard operand matches and continue", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const root = join(directory, "artifacts");
  mkdirSync(root);
  artifact(join(root, "a-early.md"), "  name: Early\n  count: 1\n");
  let current = root;
  for (let index = 0; index <= DISCOVERY_MAX_DEPTH; index += 1) {
    current = join(current, `d${index.toString().padStart(3, "0")}`);
    mkdirSync(current);
  }
  artifact(join(directory, "after.md"), "  name: After\n  count: 2\n");
  process.chdir(directory);

  expect(await main(argv("validate", "artifacts", "after.md", "--recursive"))).toBe(2);

  const aggregate = JSON.parse(captured()) as CapturedBatchAggregate;
  const limitSource = `artifacts/${Array.from({ length: DISCOVERY_MAX_DEPTH + 1 }, (_, index) =>
    `d${index.toString().padStart(3, "0")}`,
  ).join("/")}`;
  expect(aggregate.results.map((result) => result.input)).toEqual([
    {
      kind: "input_error",
      message: "artifact discovery limit exceeded",
      reason: "discovery_limit",
      source: limitSource,
    },
    {
      kind: "artifact_input",
      ok: true,
      profile: "frontmatter-md",
      source: "after.md",
      values: { record: { count: 2, name: "After" } },
    },
  ]);
});

test("batch discovery deduplicates an explicit file and symlink", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  artifact(join(directory, "artifact.md"), "  name: A\n  count: 1\n", true);
  try {
    symlinkSync(join(directory, "artifact.md"), join(directory, "alias.md"));
  } catch {
    return;
  }
  process.chdir(directory);

  expect(await main(argv("validate", "artifact.md", "alias.md"))).toBe(0);

  const aggregate = JSON.parse(captured()) as Record<string, any>;
  expect(aggregate.summary.total).toBe(1);
  expect(aggregate.results[0].input.source).toBe("artifact.md");
});

test("one binding failure does not abort the remaining artifact", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  artifact(join(directory, "a-unbound.md"), "  name: A\n  count: 1\n");
  artifact(join(directory, "b-bound.md"), "  name: B\n  count: 2\n", true);
  process.chdir(directory);

  expect(await main(argv("validate", "a-unbound.md", "b-bound.md"))).toBe(1);

  const aggregate = JSON.parse(captured()) as Record<string, any>;
  expect(aggregate.results.map((result: any) => result.outcome)).toEqual([
    "validation_failed",
    "passed",
  ]);
  expect(aggregate.results[0].validation).toBeNull();
  expect(aggregate.results[0].diagnostics[0].rule_id).toBe(
    "softschema.artifact.contract_unknown",
  );
});

test("single explicit file preserves legacy bytes with harmless batch flags", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const source = join(directory, "artifact.md");
  artifact(source, "  name: A\n  count: 1\n", true);

  expect(await main(argv("validate", source))).toBe(0);
  const legacy = captured();
  chunks = [];
  expect(await main(argv("validate", source, "--recursive", "--format", "json"))).toBe(0);

  expect(captured()).toBe(legacy);
  expect(legacy).not.toContain("diagnostic-v1");
});

test("a recursive directory yielding one file still selects diagnostic-v1", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const artifacts = join(directory, "artifacts");
  mkdirSync(artifacts);
  artifact(join(artifacts, "only.md"), "  name: A\n  count: 1\n", true);
  process.chdir(directory);

  expect(await main(argv("validate", "artifacts", "--recursive"))).toBe(0);
  expect(JSON.parse(captured()).format).toBe("diagnostic-v1");
});

test("invalid glob fails before reading or model import", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const model = join(directory, "must-not-load.mjs");
  const marker = join(directory, "loaded");
  writeFileSync(
    model,
    `import { writeFileSync } from "node:fs"; writeFileSync(${JSON.stringify(marker)}, "loaded"); export const Model = {};`,
  );

  expect(
    await main(
      argv(
        "validate",
        join(directory, "must-not-be-read"),
        "--recursive",
        "--include",
        "bad/**tail",
        "--model",
        `${model}:Model`,
      ),
    ),
  ).toBe(2);

  expect(captured()).toBe("");
  expect(capturedErrors()).toContain("partial_globstar");
  expect(existsSync(marker)).toBe(false);
});

test("SARIF output carries Unicode-code-point locations and invocation status", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const schemaPath = join(directory, "record.schema.yaml");
  const source = join(directory, "bad.md");
  schema(schemaPath);
  artifact(source, "  name: 😀\n  count: no\n");

  expect(
    await main(
      argv(
        "validate",
        source,
        "--contract",
        "test.batch:Record/v1",
        "--envelope",
        "record",
        "--schema",
        schemaPath,
        "--format",
        "sarif",
      ),
    ),
  ).toBe(1);

  const sarif = JSON.parse(captured()) as Record<string, any>;
  expect(sarif.version).toBe("2.1.0");
  expect(sarif.runs[0].columnKind).toBe("unicodeCodePoints");
  expect(sarif.runs[0].invocations[0]).toMatchObject({ executionSuccessful: true, exitCode: 1 });
  expect(sarif.runs[0].results[0].locations[0].physicalLocation.region).toEqual({
    startColumn: 10,
    startLine: 4,
  });
});

test("mixed parse, input, and valid results apply exit-two precedence", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  artifact(join(directory, "valid.md"), "  name: A\n  count: 1\n", true);
  writeFileSync(join(directory, "malformed.md"), "---\nrecord: [unterminated\n---\n");
  process.chdir(directory);

  expect(
    await main(
      argv(
        "validate",
        "valid.md",
        "malformed.md",
        "missing.md",
        "--contract",
        "test.batch:Record/v1",
        "--envelope",
        "record",
      ),
    ),
  ).toBe(2);

  const aggregate = JSON.parse(captured()) as Record<string, any>;
  expect(aggregate.summary).toEqual({
    exit_code: 2,
    input_failed: 1,
    passed: 1,
    total: 3,
    validation_failed: 1,
  });
  expect(aggregate.results.map((result: any) => result.outcome)).toEqual([
    "passed",
    "validation_failed",
    "input_failed",
  ]);
});

test("recursive profile include and exclude filters reach the CLI", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const keep = join(directory, "artifacts", "keep");
  const drop = join(directory, "artifacts", "drop");
  mkdirSync(keep, { recursive: true });
  mkdirSync(drop);
  artifact(join(keep, "selected.md"), "  name: A\n  count: 1\n", true);
  artifact(join(keep, "excluded.md"), "  name: B\n  count: 2\n", true);
  artifact(join(drop, "other.md"), "  name: C\n  count: 3\n", true);
  writeFileSync(join(keep, "wrong-profile.yaml"), "name: ignored\n");
  process.chdir(directory);

  expect(
    await main(
      argv(
        "validate",
        "artifacts",
        "--recursive",
        "--include",
        "keep/**",
        "--exclude",
        "**/excluded.md",
      ),
    ),
  ).toBe(0);

  const aggregate = JSON.parse(captured()) as Record<string, any>;
  expect(aggregate.results.map((result: any) => result.input.source)).toEqual([
    "artifacts/keep/selected.md",
  ]);
});

test("unsafe symlink-to-directory never enters the legacy reader", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  mkdirSync(join(directory, "target"));
  try {
    symlinkSync(join(directory, "target"), join(directory, "alias.md"), "dir");
  } catch {
    return;
  }
  process.chdir(directory);

  expect(await main(argv("validate", "alias.md"))).toBe(2);

  const aggregate = JSON.parse(captured()) as Record<string, any>;
  expect(aggregate.format).toBe("diagnostic-v1");
  expect(aggregate.results[0].input.reason).toBe("unreadable");
});

test("broken symlink and missing path retain legacy not_found compatibility", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  try {
    symlinkSync(join(directory, "target-missing.md"), join(directory, "broken.md"));
  } catch {
    return;
  }
  process.chdir(directory);

  for (const source of ["broken.md", "missing.md"]) {
    expect(
      await main(
        argv("validate", source, "--contract", "test.batch:Record/v1"),
      ),
    ).toBe(2);
    expect(JSON.parse(captured())).toEqual({
      kind: "input_error",
      message: "artifact path does not exist",
      reason: "not_found",
      source,
    });
    chunks = [];
  }
});

test("explicit schema diagnostics carry schema source coordinates", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  artifact(join(directory, "artifact.md"), "  name: A\n  count: 1\n", true);
  writeFileSync(
    join(directory, "bad.schema.yaml"),
    "$schema: https://example.invalid/schema\ntype: object\n",
  );
  process.chdir(directory);

  expect(
    await main(
      argv(
        "validate",
        "artifact.md",
        "--envelope",
        "record",
        "--schema",
        "bad.schema.yaml",
        "--format",
        "jsonl",
      ),
    ),
  ).toBe(1);

  const record = JSON.parse(captured()) as Record<string, any>;
  expect(record.result.diagnostics[0]).toMatchObject({
    schema_source: "bad.schema.yaml",
    schema_path: "/$schema",
    line: 1,
    column: 10,
  });
});

test("metadata schema source resolves relative to the artifact", async () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const documents = join(directory, "documents");
  mkdirSync(documents);
  writeFileSync(
    join(documents, "bad.schema.yaml"),
    "$schema: https://example.invalid/schema\ntype: object\n",
  );
  writeFileSync(
    join(documents, "artifact.md"),
    `---
softschema:
  contract: test.batch:Record/v1
  schema: bad.schema.yaml
  envelope: record
record:
  name: A
  count: 1
---
body
`,
  );
  process.chdir(directory);

  expect(
    await main(argv("validate", "documents/artifact.md", "--format", "jsonl")),
  ).toBe(1);

  const record = JSON.parse(captured()) as Record<string, any>;
  expect(record.result.diagnostics[0]).toMatchObject({
    schema_source: "documents/bad.schema.yaml",
    line: 1,
    column: 10,
  });
});

test("metadata schema symlinks cannot escape the document and working directories", async () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-batch-cli-"));
  const workspace = join(root, "workspace");
  const documents = join(workspace, "documents");
  const outside = join(root, "outside");
  mkdirSync(workspace);
  mkdirSync(documents);
  mkdirSync(outside);
  writeFileSync(join(outside, "outside.schema.yaml"), "type: object\n");
  symlinkSync(join(outside, "outside.schema.yaml"), join(documents, "linked.schema.yaml"));
  writeFileSync(
    join(documents, "artifact.md"),
    `---
softschema:
  contract: test.batch:Record/v1
  schema: linked.schema.yaml
  envelope: record
record:
  name: A
  count: 1
---
body
`,
  );
  process.chdir(workspace);

  expect(
    await main(argv("validate", "documents/artifact.md", "--format", "jsonl")),
  ).toBe(1);

  const record = JSON.parse(captured()) as Record<string, any>;
  expect(record.result.diagnostics[0]).toMatchObject({
    category: "structural",
    column: 11,
    line: 4,
    message: "compiled schema is unavailable",
    path: "/softschema/schema",
    rule_id: "softschema.artifact.schema_missing",
    source: "documents/artifact.md",
  });
});
