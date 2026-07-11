/** Shared diagnostic-v1, JSONL, and SARIF projection vectors. */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, test } from "bun:test";
import { canonicalJson } from "../src/core/canonical-json.js";
import {
  type DiagnosticAggregateV1,
  type DiagnosticLimitsWire,
  type DiagnosticResultV1,
  type DiagnosticSummaryV1,
  type DiagnosticValidationWire,
  diagnosticRuleId,
  projectDiagnosticAggregate,
  projectDiagnosticResult,
  projectDiagnosticSarif,
  projectValidationWire,
  serializeDiagnosticJsonl,
} from "../src/core/diagnostics.js";
import type { JsonObject, JsonValue, ValidationLimits } from "../src/core/value-domain.js";
import type { SchemaProfile } from "../src/models.js";
import type { ValidationResultLegacyWire } from "../src/core/results.js";
import { loadYamlFixture } from "./yaml-fixture.js";

const ROOT = resolve(import.meta.dir, "../../..");
const DIAGNOSTICS = join(ROOT, "tests", "diagnostics");

interface AggregateVector {
  id: string;
  result_ids: string[];
  summary: DiagnosticSummaryV1;
}

interface WireVectors {
  format: "diagnostic-v1";
  profile: SchemaProfile;
  limits: DiagnosticLimitsWire;
  results: Record<string, DiagnosticResultV1>;
  aggregates: AggregateVector[];
}

interface SarifVector {
  id: string;
  aggregate_id: string;
  sarif: JsonObject;
}

interface SarifVectors {
  schema: { path: string; source: string; sha256: string };
  vectors: SarifVector[];
}

const wire = loadYamlFixture<WireVectors>(join(DIAGNOSTICS, "wire-vectors.yaml"));
const sarifVectors = loadYamlFixture<SarifVectors>(join(DIAGNOSTICS, "sarif-vectors.yaml"));

function runtimeLimits(limits: DiagnosticLimitsWire): ValidationLimits {
  return {
    maxResourceBytes: limits.max_resource_bytes,
    maxBundleBytes: limits.max_bundle_bytes,
    maxResources: limits.max_resources,
    maxNodesPerResource: limits.max_nodes_per_resource,
    maxDepth: limits.max_depth,
    maxScalarCodePoints: limits.max_scalar_codepoints,
  };
}

function aggregate(aggregateId: string): DiagnosticAggregateV1 {
  const vector = wire.aggregates.find((item) => item.id === aggregateId);
  if (vector === undefined) throw new Error(`missing aggregate vector: ${aggregateId}`);
  const results = vector.result_ids.map((id) => {
    const result = wire.results[id];
    if (result === undefined) throw new Error(`missing result vector: ${id}`);
    return result;
  });
  return projectDiagnosticAggregate(wire.profile, runtimeLimits(wire.limits), results);
}

function objectArray(value: JsonValue | undefined, field: string): JsonObject[] {
  if (!Array.isArray(value) || value.some((item) => item === null || Array.isArray(item) || typeof item !== "object")) {
    throw new Error(`${field} must be an object array`);
  }
  return value as JsonObject[];
}

function firstRun(log: JsonObject): JsonObject {
  const runs = objectArray(log.runs, "runs");
  const run = runs[0];
  if (run === undefined) throw new Error("SARIF log has no run");
  return run;
}

