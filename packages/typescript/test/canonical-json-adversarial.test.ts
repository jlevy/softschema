import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "bun:test";
import {
  canonicalJson,
  compareUnicodeCodePoints,
  stableStringify,
} from "../src/core/canonical-json.js";
import { normalizePortableValue } from "../src/core/value-domain.js";
import { schemaSha256 } from "../src/settings.js";

interface SerializationVector {
  id: string;
  value: unknown;
  compact: string;
  pretty: string;
  sha256: string;
}

const vectors = JSON.parse(
  readFileSync(
    resolve(import.meta.dir, "../../../tests/parity/canonical-json-adversarial-vectors.json"),
    "utf8",
  ),
) as { format: "canonical-json-adversarial-v1"; cases: SerializationVector[] };

describe("canonical JSON adversarial parity", () => {
  test("implements a Unicode scalar comparator including equality and prefixes", () => {
    expect(compareUnicodeCodePoints("😀", "😀")).toBe(0);
    expect(compareUnicodeCodePoints("😀", "😀a")).toBeLessThan(0);
    expect(compareUnicodeCodePoints("", "𐀀")).toBeLessThan(0);
    expect(compareUnicodeCodePoints("𐀀", "")).toBeGreaterThan(0);
  });

  test("matches Python canonical bytes and hashes after portable normalization", () => {
    for (const vector of vectors.cases) {
      const normalized = normalizePortableValue(vector.value).value;
      const compact = canonicalJson(normalized);
      expect({ id: vector.id, compact, pretty: stableStringify(normalized) }).toEqual({
        id: vector.id,
        compact: vector.compact,
        pretty: vector.pretty,
      });
      expect(schemaSha256(normalized)).toBe(vector.sha256);
      expect(createHash("sha256").update(compact, "utf8").digest("hex")).toBe(vector.sha256);
    }
  });

  test("normalizes signed zero and integral floats before serialization", () => {
    const value = vectors.cases.find(
      (vector) => vector.id === "normalized-float-and-exponent-boundaries",
    )?.value;
    if (value === undefined) throw new Error("missing numeric serialization vector");
    const normalized = normalizePortableValue(value).value;
    if (!Array.isArray(normalized))
      throw new Error("numeric serialization vector must be an array");
    expect(Object.is(normalized[0], -0)).toBe(false);
    expect(normalized.slice(0, 4)).toEqual([0, 0, 1, -1]);
  });

  test("permits repeated references without treating them as cycles", () => {
    const shared = { "10": "ten", "2": "two" };
    expect(canonicalJson({ left: shared, right: shared })).toBe(
      '{"left":{"10":"ten","2":"two"},"right":{"10":"ten","2":"two"}}',
    );
  });

  test("supports null-prototype records in the portable object surface", () => {
    const value = Object.create(null) as Record<string, unknown>;
    value["2"] = "two";
    value["10"] = "ten";
    expect(canonicalJson(value)).toBe('{"10":"ten","2":"two"}');
  });

  test("rejects cycles, sparse arrays, non-plain objects, and non-JSON scalars", () => {
    const cyclicArray: unknown[] = [];
    cyclicArray.push(cyclicArray);
    const cyclicObject: Record<string, unknown> = {};
    cyclicObject.self = cyclicObject;
    const sparse = new Array(2);
    const inherited = new Array(1);
    let getterCalls = 0;
    const inheritedPrototype = Object.create(Array.prototype) as Record<string, unknown>;
    Object.defineProperty(inheritedPrototype, "0", {
      enumerable: true,
      get: () => {
        getterCalls += 1;
        return "must not run";
      },
    });
    Object.setPrototypeOf(inherited, inheritedPrototype);
    const accessorArray: unknown[] = [];
    Object.defineProperty(accessorArray, "0", {
      enumerable: true,
      get: () => {
        getterCalls += 1;
        return "must not run";
      },
    });
    const accessorObject = {};
    Object.defineProperty(accessorObject, "value", {
      enumerable: true,
      get: () => {
        getterCalls += 1;
        return "must not run";
      },
    });

    for (const value of [cyclicArray, cyclicObject]) {
      expect(() => canonicalJson(value)).toThrow("circular");
    }
    for (const value of [sparse, inherited]) {
      expect(() => canonicalJson(value)).toThrow("dense own data");
    }
    for (const value of [accessorArray, accessorObject]) {
      expect(() => canonicalJson(value)).toThrow("accessors");
    }
    expect(getterCalls).toBe(0);
    for (const value of [[undefined], { value: undefined }]) {
      expect(() => canonicalJson(value)).toThrow("undefined");
    }
    for (const value of [new Date(0), new Map(), new (class Example {})()]) {
      expect(() => canonicalJson(value)).toThrow("non-plain");
    }
    for (const value of [Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]) {
      expect(() => canonicalJson(value)).toThrow("finite");
    }
    expect(() => canonicalJson(Number.MAX_SAFE_INTEGER + 1)).toThrow("safe range");
    expect(() => canonicalJson("\ud800")).toThrow("Unicode scalar");
    expect(() => canonicalJson("\udc00")).toThrow("Unicode scalar");
    expect(() => canonicalJson({ ["\ud800"]: "value" })).toThrow("object keys");
    for (const value of [undefined, 1n, Symbol("value"), () => null]) {
      expect(() => canonicalJson(value)).toThrow("not JSON-serializable");
    }
  });
});
