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
