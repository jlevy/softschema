/** Pure diagnostic-v1, JSONL, and SARIF wire projections. */

import type { SchemaProfile, SchemaStatus } from "../models.js";
import { canonicalJson, compareUnicodeCodePoints } from "./canonical-json.js";
import type {
  ArtifactInputResult,
  SemanticResult,
  StructuralResult,
  ValidationResultLegacyWire,
} from "./results.js";
import type { JsonObject, ValidationLimits } from "./value-domain.js";

export const DIAGNOSTIC_FORMAT = "diagnostic-v1" as const;
export const SARIF_SCHEMA_URI =
  "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json";
export const SARIF_VERSION = "2.1.0" as const;

const MAX_SORT_COORDINATE = Number.MAX_SAFE_INTEGER;
const RULE_CODE_PATTERN = /[^a-z0-9_.-]+/g;

export type DiagnosticCategory =
  | "input"
  | "parse"
  | "binding"
  | "schema"
  | "structural"
  | "semantic"
  | "warning";
export type DiagnosticSeverity = "error" | "warning" | "info";
export type DiagnosticOutcome = "passed" | "validation_failed" | "input_failed";
export type DiagnosticRuleFamily =
  | "input_error"
  | "parse_error"
  | "schema_invalid"
  | "schema_violation"
  | "artifact"
  | "semantic"
  | "warning";

/** Snake-case validation budgets embedded in diagnostic wire records. */
export interface DiagnosticLimitsWire {
  max_resource_bytes: number;
  max_bundle_bytes: number;
  max_resources: number;
  max_nodes_per_resource: number;
  max_depth: number;
  max_scalar_codepoints: number;
}

/** One normalized, source-positioned diagnostic. */
export interface DiagnosticV1 {
  category: DiagnosticCategory;
  rule_id: string;
  severity: DiagnosticSeverity;
  message: string;
  source: string;
  path?: string;
  schema_source?: string;
  schema_path?: string;
  line?: number;
  column?: number;
}

/** Warning retained in the de-duplicated validation payload. */
export interface DiagnosticWarningWire {
  code: string;
  message: string;
  severity: "info" | "warning";
}

/** Legacy validation payload without duplicated source, values, or profile fields. */
export interface DiagnosticValidationWire {
  contract: ValidationResultLegacyWire["contract"];
  contract_id: string;
  document_metadata: ValidationResultLegacyWire["document_metadata"];
  semantic: SemanticResult;
  status: SchemaStatus;
  structural: StructuralResult;
  warnings: DiagnosticWarningWire[];
}

/** One diagnostic-v1 artifact result. */
export interface DiagnosticResultV1 {
  outcome: DiagnosticOutcome;
  input: ArtifactInputResult;
  validation: DiagnosticValidationWire | null;
  diagnostics: DiagnosticV1[];
}

/** Exact partition and process exit for one diagnostic aggregate. */
export interface DiagnosticSummaryV1 {
  total: number;
  passed: number;
  validation_failed: number;
  input_failed: number;
  exit_code: 0 | 1 | 2;
}

/** Versioned multi-artifact diagnostic wire result. */
export interface DiagnosticAggregateV1 {
  format: typeof DIAGNOSTIC_FORMAT;
  profile: SchemaProfile;
  limits: DiagnosticLimitsWire;
  ok: boolean;
  results: DiagnosticResultV1[];
  summary: DiagnosticSummaryV1;
}

/** Self-describing JSONL envelope for one artifact result. */
export interface DiagnosticJsonlRecordV1 {
  format: typeof DIAGNOSTIC_FORMAT;
  profile: SchemaProfile;
  limits: DiagnosticLimitsWire;
  result: DiagnosticResultV1;
}

/** Build a stable lowercase rule identifier from a portable issue code. */
export function diagnosticRuleId(family: DiagnosticRuleFamily, code: string): string {
  const normalized = code
    .toLowerCase()
    .replace(/^\$/, "")
    .replace(RULE_CODE_PATTERN, "_")
    .replace(/^[_.-]+|[_.-]+$/g, "");
  if (normalized.length === 0) {
    throw new Error("diagnostic rule code must contain an ASCII letter or digit");
  }
  return `softschema.${family}.${normalized}`;
}

