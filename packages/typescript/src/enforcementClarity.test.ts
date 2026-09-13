/** Shared actual-execution cases and TypeScript's separate model-label binding. */
import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse, stringify } from "yaml";
import { z } from "zod";
import type { Contract, SchemaStatus, ValidationExecution, WarningCode } from "./models.js";
import { repairAndValidateArtifact } from "./repairValidate.js";
import {
  ArtifactInvalidError,
  loadArtifact,
  validateArtifact,
  validateStructural,
  validateValues,
} from "./validate.js";

const Sample = z.strictObject({ name: z.string() }).refine((value) => value.name !== "rejected", {
  message: "name is unavailable",
});
const schema = { type: "object", properties: { name: { type: "string" } }, required: ["name"] };

function tmpDir(): string {
  return mkdtempSync(join(tmpdir(), "softschema-execution-"));
}
function contract(overrides: Partial<Contract> = {}): Contract {
  return {
    id: "example:Sample/v1",
    model: null,
    envelopeKey: null,
    status: "enforced",
    profile: "pure-yaml",
    schemaPath: null,
    ...overrides,
  };
}
function document(directory: string, values: unknown = { name: "hello" }): string {
  const path = join(directory, "sample.yaml");
  writeFileSync(path, stringify(values));
  return path;
}
interface LayerExpectation {
  execution: ValidationExecution | { python: ValidationExecution; typescript: ValidationExecution };
  ok: boolean;
  skipped_reason: string | null;
}
interface ExecutionCase {
  name: string;
  values: unknown;
  status?: SchemaStatus;
  model?: boolean;
  schema?: Record<string, unknown>;
  schema_text?: string;
  missing_schema?: boolean;
  require?: ("structural" | "semantic")[];
  structural: LayerExpectation;
  semantic: LayerExpectation;
  warning?: WarningCode;
  error_kind?: string;
}
const vectors = parse(
  readFileSync(
    new URL("../../../tests/vectors/validation-execution.yaml", import.meta.url),
    "utf8",
  ),
) as { cases: ExecutionCase[] };

