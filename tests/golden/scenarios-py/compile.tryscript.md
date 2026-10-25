---
cwd: ../../..
env:
  NO_COLOR: "1"
---

# Test: compile --check finds no drift against the committed sidecar

`schema_sha256` is shown literally on purpose: it is a deterministic fingerprint
of the canonical schema, so both implementations must produce the same hash. A
divergence in the canonical profile shows up here as a changed digest. The large
`schema_yaml` string is elided; the digest already fingerprints it and the
committed file is checked byte-for-byte by the cross-implementation conformance
test.

```console
$ $SOFTSCHEMA compile examples.movie_page.model:MoviePage --contract example.movies:MoviePage/v1 --out examples/movie_page/movie-page.schema.yaml --check
{
  "drift": false,
  "drift_diff": null,
  "out_path": "examples/movie_page/movie-page.schema.yaml",
  "schema_sha256": "6ee3e6803df2958ec1e58a20c71f0999f4fc7225c533b3732f2904fbb1dee6dd",
  "schema_yaml": [..]
}
? 0
```

# Test: compile --check reports drift for a different contract id

A different `--contract` changes compiler-owned contract metadata, the generated root
title, and the digest, so `--check` against the committed sidecar reports drift and
exits 1.

```console
$ $SOFTSCHEMA compile examples.movie_page.model:MoviePage --contract wrong:Movie/v1 --out examples/movie_page/movie-page.schema.yaml --check
{
  "drift": true,
  "drift_diff": "committed schema at examples/movie_page/movie-page.schema.yaml differs from compile output",
  "out_path": "examples/movie_page/movie-page.schema.yaml",
  "schema_sha256": "57d9e54b19f628aff12949d6b8fb109c5ed520310dde6b81aa5b5ff2ec7dae81",
  "schema_yaml": [..]
}
? 1
```

# Test: compile refuses a --schema-id that validation would refuse (exit 2)

`--schema-id` becomes the root `$id`, so compile applies validation’s resource-identity
grammar before writing or checking anything: a `urn:` without a namespace identifier, a
relative id, and a malformed host are refused with exit 2. The messages are
byte-identical across implementations, so they are asserted in full on stderr (`!`).

```console
$ $SOFTSCHEMA compile examples.movie_page.model:MoviePage --contract example.movies:MoviePage/v1 --out examples/movie_page/movie-page.schema.yaml --check --schema-id urn:example
! softschema compile: the root $id must name a lowercase namespace identifier and a name, as in urn:example:name, got "urn:example"
? 2
```

```console
$ $SOFTSCHEMA compile examples.movie_page.model:MoviePage --contract example.movies:MoviePage/v1 --out examples/movie_page/movie-page.schema.yaml --check --schema-id schemas/movie.json
! softschema compile: the root $id must be an absolute URI, got "schemas/movie.json"
? 2
```

```console
$ $SOFTSCHEMA compile examples.movie_page.model:MoviePage --contract example.movies:MoviePage/v1 --out examples/movie_page/movie-page.schema.yaml --check --schema-id 'http://[::1'
! softschema compile: the root $id must have a lowercase host name or a canonical IP address, an optional non-default port, and no user information, got "http://[::1"
? 2
```
