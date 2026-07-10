import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { isPortablePattern, portablePatternMatches } from "./portable-pattern.js";
import { validateStructural } from "./validate.js";

interface SyntaxVector {
  id: string;
  pattern: string;
  supported: boolean;
}

interface MatchingVector {
  id: string;
  pattern: string;
  cases: { value: string; matches: boolean }[];
}

const vectors = JSON.parse(
  readFileSync(resolve(import.meta.dir, "../../../tests/parity/portable-patterns.json"), "utf8"),
) as { syntax: SyntaxVector[]; matching: MatchingVector[] };

describe("portable-regex-v1", () => {
  test("accepts exactly the shared syntax profile", () => {
    for (const vector of vectors.syntax) {
      expect({ id: vector.id, supported: isPortablePattern(vector.pattern) }).toEqual({
        id: vector.id,
        supported: vector.supported,
      });
    }
  });

  test("matches every shared differential vector", () => {
    for (const vector of vectors.matching) {
      for (const item of vector.cases) {
        expect({
          id: vector.id,
          value: item.value,
          matches: portablePatternMatches(vector.pattern, item.value),
        }).toEqual({ id: vector.id, value: item.value, matches: item.matches });
      }
    }
  });

  test("uses portable end and dot semantics in structural validation", () => {
    expect(validateStructural("a\n", { type: "string", pattern: "^a$" }).ok).toBe(false);
    expect(validateStructural("\r", { type: "string", pattern: "." }).errors).toEqual([
      {
        kind: "schema_violation",
        path: [],
        validator: "pattern",
        validator_value: ".",
        value: "\r",
        message: "value '\\r' does not match pattern '.'",
      },
    ]);
  });

  test("uses portable patternProperties semantics for evaluated keys", () => {
    const schema = {
      type: "object",
      allOf: [{ patternProperties: { "^a$": { type: "integer" } } }],
      unevaluatedProperties: false,
    };
    expect(validateStructural({ a: 1 }, schema).ok).toBe(true);
    const result = validateStructural({ "a\n": 1 }, schema);
    expect(result.ok).toBe(false);
    expect(result.errors[0]?.validator).toBe("unevaluatedProperties");
  });

  test("does not interpret pattern-shaped annotation data as schema", () => {
    const schema = {
      type: "object",
      examples: [{ pattern: "[" }],
      properties: { value: { type: "string" } },
    };
    expect(validateStructural({ value: "ok" }, schema).ok).toBe(true);
  });

  test("returns the original pattern and an escaped pointer for patternProperties", () => {
    const pattern = "(?=a/a~)";
    expect(
      validateStructural({}, { type: "object", patternProperties: { [pattern]: true } }).errors,
    ).toEqual([
      {
        kind: "schema_invalid",
        reason: "pattern",
        message: "compiled schema contains an unsupported or invalid pattern",
        schema_path: "/patternProperties/(?=a~1a~0)",
        pattern,
      },
    ]);
  });

  test("applies the same profile to explicitly supplied resources", () => {
    const resourceId = "urn:example:portable-pattern";
    const result = validateStructural(
      "a\n",
      { $schema: "https://json-schema.org/draft/2020-12/schema", $ref: resourceId },
      {
        resources: {
          [resourceId]: {
            $schema: "https://json-schema.org/draft/2020-12/schema",
            $id: resourceId,
            type: "string",
            pattern: "^a$",
          },
        },
      },
    );
    expect(result.errors[0]?.validator).toBe("pattern");
    expect(result.errors[0]?.validator_value).toBe("^a$");
  });
});
