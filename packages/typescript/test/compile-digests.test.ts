/**
 * Pinned compiled digests for a corpus of field shapes around defaults, catches, and
 * authored annotations (`test/fixtures/compile-corpus.ts`).
 *
 * Every shape without a transform compiles to the digest it had before transforming
 * defaults were restored, so the restoration cannot move one. The exceptions are the
 * shapes in `CATCH_DEDUPLICATED`: a `.catch()` whose value the referenced `$defs` entry
 * already carries. The first `.catch()` restoration wrote that value back next to the
 * `$ref`; it is left out again, as Zod writes it.
 */
import { describe, expect, test } from "bun:test";
import { z } from "zod";
import { buildCanonicalSchema } from "../src/compile.js";
import { canonicalJson } from "../src/settings.js";
import { compileCorpus } from "./fixtures/compile-corpus.js";

const CONTRACT = "x:Corpus/v1";

/** The leading 16 hex digits of each shape's `schema_sha256`, without a transform. */
const PINNED: Record<string, string> = {
  default: "ab02bcbcaebfc846",
  default_fn: "ab02bcbcaebfc846",
  default_describe: "a9668f0bb00b709b",
  describe_default: "a9668f0bb00b709b",
  default_optional: "ab02bcbcaebfc846",
  optional_default: "ab02bcbcaebfc846",
  default_nullable: "12ac143d91c9caf8",
  nullable_default: "bad64337133e0f40",
  prefault: "c8922b6aac053266",
  prefault_describe: "1aea43d3650670a9",
  catch: "ab02bcbcaebfc846",
  default_catch: "3c2ab0f952586584",
  catch_default: "3c2ab0f952586584",
  default_default: "3c2ab0f952586584",
  catch_catch: "3c2ab0f952586584",
  default_metadefault: "da4f7f4f8cf6992e",
  metadefault_default: "ab02bcbcaebfc846",
  prefault_metadefault: "da4f7f4f8cf6992e",
  examples: "bf227ed8c617d3c6",
  metadefault: "cc64dc9f1eab0d5a",
  default_examples: "7467fcfbfdc6c325",
  object_default_inline: "a5c477bc09c1948b",
  object_default_defs: "17f95b83691814ca",
  nested_defs_field: "d551365167b36b41",
  record_enum: "4e1b58ce0d298c88",
  record_string: "26b519ce99181c9a",
  array_item: "f13418d684e3aaf0",
  array_default: "e9e66b97089c598e",
  union_member: "6bcda91f3aa9de3f",
  union_default: "e5dff76c327d7731",
  tuple_default: "b01acd2082d36390",
  object3_default: "6e8d23a2d08ea68c",
  id_plain_describe: "82fff0e7372002dc",
  id_plain_same: "a81f497b1ddb3394",
  id_plain_diff: "182ca58f6367208e",
  id_plain_optional: "a81f497b1ddb3394",
  id_plain_nullable: "879af3eed84696a5",
  id_plain_catch_same: "a81f497b1ddb3394",
  id_plain_catch_diff: "182ca58f6367208e",
  id_plain_prefault_same: "a81f497b1ddb3394",
  id_plain_examples: "ea918b3302e4aa3b",
  id_plain_describe_describe: "e668f3f33265cbc9",
  id_plain_describe_examples: "88ece74cbb724a4f",
  id_plain_optional_catch: "043b9179fee22978",
  id_caught_describe: "5ea398b7f299da27",
  id_caught_same: "889bc7c40e9af0a0",
  id_caught_diff: "a5238aee57ae5f31",
  id_caught_optional: "889bc7c40e9af0a0",
  id_caught_nullable: "c38cb96d726e127e",
  id_caught_catch_same: "889bc7c40e9af0a0",
  id_caught_catch_diff: "a5238aee57ae5f31",
  id_caught_prefault_same: "889bc7c40e9af0a0",
  id_caught_examples: "23c73b292792e6f5",
  id_caught_describe_describe: "e42bc2eba64539f0",
  id_caught_describe_examples: "647efc3756e9b51c",
  id_caught_optional_catch: "051243d2e1bd4400",
  idmeta_shapes: "9616a2d0a03b7820",
  chain_P_describe: "150a1c9b77e4015b",
  chain_P_bare: "c61571974bf9cb6f",
  chain_P_default_same: "f6a0c125b3e54511",
  chain_P_default_diff: "8c1fa8539b634c33",
  chain_P2_describe: "6140e1a6415d0ea5",
  chain_P2_default_x: "ddf9c327ad72ec42",
  chain_Q_describe: "af30a2feefed5547",
  chain_Q_default_same: "097b300340eebd08",
  chain_R_default_describe: "65851aafb28d60b5",
  chain_R_default_diff: "5f8987054e1df7e0",
  chain_R_optional: "de0007501f059bfc",
  chain_R_nullable: "9f1b5b9417339313",
  chain_R_catch_same: "de0007501f059bfc",
  chain_R_catch_diff: "5f8987054e1df7e0",
  chain_R_prefault_same: "de0007501f059bfc",
  chain_R_readonly: "1e05dda5f506ebc8",
  chain_R_optional_default_same: "73004dec90157875",
  chain_R_optional_default_diff: "5f8987054e1df7e0",
  chain_three_levels: "035471fccdb3aefd",
  E_examples_same: "dba4646839c1e70c",
  E_examples_diff: "61170106489d04a0",
  E_describe: "73741e1a4c9a84dd",
  E_default: "3a89184360aded99",
  id_slash: "e3e95c8f4b334d06",
  id_tilde: "c80d94e185cd294f",
  tree_root_ref: "1920bd7335c20c49",
  tree_id: "11710dbfdf60ca3a",
  lazy_default: "ab02bcbcaebfc846",
  dunion: "3feb72dca2c06c05",
  intersection: "bc9c50be549dd983",
  email_default: "92c8232898e1dffc",
  iso_date_default: "989259c1a6b1a992",
  int_range_default: "8186065fb1bed07d",
  literal_default: "73b1d08d57775dde",
  readonly_default: "df1b5aceac83e8a5",
  brand_default: "ab02bcbcaebfc846",
  optional_nullable_default: "506c0cdd08e92be2",
  tuple_rest_default: "4c9d59ad48a0a6b2",
  meta_examples_id_default: "f06cb58acaa13e12",
  meta_id_prefault_same: "994811e62d753e14",
  meta_id_prefault_diff: "8cf7a9efa1d067f5",
  meta_default_undefined: "db350217a72ca91f",
};

