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
  "schema_sha256": "b537ea5b1a5e36febe5feaa8f8536fc500ff25c912013b8961bdcde0cb6f7dd3",
  "schema_yaml": [..]
}
? 0
```

# Test: compile --check reports drift for a different contract id

A different `--contract` changes `$id` and the digest, so `--check` against the
committed sidecar reports drift and exits 1.

```console
$ softschema compile examples.movie_page.model:MoviePage --contract wrong:Movie/v1 --out examples/movie_page/movie-page.schema.yaml --check
{
  "drift": true,
  "drift_diff": "committed schema at examples/movie_page/movie-page.schema.yaml differs from compile output",
  "out_path": "examples/movie_page/movie-page.schema.yaml",
  "schema_sha256": "4708c54daa1ef206dd6965b0a5464cfb0e3d23b326fa781dd32c4016b3baf141",
  "schema_yaml": [..]
}
? 1
```
