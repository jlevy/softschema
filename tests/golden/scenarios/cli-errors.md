---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: ambiguous envelope is a usage error (exit 2, message on stderr)

The movie artifact carries two top-level frontmatter keys (`title` and `movie`), so the
envelope cannot be inferred. The CLI exits 2 and explains how to disambiguate with
`--envelope`. This message is byte-identical across implementations, so it is asserted in
full on stderr (`!`).

```console
$ softschema validate examples/movie_page/spirited-away.md --schema examples/movie_page/movie-page.schema.yaml
! softschema validate: multiple top-level frontmatter keys; pass --envelope to designate the softschema payload (candidates: title, movie)
? 2
```

# Test: an unknown key in the softschema block is rejected (exit 2)

The spec makes unknown `softschema:` keys a validation error. The diagnostic wording is
engine-specific (Pydantic's multi-line report vs a one-line message), so the stable
prefix is asserted and the tail elided.

```console
$ softschema validate tests/golden/fixtures/unknown-metadata-key.md 2>&1
softschema validate: [..]
...
? 2
```

# Test: a malformed contract ID is rejected by the grammar (exit 2)

The contract ID `bad id with spaces` violates the enforced grammar (whitespace, no
namespace/name shape). Both CLIs reject it at metadata-parse time with exit 2; the
diagnostic wording is engine-specific (Pydantic's multi-line report vs a one-line
message), so the stable prefix is asserted and the tail elided.

```console
$ softschema validate tests/golden/fixtures/malformed-contract.md --schema examples/movie_page/movie-page.schema.yaml --envelope record 2>&1
softschema validate: [..]
...
? 2
```

# Test: a missing artifact file is a clean usage error (exit 2)

A nonexistent file exits 2 with a one-line message and no stdout, never a traceback. The
exact OS/engine wording after the `softschema validate:` prefix is intentionally
implementation-specific (Python `[Errno 2] No such file or directory` vs Node `ENOENT`),
so only the stable prefix is asserted; the divergent tail is elided with `[..]`. Streams
are merged with `2>&1` so the single error line is matched as output.

```console
$ softschema validate tests/golden/fixtures/does-not-exist.md --schema examples/movie_page/movie-page.schema.yaml --contract example.movies:MoviePage/v1 --envelope movie 2>&1
softschema validate: [..]
? 2
```

# Test: malformed frontmatter is a clean parse error (exit 2)

The error text is multi-line and engine-specific, so the stable prefix is asserted and
the remaining lines are elided with `...`.

```console
$ softschema validate tests/golden/fixtures/malformed-frontmatter.md --schema examples/movie_page/movie-page.schema.yaml --contract example.movies:MoviePage/v1 --envelope movie 2>&1
softschema validate: [..]
...
? 2
```

# Test: inspect on a missing file is a clean usage error (exit 2)

```console
$ softschema inspect tests/golden/fixtures/does-not-exist.md 2>&1
softschema inspect: [..]
? 2
```

# Test: inspect on a malformed softschema block is a clean error (exit 2)

The `softschema:` block is a list, not a string or mapping. Both CLIs reject it with exit
2; the trailing type name differs (`got list` vs `got object`), so only the stable prefix
is asserted.

```console
$ softschema inspect tests/golden/fixtures/malformed-meta.md 2>&1
softschema inspect: [..]
? 2
```

# Test: docs with an unknown topic exits 2

Both CLIs reject an unknown topic with exit 2. The diagnostic differs in structure
(argparse usage text vs a one-line message), so only the exit code and a non-empty
diagnostic are asserted.

```console
$ softschema docs no-such-topic 2>&1
...
? 2
```

# Test: generate on a missing file is a clean usage error (exit 2)

Runtime errors in `generate` exit 2 with the `softschema generate:` prefix; exit 1 is
reserved for `--check` drift. The tail after the prefix is engine-specific (Python
`[Errno 2]` vs Node `ENOENT`), so only the stable prefix is asserted.

```console
$ softschema generate tests/golden/fixtures/does-not-exist.md 2>&1
softschema generate: [..]
? 2
```