/** Shapes whose digest moved on purpose: the catch value is left out next to the `$ref`. */
const CATCH_DEDUPLICATED = [
  "id_plain_catch_same",
  "id_caught_describe",
  "id_caught_catch_same",
  "id_caught_examples",
  "chain_R_catch_same",
];

/**
 * Transforming shapes that do not compile like their twin without a transform. In each,
 * Zod writes a `default` or `examples` beside a `$ref` whose chain already carries the same
 * value: an alias, a wrapper between the field and its `$ref`, or a second `.describe()` or
 * `.meta()` clone. Zod compares only one level, while a restored value is settled along the
 * whole chain, so the transforming twin leaves the restated value out. Validation is the
 * same, none has a Pydantic mirror, and before this fix each transforming form lacked the
 * value entirely.
 */
const RESTATED_TWINS = [
  "id_plain_describe_describe",
  "id_plain_describe_examples",
  "id_plain_optional_catch",
  "id_caught_describe_describe",
  "id_caught_describe_examples",
  "id_caught_optional_catch",
  "chain_P_default_same",
  "chain_Q_describe",
  "chain_Q_default_same",
  "chain_R_optional_default_same",
  "chain_three_levels",
];

function compile(build: () => z.ZodType) {
  const { schema, sha } = buildCanonicalSchema(build(), CONTRACT);
  return { json: canonicalJson(schema), sha };
}

describe("compiled digest corpus", () => {
  const plain = compileCorpus(z, false);
  const transforming = compileCorpus(z, true);

  test("every shape without a transform keeps its pinned digest", () => {
    expect(Object.keys(plain).sort()).toEqual(Object.keys(PINNED).sort());
    const moved = Object.entries(plain).filter(
      ([name, build]) => compile(build).sha.slice(0, 16) !== PINNED[name],
    );
    expect(moved.map(([name]) => name)).toEqual([]);
    for (const name of CATCH_DEDUPLICATED) expect(PINNED).toHaveProperty(name);
  });

  test("every transforming shape compiles like its twin, except the restated values", () => {
    const differing = Object.entries(transforming)
      .filter(([name, build]) => {
        const twin = plain[name];
        return twin === undefined || compile(build).sha !== compile(twin).sha;
      })
      .map(([name]) => name);
    expect(differing).toEqual(RESTATED_TWINS);
  });

  test("the private pending-annotation key never reaches the output", () => {
    for (const build of [...Object.values(plain), ...Object.values(transforming)]) {
      const { json } = compile(build);
      expect(json).not.toContain("\\u0000");
      expect(json).not.toContain("softschema:ref-annotations");
    }
  });
});
