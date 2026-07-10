import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  firstUnsupportedPattern,
  isPortablePattern,
  PORTABLE_PATTERN_CACHE_SIZE,
  PORTABLE_PATTERN_MAX_CODEPOINTS,
  PORTABLE_PATTERN_MAX_DFA_STATES,
  PORTABLE_PATTERN_MAX_DFA_TRANSITIONS,
  PORTABLE_PATTERN_MAX_GROUP_DEPTH,
  PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS,
  PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS,
  PORTABLE_PATTERN_MAX_VALIDATION_WORK,
  portablePatternCacheInfo,
  portablePatternMatches,
  withPortablePatternValidationBudget,
} from "./portable-pattern.js";
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
    const profile = (vectors as unknown as { profile: Record<string, unknown> }).profile;
    expect(profile.max_dfa_states).toBe(PORTABLE_PATTERN_MAX_DFA_STATES);
    expect(profile.max_dfa_transitions).toBe(PORTABLE_PATTERN_MAX_DFA_TRANSITIONS);
    expect(profile.max_schema_patterns).toBe(PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS);
    expect(profile.max_schema_codepoints).toBe(PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS);
    expect(profile.max_validation_work).toBe(PORTABLE_PATTERN_MAX_VALIDATION_WORK);
    for (const vector of vectors.syntax) {
      expect({
        id: vector.id,
        supported: isPortablePattern(vector.pattern),
      }).toEqual({
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

  test("enforces source, nesting, and compiled-state limits without overflowing", () => {
    expect(isPortablePattern("a".repeat(PORTABLE_PATTERN_MAX_CODEPOINTS))).toBe(true);
    expect(isPortablePattern("a".repeat(PORTABLE_PATTERN_MAX_CODEPOINTS + 1))).toBe(false);

    const deepestSupported =
      "(".repeat(PORTABLE_PATTERN_MAX_GROUP_DEPTH) +
      "a" +
      ")".repeat(PORTABLE_PATTERN_MAX_GROUP_DEPTH);
    const tooDeep = `(${deepestSupported})`;
    expect(isPortablePattern(deepestSupported)).toBe(true);
    expect(() => isPortablePattern(tooDeep)).not.toThrow();
    expect(isPortablePattern(tooDeep)).toBe(false);

    expect(isPortablePattern("(?:a{1000}){4}")).toBe(true);
    expect(isPortablePattern("(?:a{1000}){5}")).toBe(false);
  });

  test("matches nested quantifiers in linear time", () => {
    const adversarialValue = `${"a".repeat(100_000)}!`;
    expect(isPortablePattern("^(a+)+$")).toBe(true);
    expect(portablePatternMatches("^(a+)+$", adversarialValue)).toBe(false);
    expect(
      validateStructural(adversarialValue, {
        type: "string",
        pattern: "^(a+)+$",
      }).ok,
    ).toBe(false);
  });

  test("normalizes character classes and bounds retained DFA cache memory", () => {
    const repeatedClass = `[${"a".repeat(1000)}]`;
    expect(portablePatternMatches(repeatedClass, "b".repeat(100_000))).toBe(false);
    expect(portablePatternMatches(repeatedClass, "a")).toBe(true);

    for (let index = 0; index < PORTABLE_PATTERN_CACHE_SIZE + 8; index += 1) {
      const suffix = String(index).padStart(2, "0");
      expect(portablePatternMatches(`^cache${suffix}[a-c]+$`, `cache${suffix}abc`)).toBe(true);
    }
    const info = portablePatternCacheInfo();
    expect(info.patterns).toBe(PORTABLE_PATTERN_CACHE_SIZE);
    expect(info.transitions).toBeLessThanOrEqual(info.maxTransitions);
  });

  test("bounds aggregate membership retained by adversarial DFA subsets", () => {
    // Each successive input position creates a larger exact subset for this accepted
    // expression. State/transition counts alone do not bound the sum of those arrays.
    const pattern = "(?:a|b)*a(?:a|b){1000}";
    expect(portablePatternMatches(pattern, "a".repeat(1001))).toBe(true);
    expect(portablePatternMatches(pattern, "b".repeat(1001))).toBe(false);

    const info = portablePatternCacheInfo();
    expect(info.maxEngineMemberships).toBeLessThanOrEqual(info.maxMembershipsPerEngine);
    expect(info.memberships).toBeLessThanOrEqual(info.maxMemberships);
  });

  test("memoizes identical pattern/key classifications only within one validation", () => {
    const value = "a".repeat(10_000);
    expect(portablePatternMatches("z", value)).toBe(false);
    expect(
      withPortablePatternValidationBudget(() => {
        expect(portablePatternMatches("z", value)).toBe(false);
        return portablePatternMatches("z", value);
      }, value.length + 20),
    ).toBe(false);
  });

  test("classifies aggregate pattern/key work with the stable compile reason", () => {
    const key = "a".repeat(120_000);
    const patternProperties = Object.fromEntries(
      Array.from({ length: 70 }, (_, index) => [`z${String(index).padStart(2, "0")}`, true]),
    );
    expect(validateStructural({ [key]: 1 }, { type: "object", patternProperties }).errors).toEqual([
      {
        kind: "schema_invalid",
        reason: "compile",
        message: "compiled schema could not be compiled",
        schema_path: "",
      },
    ]);
  });

  test("uses the linear engine for additional and unevaluated property checks", () => {
    const adversarialKey = `${"a".repeat(10_000)}!`;
    const additionalResult = validateStructural(
      { [adversarialKey]: 1 },
      {
        type: "object",
        patternProperties: { "^(a+)+$": true },
        additionalProperties: false,
      },
    );
    const additionalError = additionalResult.errors[0];
    expect(additionalError?.kind).toBe("schema_violation");
    if (additionalError?.kind !== "schema_violation") {
      throw new Error("expected additionalProperties violation");
    }
    expect(additionalError.validator).toBe("additionalProperties");

    const unevaluatedResult = validateStructural(
      { [adversarialKey]: 1 },
      {
        type: "object",
        allOf: [{ patternProperties: { "^(a+)+$": true } }],
        unevaluatedProperties: false,
      },
    );
    const unevaluatedError = unevaluatedResult.errors[0];
    expect(unevaluatedError?.kind).toBe("schema_violation");
    if (unevaluatedError?.kind !== "schema_violation") {
      throw new Error("expected unevaluatedProperties violation");
    }
    expect(unevaluatedError.validator).toBe("unevaluatedProperties");
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
    const error = result.errors[0];
    expect(error?.kind).toBe("schema_violation");
    if (error?.kind !== "schema_violation") throw new Error("expected schema violation");
    expect(error.validator).toBe("unevaluatedProperties");
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
      {
        $schema: "https://json-schema.org/draft/2020-12/schema",
        $ref: resourceId,
      },
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
    const error = result.errors[0];
    expect(error?.kind).toBe("schema_violation");
    if (error?.kind !== "schema_violation") throw new Error("expected schema violation");
    expect(error.validator).toBe("pattern");
    expect(error.validator_value).toBe("^a$");
  });

  test("selects unsupported patterns by Unicode scalar order", () => {
    const bmp = "\uE000(";
    const astral = "😀(";
    expect(
      firstUnsupportedPattern({
        patternProperties: { [astral]: true, [bmp]: true },
      }),
    ).toEqual({ path: ["patternProperties", bmp], pattern: bmp });
    expect(
      firstUnsupportedPattern({
        properties: {
          [astral]: { pattern: "[" },
          [bmp]: { pattern: "(" },
        },
      }),
    ).toEqual({ path: ["properties", bmp, "pattern"], pattern: "(" });
  });

  test("selects unsupported patterns across keyword categories by path", () => {
    expect(
      firstUnsupportedPattern({
        definitions: { z: { pattern: "(" } },
        additionalProperties: { pattern: "[" },
      }),
    ).toEqual({ path: ["additionalProperties", "pattern"], pattern: "[" });
  });
});
