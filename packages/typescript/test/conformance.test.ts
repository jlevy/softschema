/** Cross-language compiled-schema parity and shared-vector readability. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { parse as yamlParse } from "yaml";
import { buildCanonicalSchema } from "../src/compile.js";
import { KitchenSink } from "./fixtures/parity.js";

const REFERENCE = join(import.meta.dir, "../../../examples/parity/parity.schema.yaml");
const HARDENING_VECTORS = join(import.meta.dir, "../../../tests/vectors/hardening.yaml");
const CONTRACT_ID = "example.parity:KitchenSink/v1";

describe("KitchenSink cross-language parity", () => {
  const committed = yamlParse(readFileSync(REFERENCE, "utf8")) as Record<string, unknown>;
  const { schema, sha } = buildCanonicalSchema(KitchenSink, CONTRACT_ID);

  test("compiles to the same canonical schema content as Pydantic", () => {
    expect(schema).toEqual(committed);
  });

  test("produces the same schema_sha256 as the committed reference", () => {
    const expected = (committed["x-softschema"] as Record<string, unknown>).schema_sha256;
    expect(sha).toBe(expected as string);
  });
});

test("shared hardening vectors are readable", () => {
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<{ id: string }>
  >;
  expect(Object.keys(vectors)).toEqual([
    "artifact_input",
    "portable_values",
    "structural",
    "canonicalization",
    "enforcement",
    "identity",
    "compiler_annotations",
    "schema_view",
    "digests",
  ]);
  const ids = Object.values(vectors).flatMap((cases) => cases.map(({ id }) => id));
  expect(new Set(ids).size).toBe(ids.length);
});