/** Project runtime validation budgets to their exact snake-case wire spelling. */
export function validationLimitsWire(limits: ValidationLimits): DiagnosticLimitsWire {
  return {
    max_resource_bytes: limits.maxResourceBytes,
    max_bundle_bytes: limits.maxBundleBytes,
    max_resources: limits.maxResources,
    max_nodes_per_resource: limits.maxNodesPerResource,
    max_depth: limits.maxDepth,
    max_scalar_codepoints: limits.maxScalarCodePoints,
  };
}

/** Remove legacy path/value/profile duplication from a validation wire payload. */
export function projectValidationWire(
  validation: ValidationResultLegacyWire,
): DiagnosticValidationWire {
  return cloneWireValue({
    contract: dataProperty(validation, "contract"),
    contract_id: dataProperty(validation, "contract_id"),
    document_metadata: dataProperty(validation, "document_metadata"),
    semantic: dataProperty(validation, "semantic"),
    status: dataProperty(validation, "status"),
    structural: dataProperty(validation, "structural"),
    warnings: dataProperty(validation, "warnings"),
  });
}

/** Build one result and derive its outcome from discriminated input/validation state. */
export function projectDiagnosticResult(
  input: ArtifactInputResult,
  validation: DiagnosticValidationWire | null,
  diagnostics: readonly DiagnosticV1[],
): DiagnosticResultV1 {
  const normalizedInput = cloneInput(input);
  const normalizedValidation = cloneValidation(validation);
  const normalizedDiagnostics = normalizedDiagnosticsFor(normalizedInput.source, diagnostics);
  return {
    outcome: resultOutcome(normalizedInput, normalizedValidation, normalizedDiagnostics),
    input: normalizedInput,
    validation: normalizedValidation,
    diagnostics: normalizedDiagnostics,
  };
}

/** Build an aggregate with an exact result partition and 2 > 1 > 0 exit precedence. */
export function projectDiagnosticAggregate(
  profile: SchemaProfile,
  limits: ValidationLimits,
  results: readonly DiagnosticResultV1[],
): DiagnosticAggregateV1 {
  if (results.length === 0) throw new Error("diagnostic aggregate requires at least one result");
  if (profile !== "frontmatter-md" && profile !== "pure-yaml") {
    throw new Error("diagnostic profile must be frontmatter-md or pure-yaml");
  }
  const normalizedResults = results.map(normalizeResult);
  const passed = normalizedResults.filter((result) => result.outcome === "passed").length;
  const validationFailed = normalizedResults.filter(
    (result) => result.outcome === "validation_failed",
  ).length;
  const inputFailed = normalizedResults.filter(
    (result) => result.outcome === "input_failed",
  ).length;
  const exitCode: 0 | 1 | 2 = inputFailed > 0 ? 2 : validationFailed > 0 ? 1 : 0;
  return {
    format: DIAGNOSTIC_FORMAT,
    profile,
    limits: validationLimitsWire(limits),
    ok: exitCode === 0,
    results: normalizedResults,
    summary: {
      total: normalizedResults.length,
      passed,
      validation_failed: validationFailed,
      input_failed: inputFailed,
      exit_code: exitCode,
    },
  };
}

/** Serialize one compact, sorted, self-describing line per result and no summary. */
export function serializeDiagnosticJsonl(aggregate: DiagnosticAggregateV1): string {
  assertAggregateSummary(aggregate);
  return `${aggregate.results
    .map((result) =>
      canonicalJson({
        format: DIAGNOSTIC_FORMAT,
        profile: aggregate.profile,
        limits: aggregate.limits,
        result,
      } satisfies DiagnosticJsonlRecordV1),
    )
    .join("\n")}\n`;
}

