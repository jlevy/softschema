---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: validate the movie example (structural + semantic ok)

The neutral `softschema` command resolves to `softschema-py` or `softschema-ts`
depending on `SOFTSCHEMA_IMPL` (see `tests/golden/run.sh`). Both implementations
must produce byte-identical output.

```console
$ softschema validate examples/movie_page/spirited-away.md --model examples.movie_page.model:MoviePage --schema examples/movie_page/movie-page.schema.yaml --envelope movie
{
  "contract": {
    "envelope_key": "movie",
    "id": "example.movies:MoviePage/v1",
    "model": "examples.movie_page.model:MoviePage",
    "profile": "frontmatter-md",
    "schema_path": "examples/movie_page/movie-page.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "example.movies:MoviePage/v1",
  "document_metadata": {
    "contract": "example.movies:MoviePage/v1",
    "status": "enforced"
  },
  "path": "examples/movie_page/spirited-away.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "cast": [
      {
        "actor": "Rumi Hiiragi",
        "character": "Chihiro / Sen"
      },
      {
        "actor": "Miyu Irino",
        "character": "Haku"
      },
      {
        "actor": "Mari Natsuki",
        "character": "Yubaba"
      }
    ],
    "directors": [
      "Hayao Miyazaki"
    ],
    "genres": [
      "Animation",
      "Adventure",
      "Family"
    ],
    "mpaa_rating": "PG",
    "ratings": {
      "imdb": {
        "score": 8.6,
        "total_votes": 850000
      },
      "rotten_tomatoes": {
        "audience_percent": 96,
        "critic_review_count": 225,
        "critics_percent": 96
      }
    },
    "release_year": 2001,
    "runtime_minutes": 125,
    "synopsis": "Ten-year-old Chihiro and her parents stumble into a mysterious abandoned town that turns out to be a spirit world. After her parents are transformed into pigs, Chihiro must take a job in a magical bathhouse run by the witch Yubaba and find a way to break the spell so the family can return home.\n",
    "title": "Spirited Away"
  },
  "warnings": []
}
? 0
```

# Test: structural validation failure (schema only, engine-neutral records)

Validating against only the schema (no `--model`) keeps the output free of
implementation-specific semantic errors, so the structural error records are
identical across implementations. Errors are sorted by (path, validator).

```console
$ softschema validate tests/golden/fixtures/bad-movie.md --schema examples/movie_page/movie-page.schema.yaml --contract example.movies:MoviePage/v1 --envelope movie
{
  "contract": {
    "envelope_key": "movie",
    "id": "example.movies:MoviePage/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "examples/movie_page/movie-page.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "example.movies:MoviePage/v1",
  "document_metadata": {
    "contract": "example.movies:MoviePage/v1",
    "status": "enforced"
  },
  "path": "tests/golden/fixtures/bad-movie.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_pydantic_model"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "schema_violation",
        "message": "array is shorter than the minimum of 1 items",
        "path": [
          "directors"
        ],
        "validator": "minItems",
        "validator_value": 1,
        "value": []
      },
      {
        "kind": "schema_violation",
        "message": "value 1500 is less than the minimum of 1888",
        "path": [
          "release_year"
        ],
        "validator": "minimum",
        "validator_value": 1888,
        "value": 1500
      },
      {
        "kind": "schema_violation",
        "message": "value 0 is not greater than 0",
        "path": [
          "runtime_minutes"
        ],
        "validator": "exclusiveMinimum",
        "validator_value": 0,
        "value": 0
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "directors": [],
    "genres": [
      "Drama"
    ],
    "ratings": {},
    "release_year": 1500,
    "runtime_minutes": 0,
    "synopsis": "A structurally invalid record.",
    "title": "Broken"
  },
  "warnings": []
}
? 1
```
