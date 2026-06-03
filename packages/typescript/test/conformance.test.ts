/**
 * Cross-language conformance: the Zod KitchenSink must compile to the same canonical
 * schema (content + schema_sha256) as the committed Python reference. YAML formatting is
 * incidental, so this compares the parsed content and the content hash, not raw bytes.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { parse as yamlParse } from "yaml";
import { buildCanonicalSchema } from "../src/compile.js";
import { KitchenSink } from "./fixtures/parity.js";

const REFERENCE = join(import.meta.dir, "../../../examples/parity/parity.schema.yaml");
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
