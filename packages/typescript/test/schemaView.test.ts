import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { SchemaView } from "../src/schemaView.js";

const MOVIE_SCHEMA = join(import.meta.dir, "../../../examples/movie_page/movie-page.schema.yaml");

describe("SchemaView (movie sidecar)", () => {
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
