import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { SchemaView } from "../src/schemaView.js";
import { inferEnvelopeKey } from "../src/validate.js";
import { PortableValueError, PortableYamlSyntaxError } from "../src/yaml-value-domain.js";
import { loadYamlFixture } from "./yaml-fixture.js";

const MOVIE_SCHEMA = join(import.meta.dir, "../../../examples/movie_page/movie-page.schema.yaml");
const vectors = loadYamlFixture<{
  cases: Array<{
    id: string;
    schema: Record<string, unknown>;
    fields: Array<Record<string, unknown>>;
  }>;
}>(join(import.meta.dir, "../../../tests/schema-view/vectors.yaml"));

function fieldOutput(field: ReturnType<SchemaView["iterFields"]>[number]): Record<string, unknown> {
  return {
    pointer: field.pointer,
    name: field.name,
    json_type: field.jsonType,
    enum: field.enum,
    required: field.required,
    description: field.description,
    softmeta: field.softmeta,
  };
}

describe("SchemaView (movie compiled schema)", () => {
  const view = SchemaView.load(MOVIE_SCHEMA);

  test("reads contract id and schema hash", () => {
    expect(view.contractId).toBe("example.movies:MoviePage/v1");
    expect(view.schemaSha256).toMatch(/^[0-9a-f]{64}$/);
  });

  test("root softmeta is language-neutral (no generated_from)", () => {
    const meta = view.rootSoftmeta;
    expect(meta.contract).toBe("example.movies:MoviePage/v1");
    expect("generated_from" in meta).toBe(false);
  });

  test("iterFields walks root and nested $ref fields", () => {
    const pointers = view.iterFields().map((f) => f.pointer);
    expect(pointers).toContain("/properties/title");
    expect(pointers).toContain("/properties/cast");
    expect(pointers).toContain("/properties/ratings/properties/rotten_tomatoes");
    expect(pointers).toContain(
      "/properties/ratings/properties/rotten_tomatoes/properties/critics_percent",
    );
  });

  test("typed field lookup", () => {
    const title = view.field("/properties/title");
    expect(title.name).toBe("title");
    expect(title.jsonType).toBe("string");
    expect(title.required).toBe(true);
    expect(title.enum).toBeNull();
    expect(() => view.field("/properties/does_not_exist")).toThrow(
      'no field at pointer "/properties/does_not_exist"',
    );
  });

  test("enum extraction (incl. anyOf nullable enum)", () => {
    expect(view.enumValues("/properties/mpaa_rating")).toEqual([
      "G",
      "PG",
      "PG-13",
      "R",
      "NC-17",
      "NR",
    ]);
  });

  test("softmeta + group/owner/tier filters", () => {
    const meta = view.softmeta("/properties/genres");
    expect(meta.group).toBe("taxonomy");
    expect(meta.tier).toBe("constrained");
    expect(meta.owner).toBe("agent");
    expect(view.fieldsByGroup("taxonomy").map((f) => f.name)).toEqual(["genres"]);
    expect(view.fieldsByOwner("agent").some((f) => f.name === "genres")).toBe(true);
  });

  test("required reflects the schema", () => {
    const required = view
      .iterFields()
      .filter((f) => f.pointer.split("/properties/").length === 2 && f.required)
      .map((f) => f.name);
    expect(new Set(required)).toEqual(
      new Set(["title", "release_year", "runtime_minutes", "directors", "genres", "synopsis", "ratings"]),
    );
  });
});

describe("SchemaView ($ref cycle detection)", () => {
  // A self-referential $def (Node.child -> Node). iter_fields must terminate by
  // tracking the followed $ref on the recursion path. This is a shared parity case
  // with the Python test in test_schema_view.py.
  const cyclic = {
    type: "object",
    properties: { root: { $ref: "#/$defs/Node" } },
    $defs: {
      Node: {
        type: "object",
        properties: {
          name: { type: "string" },
          child: { $ref: "#/$defs/Node" },
        },
      },
    },
  };

  test("terminates and expands one level before the cycle stops", () => {
    const view = new SchemaView(cyclic);
    const pointers = view.iterFields().map((f) => f.pointer);
    expect(pointers).toEqual([
      "/properties/root",
      "/properties/root/properties/name",
      "/properties/root/properties/child",
    ]);
    // The cyclic `child` is surfaced as an unresolved leaf (no further recursion).
    expect(view.field("/properties/root/properties/child").jsonType).toBeNull();
  });
});

describe("SchemaView boundary and union parity", () => {
  test.each(vectors.cases)("matches shared vector $id", (vector) => {
    expect(new SchemaView(vector.schema).iterFields().map(fieldOutput)).toEqual(vector.fields);
  });

  test("constructor and accessors are defensive deep snapshots", () => {
    const schema = {
      "x-softschema": { nested: { labels: ["root"] } },
      type: "object",
      properties: {
        field: {
          type: "string",
          description: "original",
          "x-softschema": { nested: { labels: ["field"] } },
        },
      },
    };
    const view = new SchemaView(schema);

    schema["x-softschema"].nested.labels.push("constructor mutation");
    schema.properties.field.description = "mutated";
    const raw = view.raw;
    (((raw["x-softschema"] as Record<string, unknown>).nested as Record<string, unknown>)
      .labels as string[]).push("raw mutation");
    ((raw.properties as Record<string, Record<string, unknown>>).field as Record<string, unknown>)[
      "description"
    ] = "raw mutation";
    const rootMeta = view.rootSoftmeta;
    ((rootMeta.nested as Record<string, unknown>).labels as string[]).push("root meta mutation");
    const field = view.field("/properties/field");
    ((field.softmeta.nested as Record<string, unknown>).labels as string[]).push("field mutation");

    expect(
      (((view.raw["x-softschema"] as Record<string, unknown>).nested as Record<string, unknown>)
        .labels as string[]),
    ).toEqual(["root"]);
    expect(view.field("/properties/field").description).toBe("original");
    expect(view.softmeta("/properties/field")).toEqual({ nested: { labels: ["field"] } });
  });

  test("load uses the portable mapping-key and resource-limit boundary", () => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-schema-view-"));
    const path = join(directory, "boundary.schema.yaml");
    try {
      writeFileSync(path, "\uFEFFtype: object\n", "utf8");
      expect(SchemaView.load(path).raw).toEqual({ type: "object" });

      writeFileSync(path, "1: value\n", "utf8");
      expect(() => SchemaView.load(path)).toThrow(PortableValueError);

      writeFileSync(path, "properties: [\n", "utf8");
      expect(() => SchemaView.load(path)).toThrow(PortableYamlSyntaxError);

      writeFileSync(path, new Uint8Array([0xff]));
      expect(() => SchemaView.load(path)).toThrow(TypeError);

      writeFileSync(path, "- not\n- a mapping\n", "utf8");
      expect(() => SchemaView.load(path)).toThrow("is not a mapping at the root");

      writeFileSync(path, "type: object\n", "utf8");
      expect(() => SchemaView.load(path, { maxResourceBytes: 1 })).toThrow(PortableValueError);
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  test("envelope inference consumes normalized string keys without coercion", () => {
    expect(inferEnvelopeKey({ softschema: {}, "01": {} })).toBe("01");
  });
});
