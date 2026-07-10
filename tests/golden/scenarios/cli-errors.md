---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: ambiguous envelope is a usage error (exit 2, message on stderr)

The fixture carries two top-level frontmatter keys (`title` and `record`) and declares
no `softschema.envelope`, so the envelope cannot be inferred. The CLI exits 2 and
explains how to disambiguate with `--envelope`. This message is byte-identical across
implementations, so it is asserted in full on stderr (`!`).

```console
$ softschema validate tests/golden/fixtures/multi-key-no-envelope.md
! softschema validate: multiple top-level frontmatter keys; pass --envelope to designate the softschema payload (candidates: title, record)
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

# Test: a missing artifact file is a stable input error (exit 2)

A nonexistent file emits the portable `input_error/not_found` record and exits 2. The
record never exposes operating-system error prose.

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

# Test: malformed frontmatter is a stable parse error (exit 1)

A readable malformed document emits the portable `parse_error/syntax` record and exits
1. Parser prose and source locations are reserved for the diagnostic-v1 serializer.

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

# Test: parser usage failures exit 2

Both argparse and Commander emit their own usage diagnostic, but the shared contract is
the non-empty stderr output and exit 2.

```console
$ softschema --not-a-real-option 2>&1
...
? 2
```