describe("actual validation execution", () => {
  // A model label is metadata only, so each vector must hold with and without one.
  const labels = [null, "inline:Sample"] as const;
  for (const vector of vectors.cases) {
    for (const label of labels) {
      runVector(vector, label);
    }
  }

  function runVector(vector: ExecutionCase, label: string | null): void {
    test(label === null ? vector.name : `${vector.name} (model label ${label})`, () => {
      const directory = tmpDir();
      const path = document(directory, vector.values);
      const schemaPath =
        vector.schema || vector.schema_text || vector.missing_schema
          ? join(directory, "sample.schema.yaml")
          : null;
      if (schemaPath && vector.schema_text) writeFileSync(schemaPath, vector.schema_text);
      else if (schemaPath && vector.schema) writeFileSync(schemaPath, stringify(vector.schema));
      const result = validateArtifact(
        path,
        contract({ schemaPath, status: vector.status ?? "enforced", model: label }),
        { semanticModel: vector.model ? Sample : undefined, require: vector.require },
      );
      for (const layer of ["structural", "semantic"] as const) {
        const expected = vector[layer];
        const execution =
          typeof expected.execution === "string"
            ? expected.execution
            : expected.execution.typescript;
        expect({
          execution: result[layer].execution,
          ok: result[layer].ok,
          skipped_reason: result[layer].skipped_reason,
        }).toEqual({ ...expected, execution });
        const unmet = (result[layer].errors as Record<string, unknown>[])
          .filter((error) => error.kind === "check_not_completed")
          .map(({ kind, layer, execution }) => ({ kind, layer, execution }));
        const required = (vector.require ?? []).includes(layer) && execution !== "completed";
        expect(unmet).toEqual(required ? [{ kind: "check_not_completed", layer, execution }] : []);
      }
      const expectedOk = vector.structural.ok && vector.semantic.ok;
      expect(result.ok).toBe(expectedOk);
      expect(result.outcome).toBe(expectedOk ? "valid" : "invalid");
      expect(result.warnings.map((warning) => warning.code)).toEqual(
        vector.warning ? [vector.warning] : [],
      );
      if (vector.error_kind) expect(result.structural.errors[0]?.kind).toBe(vector.error_kind);
      expect(result).not.toHaveProperty("enforcement_applied");
    });
  }

  test("a model label without a validator supplies no execution evidence", () => {
    const result = validateArtifact(document(tmpDir()), contract({ model: "inline:Sample" }));
    expect(result.semantic.execution).toBe("not_run");
    expect(result.semantic.skipped_reason).toBe("no_semantic_model");
    expect(result.structural.execution).toBe("not_run");
    // The skip reason follows the supplied validator, as in Python; a label is not a model.
    expect(result.structural.skipped_reason).toBe("no_schema");
    expect(result.warnings.map((warning) => warning.code)).toEqual([
      "document-enforcement-not-applied",
    ]);
  });

  test("a real validator with no model label supplies its completed rejection", () => {
    const result = validateArtifact(document(tmpDir(), { name: "rejected" }), contract(), {
      semanticModel: Sample,
    });
    expect(result.semantic.execution).toBe("completed");
    expect(result.semantic.ok).toBe(false);
    expect(result.structural.execution).toBe("not_run");
    expect(result.structural.skipped_reason).toBe("inferred_via_model");
    expect(result.warnings.map((warning) => warning.code)).toEqual([
      "document-enforcement-via-model-only",
    ]);
  });

  test("values and repair preserve independent completed checks", () => {
    const result = validateValues({ name: "rejected" }, { model: Sample, schema });
    expect(result.structural.execution).toBe("completed");
    expect(result.semantic.execution).toBe("completed");
    expect(result.structural.ok).toBe(true);
    expect(result.semantic.ok).toBe(false);
    const modelOnly = validateValues({ name: "hello" }, { model: Sample });
    expect(modelOnly.structural.execution).toBe("not_run");
    expect(modelOnly.structural.skipped_reason).toBeNull();
    const directory = tmpDir();
    const schemaPath = join(directory, "sample.schema.yaml");
    writeFileSync(schemaPath, stringify(schema));
    const repaired = repairAndValidateArtifact(document(directory), contract({ schemaPath }), {
      semanticModel: Sample,
      write: false,
    });
    expect(repaired.structural.execution).toBe("completed");
    expect(repaired.semantic.execution).toBe("completed");
  });

  test("pre-payload failure invokes neither check", () => {
    const result = validateArtifact(join(tmpDir(), "absent.yaml"), contract(), {
      semanticModel: Sample,
    });
    expect(result.structural.execution).toBe("not_run");
    expect(result.semantic.execution).toBe("not_run");
    expect(result.ok).toBe(false);
    expect(result.warnings).toEqual([]);
  });

  test("an exception during actual structural evaluation is errored", () => {
    const values = Object.defineProperty({}, "name", {
      enumerable: true,
      get() {
        throw new Error("payload access failed");
      },
    });
    const result = validateStructural(values, schema);
    expect(result.execution).toBe("errored");
    expect(result.ok).toBe(false);
    expect(result.errors[0]?.kind).toBe("schema_invalid");
  });

  test("a required structural check completed by a bound schema stays valid", () => {
    const directory = tmpDir();
    const schemaPath = join(directory, "sample.schema.yaml");
    writeFileSync(schemaPath, stringify(schema));
    const path = document(directory);
    const bound = contract({ schemaPath });
    const result = validateArtifact(path, bound, { require: ["structural"] });
    expect(result.outcome).toBe("valid");
    expect(result.ok).toBe(true);
    expect(result.structural.execution).toBe("completed");
    expect(result.structural.errors).toEqual([]);
    expect(result).toEqual(validateArtifact(path, bound));
    expect(loadArtifact(path, bound, { require: ["structural"] })).toEqual({ name: "hello" });
  });

  test("a required semantic check without a model is invalid", () => {
    const path = document(tmpDir());
    const unrequired = validateArtifact(path, contract({ model: "inline:Sample" }));
    expect(unrequired.outcome).toBe("valid");
    const result = validateArtifact(path, contract({ model: "inline:Sample" }), {
      require: ["semantic"],
    });
    expect(result.outcome).toBe("invalid");
    expect(result.ok).toBe(false);
    expect(result.structural).toEqual(unrequired.structural);
    expect(result.semantic).toEqual({
      ok: false,
      execution: "not_run",
      errors: [
        {
          kind: "check_not_completed",
          message: "required semantic check did not complete (execution: not_run)",
          layer: "semantic",
          execution: "not_run",
        },
      ],
      skipped_reason: "no_semantic_model",
    });
    let thrown: unknown;
    try {
      loadArtifact(path, contract(), { require: ["semantic"] });
    } catch (err) {
      thrown = err;
    }
    expect(thrown).toBeInstanceOf(ArtifactInvalidError);
    expect((thrown as ArtifactInvalidError).result.outcome).toBe("invalid");
  });

  test("a required check preserves the schema preparation error", () => {
    const directory = tmpDir();
    const schemaPath = join(directory, "sample.schema.yaml");
    writeFileSync(schemaPath, "[");
    const path = document(directory);
    const unrequired = validateArtifact(path, contract({ schemaPath }), { semanticModel: Sample });
    const result = validateArtifact(path, contract({ schemaPath }), {
      semanticModel: Sample,
      require: ["structural", "semantic"],
    });
    expect(result.outcome).toBe("invalid");
    expect(result.structural.execution).toBe("not_run");
    expect(result.structural.errors).toEqual([
      unrequired.structural.errors[0] as Record<string, unknown>,
      {
        kind: "check_not_completed",
        message: "required structural check did not complete (execution: not_run)",
        layer: "structural",
        execution: "not_run",
      },
    ]);
    expect(result.structural.errors[0]?.kind).toBe("schema_invalid");
    expect(result.semantic).toEqual(unrequired.semantic);
    expect(result.warnings).toEqual(unrequired.warnings);
  });

  test("a required check keeps a pre-payload input error", () => {
    const result = validateArtifact(join(tmpDir(), "absent.yaml"), contract(), {
      require: ["structural"],
    });
    expect(result.outcome).toBe("input_error");
    expect(result.structural.errors[0]?.kind).toBe("artifact_unreadable");
    expect(result.structural.errors.at(-1)?.kind).toBe("check_not_completed");
  });

  test("required checks on values", () => {
    const both = validateValues({ name: "hello" }, { model: Sample, schema });
    expect(
      validateValues(
        { name: "hello" },
        { model: Sample, schema, require: ["structural", "semantic"] },
      ),
    ).toEqual(both);
    const modelOnly = validateValues({ name: "hello" }, { model: Sample, require: ["structural"] });
    expect(modelOnly.structural.ok).toBe(false);
    expect(modelOnly.structural.errors.at(-1)?.kind).toBe("check_not_completed");
    expect(modelOnly.semantic.ok).toBe(true);
  });

  test("require rejects an unknown layer", () => {
    expect(() =>
      validateArtifact(document(tmpDir()), contract(), {
        require: ["payload"] as unknown as ("structural" | "semantic")[],
      }),
    ).toThrow("payload");
  });

  test("semantic programmer errors propagate without a fabricated verdict", () => {
    const broken = z.object({ name: z.string() }).refine(() => {
      throw new TypeError("model implementation failed");
    });
    expect(() => validateValues({ name: "hello" }, { model: broken })).toThrow(
      "model implementation failed",
    );
  });
});
