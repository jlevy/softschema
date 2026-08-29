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
  "outcome": "valid",
  "path": "tests/golden/fixtures/bound-ok.md",
  "profile": "frontmatter-md",
  "repairs": [],
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
    "schema": "movie-page.schema.yaml",
    "status": "enforced"
  },
  "outcome": "valid",
  "path": "examples/movie_page/spirited-away.md",
  "profile": "frontmatter-md",
  "repairs": [],
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
  "outcome": "invalid",
  "path": "tests/golden/fixtures/bound-ok.md",
  "profile": "frontmatter-md",
  "repairs": [],
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
        "code": "missing_property",
        "kind": "schema_violation",
        "message": "required property 'extra' is missing",
        "path": [],
        "property": "extra",
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
  "outcome": "invalid",
  "path": "tests/golden/fixtures/bound-missing-schema.md",
  "profile": "frontmatter-md",
  "repairs": [],
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
  "outcome": "invalid",
  "path": "tests/golden/fixtures/bound-absolute-schema.md",
  "profile": "frontmatter-md",
  "repairs": [],
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
  "outcome": "invalid",
  "path": "tests/golden/fixtures/bound-escaping-schema.md",
  "profile": "frontmatter-md",
  "repairs": [],
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
  "outcome": "invalid",
  "path": "tests/golden/fixtures/bound-envelope-absent.md",
  "profile": "frontmatter-md",
  "repairs": [],
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

# Test: a pure-yaml artifact validates with no flags

The CLI picks the profile from the artifact rather than assuming `frontmatter-md`. A
`*.yaml` file is read as pure-yaml on its name, so the spec's own pure-yaml example
binds its contract from the root `softschema:` block and needs no flags. With no
envelope designated, the whole root minus the metadata block is the payload: pure-yaml
is exempt from single-key inference and multi-key ambiguity rejection, so the two
sibling keys here are the payload rather than an ambiguity error.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-report.yaml
{
  "contract": {
    "envelope_key": null,
    "id": "test.runs:BacktestReport/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.runs:BacktestReport/v1",
  "document_metadata": {
    "contract": "test.runs:BacktestReport/v1",
    "envelope": null,
    "schema": null,
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/fixtures/pure-yaml-report.yaml",
  "profile": "pure-yaml",
  "repairs": [],
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
    "skipped_reason": "no_schema"
  },
  "values": {
    "run_id": "run-2026-04-12T18-03-00Z",
    "summary": "regression vs baseline"
  },
  "warnings": []
}
? 0
```

# Test: an enforced pure-yaml artifact fails against its bound schema

The regression guard for a profile bound to the reader instead of the document: while
`validate` always assumed `frontmatter-md`, a pure-yaml artifact declaring
`status: enforced` reported `no_frontmatter` and validated none of its payload, so a
project could wire this command into CI and get a passing build that checked nothing.
`name: 42` violates the bound schema, so the run must fail structurally with exit 1.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-enforced.yaml
{
  "contract": {
    "envelope_key": null,
    "id": "test.runs:Reading/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "enforced"
  },
  "contract_id": "test.runs:Reading/v1",
  "document_metadata": {
    "contract": "test.runs:Reading/v1",
    "envelope": null,
    "schema": "lenient.schema.yaml",
    "status": "enforced"
  },
  "outcome": "invalid",
  "path": "tests/golden/fixtures/pure-yaml-enforced.yaml",
  "profile": "pure-yaml",
  "repairs": [],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "code": "invalid_value",
        "kind": "schema_violation",
        "message": "value 42 is not of type 'string'",
        "path": [
          "name"
        ],
        "validator": "type",
        "validator_value": "string",
        "value": 42
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "name": 42
  },
  "warnings": []
}
? 1
```

# Test: a pure-yaml artifact honors a declared envelope key

With `envelope:` declared, the named key nests the payload exactly as it does in
frontmatter, so only `reading:` is validated against the contract.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-envelope.yaml
{
  "contract": {
    "envelope_key": "reading",
    "id": "test.runs:Reading/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.runs:Reading/v1",
  "document_metadata": {
    "contract": "test.runs:Reading/v1",
    "envelope": "reading",
    "schema": "lenient.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/fixtures/pure-yaml-envelope.yaml",
  "profile": "pure-yaml",
  "repairs": [],
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
    "name": "sensor-7"
  },
  "warnings": []
}
? 0
```

# Test: --profile overrides detection

The explicit escape hatch, for an artifact whose shape its name and content do not
settle. Forcing `frontmatter-md` on a YAML file makes it the fenceless document it
looks like to that reader, which is the `no_frontmatter` this command reported for
every pure-yaml artifact before detection existed.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-report.yaml --profile frontmatter-md --contract test.runs:BacktestReport/v1
{
  "contract": {
    "envelope_key": null,
    "id": "test.runs:BacktestReport/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.runs:BacktestReport/v1",
  "document_metadata": null,
  "outcome": "invalid",
  "path": "tests/golden/fixtures/pure-yaml-report.yaml",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [],
    "ok": false,
    "skipped_reason": "no_frontmatter"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "no_frontmatter",
        "message": "no frontmatter in tests/golden/fixtures/pure-yaml-report.yaml"
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

# Test: a pure-yaml artifact is detected without a *.yaml name

When the file name does not settle the profile, the document does: a fenceless document
whose whole text is a mapping carrying a root `softschema:` block is pure-yaml. That
block is the spec's metadata block, so finding it at the root is what separates a
pure-yaml artifact from prose that happens to parse as YAML — a Markdown file without
frontmatter still reports `no_frontmatter` as it always has.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-unnamed.data
{
  "contract": {
    "envelope_key": null,
    "id": "test.runs:Reading/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.runs:Reading/v1",
  "document_metadata": {
    "contract": "test.runs:Reading/v1",
    "envelope": null,
    "schema": "lenient.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/fixtures/pure-yaml-unnamed.data",
  "profile": "pure-yaml",
  "repairs": [],
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
    "name": "sensor-7"
  },
  "warnings": []
}
? 0
```
