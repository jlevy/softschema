import { join } from "node:path";
import { readFileSync } from "node:fs";
import { describe, expect, test } from "bun:test";
import YAML from "yaml";
import { SchemaView } from "../src/schemaView.js";

const MOVIE_SCHEMA = join(import.meta.dir, "../../../examples/movie_page/movie-page.schema.yaml");
const HARDENING_VECTORS = join(import.meta.dir, "../../../tests/vectors/hardening.yaml");

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

describe("SchemaView shared contract", () => {
  const vectors = YAML.parse(readFileSync(HARDENING_VECTORS, "utf8")).schema_view;

  test("preserves ref siblings, snapshots input, and rejects genuine unions", () => {
    const refCase = vectors[0];
    const source = structuredClone(refCase.schema);
    const view = new SchemaView(source);
    source.properties.name.description = "mutated";
    const field = view.field("/properties/name");
    expect({ description: field.description, type: field.jsonType }).toEqual(refCase.expected);

    const unionCase = vectors[1];
    expect(new SchemaView(unionCase.schema).field("/properties/value").jsonType).toBe(
      unionCase.expected.type,
    );
  });

  test("keeps contract and schema identities separate and returns snapshots", () => {
    const view = new SchemaView({
      $id: "https://example.com/schemas/person-v1",
      "x-softschema": { contract: "example.people:Person/v1" },
    });
    expect(view.contractId).toBe("example.people:Person/v1");
    expect(view.schemaId).toBe("https://example.com/schemas/person-v1");
    const raw = view.raw;
    raw.$id = "mutated";
    expect(view.schemaId).toBe("https://example.com/schemas/person-v1");
  });
});
