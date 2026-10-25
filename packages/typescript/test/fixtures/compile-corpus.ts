/**
 * A corpus of Zod field shapes around `.default()`, `.catch()`, `.prefault()`, and authored
 * `default` and `examples`, for the compiled-digest tests. `transforming` builds each
 * shape's twin with a transform in it; shapes without a transforming twin are built only
 * when it is false. Zod is passed in so a caller can compile the corpus with another
 * worktree's compiler.
 */
import type { z as Zod } from "zod";

type ZodApi = typeof Zod;
type Build = () => Zod.ZodType;

export function compileCorpus(z: ZodApi, transforming: boolean): Record<string, Build> {
  const t = transforming;
  const out: Record<string, Build> = {};
  const add = (name: string, build: Build) => {
    out[name] = build;
  };
  const field = (name: string, build: Build) => add(name, () => z.strictObject({ f: build() }));
  const same = (text: string) => text;
  const str = () => (t ? z.string().transform(same) : z.string());
  const en = () => (t ? z.enum(["a", "b"]).transform(same) : z.enum(["a", "b"]));

  field("default", () => str().default("x"));
  field("default_fn", () => str().default(() => "x"));
  field("default_describe", () => str().default("x").describe("d"));
  field("describe_default", () => str().describe("d").default("x"));
  field("default_optional", () => str().default("x").optional());
  field("optional_default", () => str().optional().default("x"));
  field("default_nullable", () => str().default("x").nullable());
  field("nullable_default", () => str().nullable().default("x"));
  field("prefault", () => str().prefault("p"));
  field("prefault_describe", () => str().prefault("p").describe("d"));
  field("catch", () => str().catch("x"));
  field("default_catch", () => str().default("a").catch("b"));
  field("catch_default", () => str().catch("a").default("b"));
  field("default_default", () => str().default("a").default("b"));
  field("catch_catch", () => str().catch("a").catch("b"));
  field("default_metadefault", () => str().default("x").meta({ default: "m" }));
  field("metadefault_default", () => str().meta({ default: "m" }).default("x"));
  field("prefault_metadefault", () => str().prefault("p").meta({ default: "m" }));
  field("examples", () => str().meta({ examples: ["a", "b"] }));
  field("metadefault", () => str().meta({ default: "m" }));
  field("default_examples", () => str().default("x").meta({ examples: ["a"] }));

  const Inner = () => z.strictObject({ a: str() });
  field("object_default_inline", () => Inner().default({ a: "x" }));
  field("object_default_defs", () => Inner().meta({ id: "CorpusInner" }).default({ a: "x" }));
  field("nested_defs_field", () =>
    z
      .strictObject({ g: (t ? z.int().transform(Number) : z.int()).default(0), h: z.int() })
      .meta({ id: "CorpusNested" }),
  );
  field("record_enum", () => z.record(z.enum(["a", "b"]), str().default("x")));
  field("record_string", () => z.record(z.string(), str().default("x")));
  field("array_item", () => z.array(str().default("x")));
  field("array_default", () => z.array(str()).default(["x"]));
  field("union_member", () => z.union([str().default("x"), z.int()]));
  field("union_default", () => z.union([str(), z.int()]).default("x"));
  field("tuple_default", () => z.tuple([str(), z.int()]).default(["x", 1]));
  field("object3_default", () =>
    z
      .strictObject({
        a: z
          .strictObject({ b: z.strictObject({ c: str().default("x") }).default({ c: "x" }) })
          .default({ b: { c: "x" } }),
      })
      .default({ a: { b: { c: "x" } } }),
  );

  // id'd enum defaults and catches, re-wrapped.
  const ids = {
    plain: () => en().default("a").meta({ id: "CorpusPlain" }),
    caught: () => en().catch("a").meta({ id: "CorpusCaught" }),
  };
  for (const [kind, make] of Object.entries(ids)) {
    const schema = () => make() as Zod.ZodType<"a" | "b">;
    field(`id_${kind}_describe`, () => schema().describe("d"));
    field(`id_${kind}_same`, () => schema().default("a"));
    field(`id_${kind}_diff`, () => schema().default("b"));
    field(`id_${kind}_optional`, () => schema().optional());
    field(`id_${kind}_nullable`, () => schema().nullable());
    field(`id_${kind}_catch_same`, () => schema().catch("a"));
    field(`id_${kind}_catch_diff`, () => schema().catch("b"));
    field(`id_${kind}_prefault_same`, () => schema().prefault("a"));
    field(`id_${kind}_examples`, () => schema().meta({ examples: ["a"] }));
    field(`id_${kind}_describe_describe`, () => schema().describe("a").describe("b"));
    field(`id_${kind}_describe_examples`, () => schema().describe("a").meta({ examples: ["b"] }));
    field(`id_${kind}_optional_catch`, () => schema().optional().catch("a"));
  }

  // An id'd schema with authored metadata, re-wrapped.
  add("idmeta_shapes", () => {
    const S = str().meta({ id: "CorpusMeta", examples: ["a"], default: "m" });
    return z.strictObject({
      d: S.describe("d"),
      e: S.meta({ examples: ["b"] }),
      n: S.default("n"),
      s: S.default("m"),
      x: S.meta({ examples: ["a"] }),
    });
  });

  // Aliases of id'd schemas, and wrappers between a field and its `$ref`.
  const chain = () => {
    const R = str().default("x").meta({ id: "CorpusR" });
    const P = R.default("x").meta({ id: "CorpusP" });
    const P2 = R.default("y").meta({ id: "CorpusP2" });
    const Q = R.describe("q").meta({ id: "CorpusQ" });
    return { R, P, P2, Q };
  };
  field("chain_P_describe", () => chain().P.describe("d"));
  field("chain_P_bare", () => chain().P);
  field("chain_P_default_same", () => chain().P.default("x"));
  field("chain_P_default_diff", () => chain().P.default("z"));
  field("chain_P2_describe", () => chain().P2.describe("d"));
  field("chain_P2_default_x", () => chain().P2.default("x"));
  field("chain_Q_describe", () => chain().Q.describe("d"));
  field("chain_Q_default_same", () => chain().Q.default("x"));
  field("chain_R_default_describe", () => chain().R.default("x").describe("d"));
  field("chain_R_default_diff", () => chain().R.default("y"));
  field("chain_R_optional", () => chain().R.optional());
  field("chain_R_nullable", () => chain().R.nullable());
  field("chain_R_catch_same", () => chain().R.catch("x"));
  field("chain_R_catch_diff", () => chain().R.catch("y"));
  field("chain_R_prefault_same", () => chain().R.prefault("x"));
  field("chain_R_readonly", () => chain().R.readonly());
  field("chain_R_optional_default_same", () => chain().R.optional().default("x"));
  field("chain_R_optional_default_diff", () => chain().R.optional().default("y"));
  field("chain_three_levels", () => {
    const C0 = str().default("x").meta({ id: "CorpusC0" });
    const C1 = C0.default("x").meta({ id: "CorpusC1" });
    const C2 = C1.default("x").meta({ id: "CorpusC2" });
    return C2.describe("b");
  });

  // Examples on a `$ref`.
  const E = () => str().meta({ id: "CorpusE", examples: ["a"] });
  field("E_examples_same", () => E().meta({ examples: ["a"] }));
  field("E_examples_diff", () => E().meta({ examples: ["b"] }));
  field("E_describe", () => E().describe("d"));
  field("E_default", () => E().default("x"));

  // Ids that need JSON Pointer escaping.
  field("id_slash", () => str().default("x").meta({ id: "corpus/a" }).describe("d"));
  field("id_tilde", () => str().default("x").meta({ id: "corpus~b" }).describe("d"));

  // Recursion, lazy, discriminated unions, and intersections.
  add("tree_root_ref", () => {
    const Tree: Zod.ZodType = z.strictObject({
      name: str(),
      get child() {
        return Tree.default({ name: "leaf" });
      },
    });
    return Tree;
  });
  add("tree_id", () => {
    const Tree: Zod.ZodType = z
      .strictObject({
        name: str(),
        get child() {
          return Tree.default({ name: "leaf" });
        },
      })
      .meta({ id: "CorpusTree" });
    return z.strictObject({ root: Tree });
  });
  field("lazy_default", () => z.lazy(() => str()).default("x"));
  field("dunion", () =>
    z.discriminatedUnion("k", [
      z.strictObject({ k: z.literal("a"), v: str().default("x") }),
      z.strictObject({ k: z.literal("b") }),
    ]),
  );
  field("intersection", () =>
    z.intersection(z.object({ a: str().default("x") }), z.object({ b: z.int() })),
  );

  if (!t) {
    field("email_default", () => z.email().default("a@b.co"));
    field("iso_date_default", () => z.iso.date().default("2020-01-01"));
    field("int_range_default", () => z.int().min(1).max(9).default(5));
    field("literal_default", () => z.literal("a").default("a"));
    field("readonly_default", () => z.string().readonly().default("x"));
    field("brand_default", () => z.string().brand("B").default("x" as never));
    field("optional_nullable_default", () => z.string().optional().nullable().default(null));
    field("tuple_rest_default", () => z.tuple([z.string()], z.int()).default(["x"]));
    field("meta_examples_id_default", () =>
      z.string().meta({ id: "CorpusME", examples: ["a"] }).default("x").describe("d"),
    );
    field("meta_id_prefault_same", () =>
      z.string().meta({ id: "CorpusMP", default: "m" }).prefault("m"),
    );
    field("meta_id_prefault_diff", () =>
      z.string().meta({ id: "CorpusMP", default: "m" }).prefault("q"),
    );
    field("meta_default_undefined", () => z.string().default("x").meta({ default: undefined }));
  }
  return out;
}
