/** Cross-language compiled-schema parity and shared-vector readability. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { parse as yamlParse } from "yaml";
import { buildCanonicalSchema } from "../src/compile.js";
import { parsePortableYaml } from "../src/portable.js";
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

  test("the committed reference reads back through the portable reader", () => {
    // The fixture's `separator` field carries U+0085, U+2028 and U+2029, which the Python
    // writer stores as `\N`, `\L` and `\P`; this is the read that fails when a writer
    // leaves one of them raw.
    expect(parsePortableYaml(readFileSync(REFERENCE, "utf8"))).toEqual(schema);
  });

  test("the defaulted transform runs as its AfterValidator mirror does", () => {
    // The transform is not in the schema; the default fills an absent key without it.
    expect(KitchenSink.shape.slug.parse("Spirited-Away")).toBe("spirited-away");
    expect(KitchenSink.shape.slug.parse(undefined)).toBe("none");
  });
});

test("shared hardening vectors are readable", () => {
  const vectors = yamlParse(readFileSync(HARDENING_VECTORS, "utf8")) as Record<
    string,
    Array<{ id: string }>
  >;
  expect(Object.keys(vectors)).toEqual([
    "artifact_input",
    "frontmatter",
    "fence_scan",
    "portable_values",
    "structural",
    "canonicalization",
    "enforcement",
    "enforcement_semantics",
    "engine_deviations",
    "identity",
    "compiler_annotations",
    "compiler_titles",
    "schema_view",
    "digests",
    "yaml_repair",
    "schema_conform",
  ]);
  const ids = Object.values(vectors).flatMap((cases) => cases.map(({ id }) => id));
  expect(new Set(ids).size).toBe(ids.length);
});
