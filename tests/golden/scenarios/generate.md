---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: generate --check reports no drift for the committed marker

`generate` reads the `softschema:generated` marker in the movie README, loads the
referenced sidecar through SchemaView, and re-renders the enum table. Both
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
