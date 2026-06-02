---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: ambiguous envelope is a usage error (exit 2, message on stderr)

The movie artifact carries two top-level frontmatter keys (`title` and `movie`),
so the envelope cannot be inferred. The CLI exits 2 and explains how to
disambiguate with `--envelope`.

```console
$ softschema validate examples/movie_page/spirited-away.md --schema examples/movie_page/movie-page.schema.yaml
! softschema validate: multiple top-level frontmatter keys; pass --envelope to designate the softschema payload (candidates: title, movie)
? 2
```

# Test: a validation implementation is required

```console
$ softschema validate examples/movie_page/spirited-away.md --envelope movie
! softschema validate: missing validation implementation; pass --model, --schema, or both
? 2
```
