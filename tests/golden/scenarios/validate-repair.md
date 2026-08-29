---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Journey: `validate --repair` rescues a document nothing could read

`--repair` **rewrites the artifact it is given**, which makes this file different from
every other one in the corpus in three ways, all downstream of that write:

- Each journey copies its fixture into a scratch directory first. Pointing a mutating
  command at a checked-in fixture would pass once and then fail on a dirty tree.
- The scratch directory is a **fixed path**, recreated by the same command that uses it
  (tryscript gives each command a fresh shell, so no variable survives between commands —
  but the filesystem does). A fixed path is what lets the transcripts below pin the
  **complete JSON result**, byte for byte with the `path` field included, instead of
  grepping fragments out of it: broad state, per the golden-testing discipline, so an
  unexpected change anywhere in the verdict shows up as a diff.
- Each mutating journey prints the file afterward. The write is the deliverable; the
  repaired bytes in the transcript are what surface an emitter that starts restyling what
  it was only asked to quote.

Without `--repair`, an unquoted `: ` inside a value makes the whole document unreadable —
a total loss over one character, and exit `2` (an input error), not a validation verdict.
The parser's wording is engine-specific, so here (and only here) the stable prefix is
asserted and the rest elided, matching `cli-errors.md`.

```console
$ softschema validate tests/golden/fixtures/repair-unquoted-colon.md 2>&1
softschema validate: [..]
...
? 2
```

With `--repair` the quotes go back in, the file is written, and the document validates.
The `repairs` array is what distinguishes "was already valid" from "was repaired into
validity" — an exit code cannot say which happened.

```console
$ D=tests/golden/tmp/repair-rescue && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-unquoted-colon.md tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-unquoted-colon.md" --repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/tmp/repair-rescue/repair-unquoted-colon.md",
  "profile": "frontmatter-md",
  "repairs": [
    {
      "code": "yaml_quoted_scalar",
      "kind": "repair_applied",
      "message": "quoted the value of 'summary'",
      "path": [
        "summary"
      ]
    }
  ],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "Acme",
    "summary": "Note: actually Q1"
  },
  "warnings": []
}
? 0
```

Only the one scalar differs from the original; the body prose and every other line are
untouched.

```console
$ cat tests/golden/tmp/repair-rescue/repair-unquoted-colon.md
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

# Journey: scalar type drift is conformed

A brand genuinely named `1850` arrives as an integer, because YAML plain scalars carry no
type marker and no serializer was in the path to quote it. `--repair` writes the quotes
the missing serializer would have; the scalar's own source text is the replacement.

```console
$ D=tests/golden/tmp/repair-drift && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-scalar-drift.md tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-scalar-drift.md" --repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/tmp/repair-drift/repair-scalar-drift.md",
  "profile": "frontmatter-md",
  "repairs": [
    {
      "code": "scalar_conformed",
      "kind": "conform_applied",
      "message": "conformed 1850 to the string '1850'",
      "path": [
        "name"
      ]
    }
  ],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "1850",
    "summary": "A brand named like a number."
  },
  "warnings": []
}
? 0
```

```console
$ cat tests/golden/tmp/repair-drift/repair-scalar-drift.md
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

Idempotence, visible rather than asserted: the second run's complete result shows an
empty `repairs` array, and the bytes on disk are unchanged.

```console
$ D=tests/golden/tmp/repair-twice && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-unquoted-colon.md tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-unquoted-colon.md" --repair > /dev/null && cp "$D/repair-unquoted-colon.md" "$D/once.md" && softschema validate "$D/repair-unquoted-colon.md" --repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/tmp/repair-twice/repair-unquoted-colon.md",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "Acme",
    "summary": "Note: actually Q1"
  },
  "warnings": []
}
? 0
```

```console
$ diff tests/golden/tmp/repair-twice/once.md tests/golden/tmp/repair-twice/repair-unquoted-colon.md && echo "bytes unchanged"
bytes unchanged
? 0
```

# Journey: an already-valid document is left byte-identical

The no-widening invariant. `--repair` on a document that needs nothing must not reformat
it, requote it, or touch its line endings.

```console
$ D=tests/golden/tmp/repair-valid && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-already-valid.md tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-already-valid.md" --repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/tmp/repair-valid/repair-already-valid.md",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "Acme",
    "summary": "Already fine."
  },
  "warnings": []
}
? 0
```

```console
$ diff tests/golden/fixtures/repair-already-valid.md tests/golden/tmp/repair-valid/repair-already-valid.md && echo "byte-identical"
byte-identical
? 0
```

# Journey: a missing field is never invented, a near-miss key never renamed

`reason` where the contract wants `rationale` is a *missing field*, not a type error.
Inferring the rename would be guessing intent, so the document is left exactly as
authored, the `repairs` array stays empty, and the verdict stays honest.

