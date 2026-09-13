---
cwd: ../../..
env:
  NO_COLOR: "1"
---

# Test: validate --model runs the Zod semantic layer

Exercises the `--model` loading path with a bound structural schema. Both layer records
show completed execution. A later semantic rejection proves that the schema's acceptance
does not determine the complete verdict. Semantic error details remain language-specific.

```console
$ $SOFTSCHEMA validate examples/movie_page/spirited-away.md --model packages/typescript/test/fixtures/movie-model.mjs:MoviePage --envelope movie
{
  "contract": {
    "envelope_key": "movie",
    "id": "example.movies:MoviePage/v1",
    "model": "packages/typescript/test/fixtures/movie-model.mjs:MoviePage",
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "enforced"
  },
  "contract_id": "example.movies:MoviePage/v1",
  "document_metadata": {
    "contract": "example.movies:MoviePage/v1",
    "envelope": "movie",
    "schema": "movie-page.schema.yaml",
    "status": "enforced"
  },
  "outcome": "valid",
  "path": "examples/movie_page/spirited-away.md",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [],
    "execution": "completed",
    "ok": true,
    "skipped_reason": null
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "execution": "completed",
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

The schema accepts the payload's types while a model invariant rejects its name. The
complete result must retain both verdicts and serialize the semantic error as plain data.

```console
$ $SOFTSCHEMA validate tests/golden/fixtures/execution-rejected.md --model packages/typescript/test/fixtures/execution-model.mjs:Sample
{
  "contract": {
    "envelope_key": "sample",
    "id": "example:Sample/v1",
    "model": "packages/typescript/test/fixtures/execution-model.mjs:Sample",
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "enforced"
  },
  "contract_id": "example:Sample/v1",
  "document_metadata": {
    "contract": "example:Sample/v1",
    "envelope": "sample",
    "schema": "execution.schema.yaml",
    "status": "enforced"
  },
  "outcome": "invalid",
  "path": "tests/golden/fixtures/execution-rejected.md",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [
      {
        "code": "custom",
        "message": "name is unavailable",
        "path": []
      }
    ],
    "execution": "completed",
    "ok": false,
    "skipped_reason": null
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "execution": "completed",
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "rejected"
  },
  "warnings": []
}
? 1
```
