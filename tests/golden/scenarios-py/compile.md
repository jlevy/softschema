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
  "schema_sha256": "6f06e8140c762cc35168eb136589e563259993ba97b746396909ba6a540f6783",
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
  "schema_sha256": "4a7ad0e7214598faaf28ed7336cd0e75bfde2cc916f9d841eb2ac028804cc19c",
  "schema_yaml": [..]
}
? 1
```