describe("diagnostic-v1 wire projection", () => {
  test("projects exact summaries, JSONL records, and exit precedence", () => {
    for (const vector of wire.aggregates) {
      const actual = aggregate(vector.id);
      expect(actual.summary).toEqual(vector.summary);
      expect(actual.ok).toBe(vector.summary.exit_code === 0);

      const jsonl = serializeDiagnosticJsonl(actual);
      expect(jsonl.endsWith("\n")).toBe(true);
      const lines = jsonl.slice(0, -1).split("\n");
      expect(lines).toHaveLength(vector.result_ids.length);
      for (const [index, line] of lines.entries()) {
        const record = JSON.parse(line) as Record<string, unknown>;
        expect(record).toEqual({
          format: "diagnostic-v1",
          profile: wire.profile,
          limits: wire.limits,
          result: actual.results[index],
        });
        expect(record).not.toHaveProperty("summary");
        expect(line).toBe(canonicalJson(record));
      }
    }

    expect(aggregate("input-precedence-exit-2").summary).toMatchObject({
      input_failed: 3,
      exit_code: 2,
    });
    expect(
      aggregate("unicode-code-point-order").results[0]?.diagnostics.map(
        (diagnostic) => diagnostic.path,
      ),
    ).toEqual(["/", "/𐀀"]);
  });

  test("derives result outcomes and removes legacy duplication", () => {
    for (const expected of Object.values(wire.results)) {
      expect(
        projectDiagnosticResult(expected.input, expected.validation, expected.diagnostics),
      ).toEqual(expected);
    }

    const expected = wire.results.passed?.validation;
    if (expected === undefined || expected === null) throw new Error("missing validation vector");
    const legacy: ValidationResultLegacyWire = {
      ...expected,
      path: "artifacts/valid movie.md",
      profile: "frontmatter-md",
      values: { movie: { title: "Arrival", year: 2016 } },
      warnings: [],
    };
    expect(projectValidationWire(legacy)).toEqual(expected);
    expect(diagnosticRuleId("schema_violation", "$Ref")).toBe(
      "softschema.schema_violation.ref",
    );
  });

  test("deeply isolates projected validation and result wire values", () => {
    const source = JSON.parse(JSON.stringify(wire.results.structural)) as DiagnosticResultV1;
    if (
      source.input.kind !== "artifact_input" ||
      source.validation === null ||
      source.validation.document_metadata === null
    ) {
      throw new Error("structural mutation vector is incomplete");
    }
    source.validation.document_metadata.extensions = {
      "example.test": { nested: [{ label: "original" }] },
    };
    const structuralIssue = source.validation.structural.errors[0] as unknown as Record<
      string,
      JsonValue | undefined
    >;
    structuralIssue.context = { nested: [{ label: "original" }] };
    const legacy: ValidationResultLegacyWire = {
      ...source.validation,
      path: source.input.source,
      profile: source.input.profile,
      values: source.input.values,
      warnings: [],
    };

    const projectedValidation = projectValidationWire(legacy);
    const result = projectDiagnosticResult(
      source.input,
      projectedValidation,
      source.diagnostics,
    );
    const projectedBefore = canonicalJson(projectedValidation);
    const resultBefore = canonicalJson(result);

    const movie = source.input.values.movie as JsonObject;
    movie.year = 2049;
    const extension = source.validation.document_metadata.extensions["example.test"] as JsonObject;
    ((extension.nested as JsonValue[])[0] as JsonObject).label = "mutated-source";
    ((structuralIssue.context as JsonObject).nested as JsonValue[]).push("mutated-source");
    (structuralIssue.validator_value as JsonValue[]).push("mutated-source");

    expect(canonicalJson(projectedValidation)).toBe(projectedBefore);
    expect(canonicalJson(result)).toBe(resultBefore);

    const projectedMetadata = projectedValidation.document_metadata;
    if (projectedMetadata?.extensions === undefined) {
      throw new Error("projected extensions are missing");
    }
    const projectedExtension = projectedMetadata.extensions["example.test"] as JsonObject;
    ((projectedExtension.nested as JsonValue[])[0] as JsonObject).label = "mutated-projection";
    const projectedIssue = projectedValidation.structural.errors[0] as unknown as Record<
      string,
      JsonValue | undefined
    >;
    ((projectedIssue.context as JsonObject).nested as JsonValue[]).push("mutated-projection");

    expect(canonicalJson(result)).toBe(resultBefore);
  });

  test("wire cloning rejects accessors without invoking them", () => {
    const source = JSON.parse(JSON.stringify(wire.results.structural)) as DiagnosticResultV1;
    if (source.validation === null) throw new Error("structural mutation vector is incomplete");
    let getterCalls = 0;
    const accessorValue = {};
    Object.defineProperty(accessorValue, "nested", {
      enumerable: true,
      get: () => {
        getterCalls += 1;
        return "not portable";
      },
    });
    const structuralIssue = source.validation.structural.errors[0] as unknown as Record<
      string,
      JsonValue | undefined
    >;
    structuralIssue.context = accessorValue as JsonObject;

    expect(() =>
      projectDiagnosticResult(source.input, source.validation, source.diagnostics),
    ).toThrow("own data properties");
    expect(getterCalls).toBe(0);
  });

  test("rejects invalid profiles, mismatched sources, and stale summaries", () => {
    const passed = wire.results.passed;
    const binding = wire.results.binding;
    if (passed === undefined || binding === undefined) throw new Error("missing wire vector");
    expect(() =>
      projectDiagnosticAggregate(
        "invalid-profile" as SchemaProfile,
        runtimeLimits(wire.limits),
        [passed],
      ),
    ).toThrow("diagnostic profile");

    const input = binding.input;
    const diagnostic = binding.diagnostics[0];
    if (diagnostic === undefined) throw new Error("missing binding diagnostic");
    expect(() =>
      projectDiagnosticResult(input, null, [{ ...diagnostic, source: "other.md" }]),
    ).toThrow("source must match");

    const stale = aggregate("success");
    stale.summary.exit_code = 1;
    expect(() => serializeDiagnosticJsonl(stale)).toThrow("summary does not match");
  });
});

describe("SARIF projection", () => {
  test("matches shared vectors and pinned OASIS fixture digest", () => {
    const fixture = readFileSync(join(DIAGNOSTICS, sarifVectors.schema.path));
    expect(createHash("sha256").update(fixture).digest("hex")).toBe(
      "c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e",
    );
    expect(sarifVectors.schema.sha256).toBe(
      "c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e",
    );

    for (const vector of sarifVectors.vectors) {
      expect(projectDiagnosticSarif(aggregate(vector.aggregate_id))).toEqual(vector.sarif);
    }
  });

  test("uses sorted rules, stable indexes, code-point columns, and honest invocation state", () => {
    const exitOne = projectDiagnosticSarif(aggregate("validation-exit-1"));
    const exitTwo = projectDiagnosticSarif(aggregate("input-precedence-exit-2"));
    const run = firstRun(exitOne);
    const driver = (run.tool as JsonObject).driver as JsonObject;
    const rules = driver.rules as JsonObject[];
    const ruleIds = rules.map((rule) => rule.id as string);
    expect(ruleIds).toEqual([...ruleIds].sort());
    expect(run.columnKind).toBe("unicodeCodePoints");
    for (const result of run.results as JsonObject[]) {
      expect(ruleIds[result.ruleIndex as number]).toBe(result.ruleId as string);
    }
    expect(run.invocations).toEqual([{ executionSuccessful: true, exitCode: 1 }]);
    expect(firstRun(exitTwo).invocations).toEqual([
      { executionSuccessful: false, exitCode: 2 },
    ]);
  });
});