```console
$ D=tests/golden/tmp/repair-missing && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-missing-required.md tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-missing-required.md" --repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "invalid",
  "path": "tests/golden/tmp/repair-missing/repair-missing-required.md",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "code": "missing_property",
        "kind": "schema_violation",
        "message": "required property 'summary' is missing",
        "path": [],
        "property": "summary",
        "validator": "required",
        "validator_value": [
          "name",
          "summary"
        ],
        "value": {
          "name": "Acme",
          "reason": "a near-miss key, not a rename"
        }
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "name": "Acme",
    "reason": "a near-miss key, not a rename"
  },
  "warnings": []
}
? 1
```

```console
$ diff tests/golden/fixtures/repair-missing-required.md tests/golden/tmp/repair-missing/repair-missing-required.md && echo "byte-identical"
byte-identical
? 0
```

# Journey: a document repair cannot rescue reports its real failure

The escalation has a floor: when quoting does not make the document parse, `--repair`
reports exactly what plain `validate` reports — the parse failure, not a repair artifact
of its own — and the file is left exactly as it was found. The binding is passed as flags
because the document's own `softschema:` block sits inside the very frontmatter that
cannot be read. The parse-failure `message` is engine wording, so that one line is
elided; every other field is pinned.

```console
$ D=tests/golden/tmp/repair-floor && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-unrepairable.md "$D" && softschema validate "$D/repair-unrepairable.md" --repair --contract test.repair:Doc/v1 --envelope data
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": null,
  "outcome": "invalid",
  "path": "tests/golden/tmp/repair-floor/repair-unrepairable.md",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [],
    "ok": false,
    "skipped_reason": "yaml_parse_error"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "yaml_parse_error",
        "message": [..]
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": null,
  "warnings": []
}
? 1
```

```console
$ diff tests/golden/fixtures/repair-unrepairable.md tests/golden/tmp/repair-floor/repair-unrepairable.md && echo "byte-identical"
byte-identical
? 0
```

# Journey: `--check-repair` reports without writing

What a gate runs when it wants to know whether an artifact *would* be repaired, without
mutating one under review. Exit `1` means something would change; the file does not.

```console
$ D=tests/golden/tmp/repair-check && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-unquoted-colon.md tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-unquoted-colon.md" --check-repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/tmp/repair-check/repair-unquoted-colon.md",
  "profile": "frontmatter-md",
  "repairs": [
    {
      "code": "yaml_quoted_scalar",
      "kind": "repair_applied",
      "message": "quoted the value of 'summary'",
      "path": [
        "summary"
      ]
    }
  ],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "Acme",
    "summary": "Note: actually Q1"
  },
  "warnings": []
}
? 1
```

```console
$ diff tests/golden/fixtures/repair-unquoted-colon.md tests/golden/tmp/repair-check/repair-unquoted-colon.md && echo "not written"
not written
? 0
```

On a document that needs nothing, it exits `0`.

```console
$ D=tests/golden/tmp/repair-check-clean && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-already-valid.md tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-already-valid.md" --check-repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/tmp/repair-check-clean/repair-already-valid.md",
  "profile": "frontmatter-md",
  "repairs": [],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "Acme",
    "summary": "Already fine."
  },
  "warnings": []
}
? 0
```

# Journey: pure-yaml gets the same treatment

The profile with no fence at all, and its payload keys at column 0 — the case the
upstream repair matcher could not reach, because it required leading indentation.

```console
$ D=tests/golden/tmp/repair-pure && rm -rf "$D" && mkdir -p "$D" && cp tests/golden/fixtures/repair-pure.yaml tests/golden/fixtures/repair.schema.yaml "$D" && softschema validate "$D/repair-pure.yaml" --repair
{
  "contract": {
    "envelope_key": "data",
    "id": "test.repair:Doc/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.repair:Doc/v1",
  "document_metadata": {
    "contract": "test.repair:Doc/v1",
    "envelope": "data",
    "schema": "repair.schema.yaml",
    "status": null
  },
  "outcome": "valid",
  "path": "tests/golden/tmp/repair-pure/repair-pure.yaml",
  "profile": "pure-yaml",
  "repairs": [
    {
      "code": "yaml_quoted_scalar",
      "kind": "repair_applied",
      "message": "quoted the value of 'summary'",
      "path": [
        "summary"
      ]
    },
    {
      "code": "scalar_conformed",
      "kind": "conform_applied",
      "message": "conformed 1850 to the string '1850'",
      "path": [
        "name"
      ]
    }
  ],
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "name": "1850",
    "summary": "Note: actually Q1"
  },
  "warnings": []
}
? 0
```

```console
$ cat tests/golden/tmp/repair-pure/repair-pure.yaml
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
