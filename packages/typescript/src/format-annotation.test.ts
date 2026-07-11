import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import { z } from "zod";
import { loadYamlFixture } from "../test/yaml-fixture.js";
import { validateStructural, validateValues } from "./validate.js";

interface FormatVector {
  id: string;
  format: string;
  value: string;
}

const vectors = loadYamlFixture<{ cases: FormatVector[] }>(
  resolve(import.meta.dir, "../../../tests/parity/format-annotations.yaml"),
);

describe("annotation-only-v1 formats", () => {
  test("known and unknown formats are warning-free annotations", () => {
    const logged: unknown[][] = [];
    const originalWarn = console.warn;
    const originalError = console.error;
    console.warn = (...values: unknown[]) => logged.push(values);
    console.error = (...values: unknown[]) => logged.push(values);
    try {
      for (const vector of vectors.cases) {
        const result = validateStructural(vector.value, {
          type: "string",
          format: vector.format,
        });
        expect({ id: vector.id, ok: result.ok, errors: result.errors }).toEqual({
          id: vector.id,
          ok: true,
          errors: [],
        });
      }
    } finally {
      console.warn = originalWarn;
      console.error = originalError;
    }
    expect(logged).toEqual([]);
  });

  test("non-format assertions still apply", () => {
    const result = validateStructural("not-an-email", {
      type: "string",
      format: "email",
      minLength: 20,
    });
    expect(result.ok).toBe(false);
    expect(
      result.errors.map((error) =>
        error.kind === "schema_violation" ? error.validator : error.kind,
      ),
    ).toEqual(["minLength"]);
  });

  test("trusted semantic models remain independent", () => {
    const TrustedModel = z.object({
      value: z.string().refine((value) => value !== "blocked", "blocked by trusted model"),
    });
    const result = validateValues(
      { value: "blocked" },
      {
        model: TrustedModel,
        schema: {
          type: "object",
          properties: { value: { type: "string", format: "email" } },
          required: ["value"],
        },
      },
    );
    expect(result.structural.ok).toBe(true);
    expect(result.semantic.ok).toBe(false);
  });
});
