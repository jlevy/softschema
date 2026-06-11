---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: generate --check reports no drift for the committed marker

`generate` reads the `softschema:generated` marker in the movie README, loads the
referenced compiled schema through SchemaView, and re-renders the enum table. Both
implementations render byte-identical bodies, so `--check` reports no drift.

```console
$ softschema generate examples/movie_page/README.md --check
{
  "check": true,
  "drift": false,
  "files": [
    {
      "drift": false,
      "drift_details": [],
      "path": "examples/movie_page/README.md",
      "sections": 1
    }
  ]
}
? 0
```

# Test: generate --check reports drift for a stale section (exit 1)

A fixture whose committed `enum_table` body is wrong drifts from the schema; `--check`
reports it and exits 1. The drift detail names the file and section, byte-identical
across implementations.

```console
$ softschema generate tests/golden/fixtures/stale-generated.md --check
{
  "check": true,
  "drift": true,
  "files": [
    {
      "drift": true,
      "drift_details": [
        "tests/golden/fixtures/stale-generated.md: section enum_table drifted"
      ],
      "path": "tests/golden/fixtures/stale-generated.md",
      "sections": 1
    }
  ]
}
? 1
```

# Test: a marker using the legacy contract= attribute is rejected (exit 2)

The path attribute is now `schema=`; a marker still using `contract=` (which named a
schema *path* in 0.1) is rejected with a rename hint, because a contract is a logical ID,
not a file path. The message is byte-identical across implementations, so it is asserted
in full on stderr (`!`).

```console
$ softschema generate tests/golden/fixtures/legacy-contract-marker.md
! softschema generate: tests/golden/fixtures/legacy-contract-marker.md: softschema:generated marker uses the removed "contract" attribute for a schema path; rename it to "schema" (contract is a logical ID, not a file path)
? 2
```