/** Project diagnostic-v1 into deterministic SARIF 2.1.0 Errata 01 JSON. */
export function projectDiagnosticSarif(aggregate: DiagnosticAggregateV1): JsonObject {
  assertAggregateSummary(aggregate);
  const diagnostics = aggregate.results.flatMap((result) =>
    result.diagnostics.map((diagnostic) => ({ outcome: result.outcome, diagnostic })),
  );
  const ruleIds = [...new Set(diagnostics.map(({ diagnostic }) => diagnostic.rule_id))].sort(
    compareUnicodeCodePoints,
  );
  const ruleIndexes = new Map(ruleIds.map((ruleId, index) => [ruleId, index]));
  const artifactSources = new Set(aggregate.results.map((result) => result.input.source));
  const schemaSources = new Set<string>();
  for (const { diagnostic } of diagnostics) {
    if (diagnostic.schema_source !== undefined) schemaSources.add(diagnostic.schema_source);
  }
  const sources = new Set([...artifactSources, ...schemaSources]);
  const artifacts = [...sources]
    .map((source) => ({ source, uri: artifactUri(source, schemaSources.has(source)) }))
    .sort(
      (left, right) =>
        compareUnicodeCodePoints(left.uri, right.uri) ||
        compareUnicodeCodePoints(left.source, right.source),
    );
  const artifactIndexes = new Map(artifacts.map(({ source }, index) => [source, index]));
  const sarifResults = diagnostics.map(({ outcome, diagnostic }) =>
    sarifResult(outcome, diagnostic, ruleIndexes, artifactIndexes),
  );
  const run: JsonObject = {
    tool: {
      driver: {
        name: "softschema",
        informationUri: "https://github.com/jlevy/softschema",
        rules: ruleIds.map((id) => ({ id })),
      },
    },
    invocations: [
      {
        executionSuccessful: aggregate.summary.exit_code !== 2,
        exitCode: aggregate.summary.exit_code,
      },
    ],
    artifacts: artifacts.map(({ uri }) => ({ location: { uri } })),
    results: sarifResults,
    columnKind: "unicodeCodePoints",
    properties: {
      softschemaFormat: DIAGNOSTIC_FORMAT,
      softschemaProfile: aggregate.profile,
      softschemaLimits: limitsJson(aggregate.limits),
      softschemaSummary: summaryJson(aggregate.summary),
    },
  };
  return {
    $schema: SARIF_SCHEMA_URI,
    version: SARIF_VERSION,
    runs: [run],
  };
}

function normalizedDiagnosticsFor(
  source: string,
  diagnostics: readonly DiagnosticV1[],
): DiagnosticV1[] {
  const copied = diagnostics.map((diagnostic) => cloneWireValue(diagnostic));
  for (const diagnostic of copied) {
    if (diagnostic.source !== source) throw new Error("diagnostic source must match input.source");
    if (diagnostic.column !== undefined && diagnostic.line === undefined) {
      throw new Error("diagnostic column requires line");
    }
  }
  return copied.sort(compareDiagnostics);
}

function compareDiagnostics(left: DiagnosticV1, right: DiagnosticV1): number {
  return (
    compareUnicodeCodePoints(
      left.schema_source ?? left.source,
      right.schema_source ?? right.source,
    ) ||
    (left.line ?? MAX_SORT_COORDINATE) - (right.line ?? MAX_SORT_COORDINATE) ||
    (left.column ?? MAX_SORT_COORDINATE) - (right.column ?? MAX_SORT_COORDINATE) ||
    compareUnicodeCodePoints(left.rule_id, right.rule_id) ||
    compareUnicodeCodePoints(left.path ?? "", right.path ?? "") ||
    compareUnicodeCodePoints(left.schema_path ?? "", right.schema_path ?? "") ||
    compareUnicodeCodePoints(left.message, right.message) ||
    compareUnicodeCodePoints(left.severity, right.severity)
  );
}

