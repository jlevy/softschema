import { expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import type { SourceSpan } from "../src/core/source-map.js";
import {
  type JsonValue,
  parsePortableYamlWithLocations,
  PortableYamlSyntaxError,
} from "../src/yaml-value-domain.js";

interface PlainPoint {
  line: number;
  column: number;
}

interface PlainSpan {
  start: PlainPoint;
  end: PlainPoint;
}

interface RejectedCompactFlowVector {
  id: string;
  yaml: string;
  line: number;
  column: number;
}

interface AcceptedCompactFlowVector {
  id: string;
  yaml: string;
  value: JsonValue;
}

interface ComposerSyntaxVector {
  id: string;
  yaml: string;
  message: string;
  line: number;
  column: number;
  cli: { kind: string; reason: string; message: string; exit_code: number };
}

interface EmptyNullAnchorVector {
  id: string;
  yaml: string;
  value: JsonValue;
  anchors: { pointer: string; span: PlainSpan }[];
  diagnostic?: { path: string; line: number; column: number };
}

interface YamlParityEdgeVectors {
  compact_flow_policy: {
    message: string;
    rejected: RejectedCompactFlowVector[];
    accepted: AcceptedCompactFlowVector[];
  };
  composer_syntax_errors: ComposerSyntaxVector[];
  empty_null_anchors: EmptyNullAnchorVector[];
}

const ROOT = resolve(import.meta.dir, "../../..");
const CLI = resolve(ROOT, "packages/typescript/src/cli.ts");
const VECTORS = JSON.parse(
  readFileSync(resolve(ROOT, "tests/value-domain/yaml-parity-edge-vectors.json"), "utf8"),
) as YamlParityEdgeVectors;

function span(value: SourceSpan): PlainSpan {
  return {
    start: { line: value.start.line, column: value.start.column },
    end: { line: value.end.line, column: value.end.column },
  };
}

test("plain compact flow colons follow the shared portable policy", () => {
  const policy = VECTORS.compact_flow_policy;
  for (const vector of policy.rejected) {
    let caught: unknown;
    try {
      parsePortableYamlWithLocations(vector.yaml);
    } catch (error) {
      caught = error;
    }

    expect(caught, vector.id).toBeInstanceOf(PortableYamlSyntaxError);
    const located = caught as PortableYamlSyntaxError;
    expect(located.message, vector.id).toBe(policy.message);
    expect({ line: located.line, column: located.column }, vector.id).toEqual({
      line: vector.line,
      column: vector.column,
    });
  }

  for (const vector of policy.accepted) {
    expect(parsePortableYamlWithLocations(vector.yaml).value, vector.id).toEqual(vector.value);
  }

  expect(() =>
    parsePortableYamlWithLocations("[a:]", { maxNodesPerResource: 1 }),
  ).toThrow(PortableYamlSyntaxError);
});

test("yaml parser exceptions with codes become portable syntax errors", () => {
  for (const vector of VECTORS.composer_syntax_errors) {
    let caught: unknown;
    try {
      parsePortableYamlWithLocations(vector.yaml);
    } catch (error) {
      caught = error;
    }

    expect(caught, vector.id).toBeInstanceOf(PortableYamlSyntaxError);
    const located = caught as PortableYamlSyntaxError;
    expect(located.message, vector.id).toBe(vector.message);
    expect({ line: located.line, column: located.column }, vector.id).toEqual({
      line: vector.line,
      column: vector.column,
    });
  }
});

test("empty null nodes use shared boundary anchors", () => {
  for (const vector of VECTORS.empty_null_anchors) {
    const parsed = parsePortableYamlWithLocations(vector.yaml);

    expect(parsed.value, vector.id).toEqual(vector.value);
    for (const expected of vector.anchors) {
      const node = parsed.sourceMap.node(expected.pointer);
      if (node === undefined) throw new Error(`missing source node ${expected.pointer}`);
      expect(span(node.value), `${vector.id}:${expected.pointer}`).toEqual(expected.span);
    }
  }
});

test("empty null anchor reaches CLI diagnostics", () => {
  const vector = VECTORS.empty_null_anchors.find((item) => item.diagnostic !== undefined);
  if (vector?.diagnostic === undefined) throw new Error("diagnostic anchor vector missing");
  const directory = mkdtempSync(join(tmpdir(), "softschema-empty-null-"));
  const source = join(directory, "empty-null.yaml");
  const schema = join(directory, "empty-null.schema.yaml");
  writeFileSync(source, new TextEncoder().encode(vector.yaml));
  writeFileSync(
    schema,
    `$schema: https://json-schema.org/draft/2020-12/schema
type: object
properties:
  values:
    type: array
    items: {type: string}
required: [values]
`,
    "utf8",
  );

  const child = Bun.spawnSync({
    cmd: [
      process.execPath,
      CLI,
      "validate",
      source,
      "--profile",
      "pure-yaml",
      "--contract",
      "example:Value/v1",
      "--schema",
      schema,
      "--format",
      "jsonl",
    ],
    stderr: "pipe",
    stdout: "pipe",
  });

  const result = JSON.parse(child.stdout.toString()) as {
    result: { diagnostics: Record<string, unknown>[] };
  };
  expect(child.exitCode).toBe(1);
  expect(child.stderr.toString()).toBe("");
  expect(result.result.diagnostics[0]).toMatchObject(vector.diagnostic);
});

test("coded YAML parser error is a CLI parse_error", () => {
  const vector = VECTORS.composer_syntax_errors[0];
  if (vector === undefined) throw new Error("composer syntax vector missing");
  const directory = mkdtempSync(join(tmpdir(), "softschema-coded-yaml-error-"));
  const source = join(directory, "coded-parser-error.yaml");
  writeFileSync(source, vector.yaml, "utf8");

  const child = Bun.spawnSync({
    cmd: [
      process.execPath,
      CLI,
      "validate",
      source,
      "--profile",
      "pure-yaml",
      "--contract",
      "example:Value/v1",
    ],
    stderr: "pipe",
    stdout: "pipe",
  });

  const record = JSON.parse(child.stdout.toString()) as Record<string, unknown>;
  expect(child.exitCode).toBe(vector.cli.exit_code);
  expect(child.stderr.toString()).toBe("");
  expect(record.kind).toBe(vector.cli.kind);
  expect(record.reason).toBe(vector.cli.reason);
  expect(record.message).toBe(vector.cli.message);
});
