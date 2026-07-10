---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: compile --check finds no drift against the committed sidecar

`schema_sha256` is shown literally on purpose: it is a deterministic fingerprint
of the canonical schema, so both implementations must produce the same hash. A
divergence in the canonical profile shows up here as a changed digest. The large
`schema_yaml` string is elided; the digest already fingerprints it and the
committed file is checked byte-for-byte by the cross-implementation conformance
test.

```console
$ softschema compile examples.movie_page.model:MoviePage --contract example.movies:MoviePage/v1 --out examples/movie_page/movie-page.schema.yaml --check
{
  "drift": false,
  "drift_diff": null,
  "out_path": "examples/movie_page/movie-page.schema.yaml",
  "schema_sha256": "a8e4d444e314a34b3ad2eb48a7ec124fcacc601bdd522035283a7583f5930521",
  "schema_yaml": [..]
}
? 0
```

# Test: compile --check reports drift for a different contract id

A different `--contract` changes `x-softschema.contract` and the digest, so `--check`
against the committed sidecar reports drift and exits 1.

```console
$ softschema compile examples.movie_page.model:MoviePage --contract wrong:Movie/v1 --out examples/movie_page/movie-page.schema.yaml --check
{
  "drift": true,
  "drift_diff": "committed schema at examples/movie_page/movie-page.schema.yaml differs from compile output",
  "out_path": "examples/movie_page/movie-page.schema.yaml",
  "schema_sha256": "a903e54b6fd7afe7de93e47a701e534fb862a7d46bc779f276e675b7071b4df9",
  "schema_yaml": [..]
}
? 1
```
