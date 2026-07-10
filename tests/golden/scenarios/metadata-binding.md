---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: a self-describing artifact validates with no flags

The fixture declares the full metadata quartet (`contract`, `schema`, `envelope`,
`status` defaulted): the compiled schema resolves relative to the document and the
declared envelope picks the payload out of a multi-key frontmatter, so
`softschema validate <doc>` needs no flags at all.

```console
$ softschema validate tests/golden/fixtures/bound-ok.md
{
  "contract": {
    "envelope_key": "data",
    "id": "test.bind:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.bind:Doc/v1",
  "document_metadata": {
    "contract": "test.bind:Doc/v1",
    "envelope": "data",
    "schema": "error-norm.schema.yaml",
    "status": null
  },
  "path": "tests/golden/fixtures/bound-ok.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "title": "Hello",
    "year": 2001
  },
  "warnings": []
}
? 0
```

# Test: the flagship movie example validates with no flags

The committed example artifact is fully self-describing (`contract`, `schema`,
`envelope`, `status: enforced`), so the quickstart is a zero-flag command even though
the artifact also carries a host `title:` key.

```console
$ softschema validate examples/movie_page/spirited-away.md
{
  "contract": {
    "envelope_key": "movie",
    "id": "example.movies:MoviePage/v1",
    "model": null,
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
    "skipped_reason": "no_semantic_model"
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

# Test: --schema overrides the document's softschema.schema binding

The artifact's own binding (`error-norm.schema.yaml`) passes; pointing `--schema` at a
schema that additionally requires `extra` proves the flag outranks the metadata: the
run fails with that schema's error, not the binding's success.

```console
$ softschema validate tests/golden/fixtures/bound-ok.md --schema tests/golden/fixtures/requires-extra.schema.yaml
{
  "contract": {
    "envelope_key": "data",
    "id": "test.bind:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/requires-extra.schema.yaml",
    "status": "soft"
  },
  "contract_id": "test.bind:Doc/v1",
  "document_metadata": {
    "contract": "test.bind:Doc/v1",
    "envelope": "data",
    "schema": "error-norm.schema.yaml",
    "status": null
  },
  "path": "tests/golden/fixtures/bound-ok.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "schema_violation",
        "message": "required property ['title', 'year', 'extra'] is missing",
        "path": [],
        "validator": "required",
        "validator_value": [
          "title",
          "year",
          "extra"
        ],
        "value": {
          "title": "Hello",
          "year": 2001
        }
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "title": "Hello",
    "year": 2001
  },
  "warnings": []
}
? 1
```

# Test: a bound schema that does not exist is schema_missing (exit 1)

```console
$ softschema validate tests/golden/fixtures/bound-missing-schema.md
{
  "contract": {
    "envelope_key": "data",
    "id": "test.bind:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.bind:Doc/v1",
  "document_metadata": {
    "contract": "test.bind:Doc/v1",
    "envelope": null,
    "schema": "no-such.schema.yaml",
    "status": null
  },
  "path": "tests/golden/fixtures/bound-missing-schema.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "schema_missing",
        "message": "compiled schema not found: no-such.schema.yaml",
        "path": "no-such.schema.yaml"
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "title": "Hello",
    "year": 2001
  },
  "warnings": []
}
? 1
```

# Test: an absolute path in softschema.schema is rejected (exit 1)

A document may only bind a relative path; absolute paths are caller territory
(`--schema`).

```console
$ softschema validate tests/golden/fixtures/bound-absolute-schema.md
{
  "contract": {
    "envelope_key": "data",
    "id": "test.bind:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.bind:Doc/v1",
  "document_metadata": {
    "contract": "test.bind:Doc/v1",
    "envelope": null,
    "schema": "/etc/error-norm.schema.yaml",
    "status": null
  },
  "path": "tests/golden/fixtures/bound-absolute-schema.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "schema_missing",
        "message": "softschema.schema must be a relative path: /etc/error-norm.schema.yaml",
        "path": "/etc/error-norm.schema.yaml"
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "title": "Hello",
    "year": 2001
  },
  "warnings": []
}
? 1
```

# Test: a softschema.schema path escaping the bound is rejected (exit 1)

Relative values resolve from the document's directory and must stay inside the document
directory or the working directory, so a `../../...` value cannot bind an arbitrary
file.

```console
$ softschema validate tests/golden/fixtures/bound-escaping-schema.md
{
  "contract": {
    "envelope_key": "data",
    "id": "test.bind:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.bind:Doc/v1",
  "document_metadata": {
    "contract": "test.bind:Doc/v1",
    "envelope": null,
    "schema": "../../../../../../../../etc/error-norm.schema.yaml",
    "status": null
  },
  "path": "tests/golden/fixtures/bound-escaping-schema.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "schema_missing",
        "message": "softschema.schema escapes the document directory and the working directory: ../../../../../../../../etc/error-norm.schema.yaml",
        "path": "../../../../../../../../etc/error-norm.schema.yaml"
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "title": "Hello",
    "year": 2001
  },
  "warnings": []
}
? 1
```

# Test: a non-string softschema.schema is a metadata error (exit 2)

The metadata block is rejected at parse time; the diagnostic wording is
engine-specific, so the stable prefix is asserted and the tail elided.

```console
$ softschema validate tests/golden/fixtures/bound-bad-value.md 2>&1
softschema validate: [..]
...
? 2
```

# Test: a declared envelope absent from the document is envelope_mismatch (exit 1)

```console
$ softschema validate tests/golden/fixtures/bound-envelope-absent.md
{
  "contract": {
    "envelope_key": "data",
    "id": "test.bind:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.bind:Doc/v1",
  "document_metadata": {
    "contract": "test.bind:Doc/v1",
    "envelope": "data",
    "schema": "error-norm.schema.yaml",
    "status": null
  },
  "path": "tests/golden/fixtures/bound-envelope-absent.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": false,
    "skipped_reason": "envelope_mismatch"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "actual_keys": [
          "record"
        ],
        "expected_key": "data",
        "kind": "envelope_mismatch",
        "message": "contract 'test.bind:Doc/v1' expects 'data'"
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": null,
  "warnings": []
}
? 1
```