function resultOutcome(
  input: ArtifactInputResult,
  validation: DiagnosticValidationWire | null,
  diagnostics: readonly DiagnosticV1[],
): DiagnosticOutcome {
  const errors = diagnostics.filter((diagnostic) => diagnostic.severity === "error");
  switch (input.kind) {
    case "input_error":
      if (validation !== null) throw new Error("input failure cannot contain validation");
      if (!errors.some((diagnostic) => diagnostic.category === "input")) {
        throw new Error("input failure requires an input error diagnostic");
      }
      return "input_failed";
    case "parse_error":
      if (validation !== null) throw new Error("parse failure cannot contain validation");
      if (!errors.some((diagnostic) => diagnostic.category === "parse")) {
        throw new Error("parse failure requires a parse error diagnostic");
      }
      return "validation_failed";
    case "artifact_input": {
      if (validation === null) {
        if (!errors.some((diagnostic) => diagnostic.category === "binding")) {
          throw new Error("unbound artifact requires a binding error diagnostic");
        }
        return "validation_failed";
      }
      const validationOk = validation.structural.ok && validation.semantic.ok;
      if (validationOk) {
        if (errors.length > 0)
          throw new Error("passed validation cannot contain error diagnostics");
        return "passed";
      }
      if (errors.length === 0) throw new Error("failed validation requires an error diagnostic");
      return "validation_failed";
    }
    default: {
      const exhaustive: never = input;
      throw new Error(`unsupported artifact input: ${String(exhaustive)}`);
    }
  }
}

function normalizeResult(result: DiagnosticResultV1): DiagnosticResultV1 {
  const copied = cloneWireValue(result);
  const diagnostics = normalizedDiagnosticsFor(copied.input.source, copied.diagnostics);
  const expected = resultOutcome(copied.input, copied.validation, diagnostics);
  if (copied.outcome !== expected) throw new Error(`result outcome must be ${expected}`);
  return {
    outcome: copied.outcome,
    input: copied.input,
    validation: copied.validation,
    diagnostics,
  };
}

function assertAggregateSummary(aggregate: DiagnosticAggregateV1): void {
  const limits: ValidationLimits = {
    maxResourceBytes: aggregate.limits.max_resource_bytes,
    maxBundleBytes: aggregate.limits.max_bundle_bytes,
    maxResources: aggregate.limits.max_resources,
    maxNodesPerResource: aggregate.limits.max_nodes_per_resource,
    maxDepth: aggregate.limits.max_depth,
    maxScalarCodePoints: aggregate.limits.max_scalar_codepoints,
  };
  const rebuilt = projectDiagnosticAggregate(aggregate.profile, limits, aggregate.results);
  if (
    canonicalJson(rebuilt.summary) !== canonicalJson(aggregate.summary) ||
    rebuilt.ok !== aggregate.ok
  ) {
    throw new Error("diagnostic aggregate summary does not match results");
  }
}

function sarifResult(
  outcome: DiagnosticOutcome,
  diagnostic: DiagnosticV1,
  ruleIndexes: ReadonlyMap<string, number>,
  artifactIndexes: ReadonlyMap<string, number>,
): JsonObject {
  const anchorSource = diagnostic.schema_source ?? diagnostic.source;
  const index = artifactIndexes.get(anchorSource);
  const ruleIndex = ruleIndexes.get(diagnostic.rule_id);
  if (index === undefined || ruleIndex === undefined) {
    throw new Error("SARIF projection index is missing");
  }
  const physicalLocation: JsonObject = {
    artifactLocation: {
      uri: artifactUri(anchorSource, diagnostic.schema_source !== undefined),
      index,
    },
  };
  if (diagnostic.line !== undefined) {
    const region: JsonObject = { startLine: diagnostic.line };
    if (diagnostic.column !== undefined) region.startColumn = diagnostic.column;
    physicalLocation.region = region;
  }
  const properties: JsonObject = {
    softschemaCategory: diagnostic.category,
    softschemaOutcome: outcome,
    softschemaSource: diagnostic.source,
  };
  if (diagnostic.path !== undefined) properties.softschemaPath = diagnostic.path;
  if (diagnostic.schema_source !== undefined) {
    properties.softschemaSchemaSource = diagnostic.schema_source;
  }
  if (diagnostic.schema_path !== undefined) {
    properties.softschemaSchemaPath = diagnostic.schema_path;
  }
  const level = { error: "error", warning: "warning", info: "note" }[diagnostic.severity] as
    | "error"
    | "warning"
    | "note";
  return {
    ruleId: diagnostic.rule_id,
    ruleIndex,
    level,
    message: { text: diagnostic.message },
    locations: [{ physicalLocation }],
    properties,
  };
}

