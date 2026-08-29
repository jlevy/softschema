---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Journey: `validate --repair` rescues a document nothing could read

`--repair` **rewrites the artifact it is given**, which makes this journey different from
every other one in the corpus in two ways.

Each case copies its fixture into a fresh scratch directory first. Pointing a mutating
command at a checked-in fixture would pass once and then fail on a dirty tree, so the
transcript would only be reproducible on a clean checkout. Each case does its copy and its
command together, so no state has to survive between blocks.

And each mutating case prints the file afterward. The write is the deliverable here: a
transcript showing only the JSON verdict would not have tested the feature, and having the
repaired bytes in the transcript is what lets a reviewer catch an emitter that starts
restyling what it was only asked to quote.

Without `--repair`, an unquoted `: ` inside a value makes the whole document unreadable, so
nothing downstream sees any of it — a total loss over one character. Note that this is exit
`2`, an input error, not a validation verdict.

The parser's wording is engine-specific, so the stable prefix is asserted and the rest is
elided, matching how `cli-errors.md` handles the same class of failure.

```console
$ softschema validate tests/golden/fixtures/repair-unquoted-colon.md 2>&1
softschema validate: [..]
...
? 2
```

With `--repair` the quotes go back in, the file is written, and the document validates.
Only the one scalar differs from the original; the body prose and every other line are
untouched.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-unquoted-colon.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-unquoted-colon.md" --repair > "$D/out.json"; echo "exit=$?"; cat "$D/repair-unquoted-colon.md"
exit=0
---
softschema:
  contract: test.repair:Doc/v1
  schema: repair.schema.yaml
  envelope: data
data:
  name: Acme
  summary: "Note: actually Q1"
---
Body prose stays put.
? 0
```

# Journey: the `repairs` array says what changed

An exit code cannot distinguish "was already valid" from "was repaired into validity", so
the result carries a record per change, shaped like a structural error record.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-unquoted-colon.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-unquoted-colon.md" --repair | grep -A 5 '"repairs"'
  "repairs": [
    {
      "code": "yaml_quoted_scalar",
      "kind": "repair_applied",
      "message": "quoted the value of 'summary'",
      "path": [
? 0
```

# Journey: scalar type drift is conformed

A brand genuinely named `1850` arrives as an integer, because YAML plain scalars carry no
type marker and no serializer was in the path to quote it. Plain `validate` reports it as a
type violation (the exit code below is `grep`'s, not the CLI's; the CLI exits `1`).

```console
$ softschema validate tests/golden/fixtures/repair-scalar-drift.md | grep '"message"'
        "message": "value 1850 is not of type 'string'",
? 0
```

`--repair` writes the quotes the missing serializer would have.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-scalar-drift.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-scalar-drift.md" --repair > /dev/null; echo "exit=$?"; cat "$D/repair-scalar-drift.md"
exit=0
---
softschema:
  contract: test.repair:Doc/v1
  schema: repair.schema.yaml
  envelope: data
data:
  name: '1850'
  summary: A brand named like a number.
---
Body prose stays put.
? 0
```

# Journey: repairing twice changes nothing

Idempotence, visible in the transcript rather than asserted: the second run reports an
empty `repairs` array and the bytes are unchanged.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-unquoted-colon.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-unquoted-colon.md" --repair > /dev/null && cp "$D/repair-unquoted-colon.md" "$D/once.md" && softschema validate "$D/repair-unquoted-colon.md" --repair | grep -A 1 '"repairs"' && diff "$D/once.md" "$D/repair-unquoted-colon.md" && echo "bytes unchanged"
  "repairs": [],
  "semantic": {
bytes unchanged
? 0
```

# Journey: an already-valid document is left byte-identical

The no-widening invariant. `--repair` on a document that needs nothing must not reformat
it, requote it, or touch its line endings.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-already-valid.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-already-valid.md" --repair > /dev/null && diff tests/golden/fixtures/repair-already-valid.md "$D/repair-already-valid.md" && echo "byte-identical"
byte-identical
? 0
```

# Journey: a missing field is never invented, a near-miss key never renamed

`reason` where the contract wants `rationale` is a *missing field*, not a type error.
Inferring the rename would be guessing intent, so the document is left exactly as authored
and the verdict stays honest.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-missing-required.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-missing-required.md" --repair > "$D/out.json"; echo "exit=$?"; grep -c '"repairs": \[\]' "$D/out.json"; diff tests/golden/fixtures/repair-missing-required.md "$D/repair-missing-required.md" && echo "byte-identical"
exit=1
1
byte-identical
? 0
```

# Journey: `--check-repair` reports without writing

What a gate runs when it wants to know whether an artifact *would* be repaired, without
mutating one under review. Exit `1` means something would change; the file does not.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-unquoted-colon.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-unquoted-colon.md" --check-repair > /dev/null; echo "exit=$?"; diff tests/golden/fixtures/repair-unquoted-colon.md "$D/repair-unquoted-colon.md" && echo "not written"
exit=1
not written
? 0
```

On a document that needs nothing, it exits `0`.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-already-valid.md tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-already-valid.md" --check-repair > /dev/null; echo "exit=$?"
exit=0
? 0
```

# Journey: pure-yaml gets the same treatment

The profile with no fence at all, and its payload keys at column 0 — the case the upstream
repair matcher could not reach, because it required leading indentation.

```console
$ D=$(mktemp -d) && cp tests/golden/fixtures/repair-pure.yaml tests/golden/fixtures/repair.schema.yaml "$D/" && softschema validate "$D/repair-pure.yaml" --repair > /dev/null; echo "exit=$?"; cat "$D/repair-pure.yaml"
exit=0
softschema:
  contract: test.repair:Doc/v1
  schema: repair.schema.yaml
  envelope: data
data:
  name: '1850'
  summary: "Note: actually Q1"
? 0
```

# Journey: the two flags are mutually exclusive

```console
$ softschema validate tests/golden/fixtures/repair-already-valid.md --repair --check-repair
softschema validate: --repair and --check-repair are mutually exclusive
? 2
```
