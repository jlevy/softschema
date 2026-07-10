import { expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import type { SourceSpan } from "../src/core/source-map.js";
import {
  type JsonValue,
  parsePortableYamlWithLocations,
  PortableValueError,
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

interface FirstErrorVector {
  id: string;
  yaml: string;
  limits?: { max_nodes_per_resource?: number; max_depth?: number };
  message: string;
  path: string;
  line: number;
  column: number;
}

interface SyntaxClassificationVector {
  id: string;
  yaml: string;
  limits?: { max_nodes_per_resource?: number; max_depth?: number };
  kind: "syntax" | "value";
  message: string;
  path: string;
  line: number;
  column: number;
}

interface YamlParityEdgeVectors {
  compact_flow_policy: {
    message: string;
    rejected: RejectedCompactFlowVector[];
    accepted: AcceptedCompactFlowVector[];
  };
  composer_syntax_errors: ComposerSyntaxVector[];
  flow_opener_comment_policy: {
    message: string;
    rejected: RejectedCompactFlowVector[];
    accepted: AcceptedCompactFlowVector[];
  };
  tag_directive_policy: {
    accepted: AcceptedCompactFlowVector[];
    rejected: {
      id: string;
      yaml: string;
      message: string;
      path: string;
      line: number;
      column: number;
    }[];
    syntax_rejected: {
      id: string;
      yaml: string;
      message: string;
      path: string;
      line: number;
      column: number;
    }[];
  };
  explicit_numeric_tags: {
    accepted: AcceptedCompactFlowVector[];
    rejected: {
      id: string;
      yaml: string;
      message: string;
      path: string;
      line: number;
      column: number;
    }[];
  };
  first_error_precedence: FirstErrorVector[];
  syntax_classification: SyntaxClassificationVector[];
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

test("flow opener comments require separation in both runtimes", () => {
  const policy = VECTORS.flow_opener_comment_policy;
  for (const vector of policy.rejected) {
    try {
      parsePortableYamlWithLocations(vector.yaml);
      throw new Error(`expected ${vector.id} to fail`);
    } catch (error) {
      expect(error, vector.id).toBeInstanceOf(PortableYamlSyntaxError);
      expect((error as PortableYamlSyntaxError).message, vector.id).toBe(policy.message);
      expect(
        {
          line: (error as PortableYamlSyntaxError).line,
          column: (error as PortableYamlSyntaxError).column,
        },
        vector.id,
      ).toEqual({ line: vector.line, column: vector.column });
    }
  }

  for (const vector of policy.accepted) {
    expect(parsePortableYamlWithLocations(vector.yaml).value, vector.id).toEqual(vector.value);
  }
});

test("tag directives expand before portable tag classification", () => {
  for (const vector of VECTORS.tag_directive_policy.accepted) {
    expect(parsePortableYamlWithLocations(vector.yaml).value, vector.id).toEqual(vector.value);
  }
  for (const vector of VECTORS.tag_directive_policy.rejected) {
    try {
      parsePortableYamlWithLocations(vector.yaml);
      throw new Error(`expected ${vector.id} to fail`);
    } catch (error) {
      expect(error, vector.id).toBeInstanceOf(PortableValueError);
      expect(error, vector.id).toMatchObject({
        message: vector.message,
        path: vector.path,
        line: vector.line,
        column: vector.column,
      });
    }
  }
  for (const vector of VECTORS.tag_directive_policy.syntax_rejected) {
    try {
      parsePortableYamlWithLocations(vector.yaml);
      throw new Error(`expected ${vector.id} to fail`);
    } catch (error) {
      expect(error, vector.id).toBeInstanceOf(PortableYamlSyntaxError);
      expect(error, vector.id).toMatchObject({
        message: vector.message,
        path: vector.path,
        line: vector.line,
        column: vector.column,
      });
    }
  }
});

test("explicit numeric tags use the shared portable grammar", () => {
  for (const vector of VECTORS.explicit_numeric_tags.accepted) {
    expect(parsePortableYamlWithLocations(vector.yaml).value, vector.id).toEqual(vector.value);
  }
  for (const vector of VECTORS.explicit_numeric_tags.rejected) {
    try {
      parsePortableYamlWithLocations(vector.yaml);
      throw new Error(`expected ${vector.id} to fail`);
    } catch (error) {
      expect(error, vector.id).toBeInstanceOf(PortableValueError);
      expect(error, vector.id).toMatchObject({
        message: vector.message,
        path: vector.path,
        line: vector.line,
        column: vector.column,
      });
    }
  }
});

test("semantic and resource failures follow shared event order", () => {
  for (const vector of VECTORS.first_error_precedence) {
    const limits: { maxNodesPerResource?: number; maxDepth?: number } = {};
    if (vector.limits?.max_nodes_per_resource !== undefined) {
      limits.maxNodesPerResource = vector.limits.max_nodes_per_resource;
    }
    if (vector.limits?.max_depth !== undefined) limits.maxDepth = vector.limits.max_depth;
    try {
      parsePortableYamlWithLocations(vector.yaml, limits);
      throw new Error(`expected ${vector.id} to fail`);
    } catch (error) {
      expect(error, vector.id).toBeInstanceOf(PortableValueError);
      expect(error, vector.id).toMatchObject({
        message: vector.message,
        path: vector.path,
        line: vector.line,
        column: vector.column,
      });
    }
  }
});

test("document and empty-key edges use shared syntax classifications", () => {
  for (const vector of VECTORS.syntax_classification) {
    const limits: { maxNodesPerResource?: number; maxDepth?: number } = {};
    if (vector.limits?.max_nodes_per_resource !== undefined) {
      limits.maxNodesPerResource = vector.limits.max_nodes_per_resource;
    }
    if (vector.limits?.max_depth !== undefined) limits.maxDepth = vector.limits.max_depth;
    try {
      parsePortableYamlWithLocations(vector.yaml, limits);
      throw new Error(`expected ${vector.id} to fail`);
    } catch (error) {
      expect(error, vector.id).toBeInstanceOf(
        vector.kind === "syntax" ? PortableYamlSyntaxError : PortableValueError,
      );
      expect(error, vector.id).toMatchObject({
        message: vector.message,
        path: vector.path,
        line: vector.line,
        column: vector.column,
      });
    }
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