function artifactUri(source: string, allowUri: boolean): string {
  if (/^[A-Za-z]:\//.test(source)) {
    return `file:///${source.slice(0, 2)}${encodeRelativePath(source.slice(2))}`;
  }
  if (source.startsWith("//")) return `file:${encodeRelativePath(source)}`;
  if (source.startsWith("/")) return `file://${encodeRelativePath(source)}`;
  if (allowUri && /^[A-Za-z][A-Za-z0-9+.-]*:/.test(source)) return encodeAbsoluteUri(source);
  return encodeRelativePath(source);
}

function encodeAbsoluteUri(source: string): string {
  return source
    .split(/(%[0-9A-Fa-f]{2})/)
    .map((part) => (/^%[0-9A-Fa-f]{2}$/.test(part) ? part.toUpperCase() : encodeURI(part)))
    .join("");
}

function encodeRelativePath(source: string): string {
  return source
    .split("/")
    .map((segment) =>
      encodeURIComponent(segment).replace(
        /[!'()*]/g,
        (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
      ),
    )
    .join("/");
}

function cloneInput(input: ArtifactInputResult): ArtifactInputResult {
  return cloneWireValue(input);
}

function cloneValidation(
  validation: DiagnosticValidationWire | null,
): DiagnosticValidationWire | null {
  return cloneWireValue(validation);
}

function dataProperty<T extends object, K extends keyof T>(value: T, key: K): T[K] {
  const descriptor = Object.getOwnPropertyDescriptor(value, key);
  if (descriptor === undefined || !("value" in descriptor)) {
    throw new TypeError("diagnostic wire values must use own data properties");
  }
  return descriptor.value as T[K];
}

/** Deep-copy JSON wire data without JSON hooks or property accessor evaluation. */
function cloneWireValue<T>(value: T): T {
  return cloneWireSubvalue(value, new Set()) as T;
}

function cloneWireSubvalue(value: unknown, active: Set<object>): unknown {
  if (
    value === null ||
    value === undefined ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  if (typeof value !== "object") {
    throw new TypeError("diagnostic wire values must be JSON-compatible");
  }
  if (active.has(value)) throw new TypeError("diagnostic wire values must not contain cycles");
  active.add(value);
  try {
    if (Array.isArray(value)) {
      const lengthDescriptor = Object.getOwnPropertyDescriptor(value, "length");
      const length = lengthDescriptor?.value;
      if (!Number.isSafeInteger(length) || length < 0) {
        throw new TypeError("diagnostic wire arrays must have a valid length");
      }
      const result = new Array<unknown>(length);
      for (let index = 0; index < length; index += 1) {
        const descriptor = Object.getOwnPropertyDescriptor(value, String(index));
        if (descriptor === undefined || !("value" in descriptor)) {
          throw new TypeError("diagnostic wire arrays must use dense data properties");
        }
        result[index] = cloneWireSubvalue(descriptor.value, active);
      }
      return result;
    }

    const result: Record<string, unknown> = {};
    for (const key of Object.keys(value)) {
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (descriptor === undefined || !("value" in descriptor)) {
        throw new TypeError("diagnostic wire values must use own data properties");
      }
      Object.defineProperty(result, key, {
        configurable: true,
        enumerable: true,
        value: cloneWireSubvalue(descriptor.value, active),
        writable: true,
      });
    }
    return result;
  } finally {
    active.delete(value);
  }
}

function limitsJson(limits: DiagnosticLimitsWire): JsonObject {
  return { ...limits };
}

function summaryJson(summary: DiagnosticSummaryV1): JsonObject {
  return { ...summary };
}
