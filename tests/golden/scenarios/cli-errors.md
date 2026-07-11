---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: ambiguous envelope is a usage error

```console
$ softschema validate tests/golden/fixtures/multi-key-no-envelope.md
! softschema validate: multiple top-level frontmatter keys; pass --envelope to designate the softschema payload (candidates: title, record)
? 2
```

# Test: an unknown metadata key is rejected

The detailed model wording is runtime-specific, so only the stable command boundary is
shared.

```console
$ softschema validate tests/golden/fixtures/unknown-metadata-key.md 2>&1
softschema validate: [..]
...
? 2
```

# Test: a missing artifact is a portable input error

```console
$ softschema validate tests/golden/fixtures/does-not-exist.md --schema examples/movie_page/movie-page.schema.yaml --contract example.movies:MoviePage/v1 --envelope movie 2>&1
{
  "kind": "input_error",
  "message": "artifact path does not exist",
  "reason": "not_found",
  "source": "tests/golden/fixtures/does-not-exist.md"
}
? 2
```

# Test: malformed frontmatter is a portable parse error

```console
$ softschema validate tests/golden/fixtures/malformed-frontmatter.md --schema examples/movie_page/movie-page.schema.yaml --contract example.movies:MoviePage/v1 --envelope movie 2>&1
{
  "kind": "parse_error",
  "message": "artifact is not valid YAML",
  "reason": "syntax",
  "source": "tests/golden/fixtures/malformed-frontmatter.md"
}
? 1
```

# Test: parser usage failures exit two

```console
$ softschema --not-a-real-option 2>&1
...
? 2
```
