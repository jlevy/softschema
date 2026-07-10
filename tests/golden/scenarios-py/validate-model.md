---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: validate --model runs the Pydantic semantic layer (model-only, structural skipped)

Exercises the `--model` loading path: the CLI imports the model and runs semantic
validation (no `--schema`, so structural is skipped as `inferred_via_model`). The model
spec is language-specific; the rest of the output is byte-identical to the other
implementation (semantic logic itself is per-language by design and is not asserted
beyond pass/empty-errors here).

```console
$ softschema validate examples/movie_page/spirited-away.md --model examples.movie_page.model:MoviePage --envelope movie
{
  "contract": {
    "envelope_key": "movie",
    "id": "example.movies:MoviePage/v1",
    "model": "examples.movie_page.model:MoviePage",
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "enforced"
  },
  "contract_id": "example.movies:MoviePage/v1",
  "document_metadata": {
    "contract": "example.movies:MoviePage/v1",
    "envelope": "movie",
    "format": "1",
    "schema": "movie-page.schema.yaml",
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
