---
sandbox: true
fixtures:
  # Every journey below rewrites its artifact, so each works in its own directory, named
  # for the journey. Declaring the layout here is what keeps each command line down to the
  # one command the journey is about.
  - {source: ../fixtures/repair-unquoted-colon.md, dest: rescue/repair-unquoted-colon.md}
  - {source: ../fixtures/repair.schema.yaml, dest: rescue/repair.schema.yaml}
  - {source: ../fixtures/repair-scalar-drift.md, dest: drift/repair-scalar-drift.md}
  - {source: ../fixtures/repair.schema.yaml, dest: drift/repair.schema.yaml}
  - {source: ../fixtures/repair-unquoted-colon.md, dest: twice/repair-unquoted-colon.md}
  - {source: ../fixtures/repair.schema.yaml, dest: twice/repair.schema.yaml}
  - {source: ../fixtures/repair-already-valid.md, dest: valid/repair-already-valid.md}
  - {source: ../fixtures/repair.schema.yaml, dest: valid/repair.schema.yaml}
  - {source: ../fixtures/repair-missing-required.md, dest: missing/repair-missing-required.md}
  - {source: ../fixtures/repair.schema.yaml, dest: missing/repair.schema.yaml}
  - {source: ../fixtures/repair-unrepairable.md, dest: floor/repair-unrepairable.md}
  - {source: ../fixtures/repair-unquoted-colon.md, dest: check/repair-unquoted-colon.md}
  - {source: ../fixtures/repair.schema.yaml, dest: check/repair.schema.yaml}
  - {source: ../fixtures/repair-already-valid.md, dest: check-clean/repair-already-valid.md}
  - {source: ../fixtures/repair.schema.yaml, dest: check-clean/repair.schema.yaml}
  - {source: ../fixtures/repair-pure.yaml, dest: pure/repair-pure.yaml}
  - {source: ../fixtures/repair.schema.yaml, dest: pure/repair.schema.yaml}
  # Untouched copies, so the journeys that must prove a file was *not* rewritten have the
  # bytes as authored to diff against.
  - {source: ../fixtures/repair-unquoted-colon.md, dest: original/repair-unquoted-colon.md}
  - {source: ../fixtures/repair-already-valid.md, dest: original/repair-already-valid.md}
  - {source: ../fixtures/repair-missing-required.md, dest: original/repair-missing-required.md}
  - {source: ../fixtures/repair-unrepairable.md, dest: original/repair-unrepairable.md}
env:
  NO_COLOR: "1"
---

# Journey: `validate --repair` rescues a document nothing could read

`--repair` **rewrites the artifact it is given**, which makes this file different from
every other one in the corpus in three ways, all downstream of that write:

- It runs in a **sandbox**: tryscript gives the file a fresh temporary directory and copies
  in the layout declared above. Pointing a mutating command at a checked-in fixture would
  pass once and then fail on a dirty tree, and each journey gets its own directory because
  three of them start from the same fixture and must not inherit each other's writes.
- Those paths are short and stable, which is what lets each transcript below pin the
  **complete JSON result** — the `path` field included — instead of grepping fragments out
  of it. Broad state, per the golden-testing discipline: an unexpected change anywhere in
  the verdict shows up as a diff.
- Each mutating journey prints the file afterward. The write is the deliverable; the
  repaired bytes in the transcript are what surface an emitter that starts restyling what
  it was only asked to quote. The journeys that must prove a file was *left alone* diff it
  against the untouched copy under `original/`.

Without `--repair`, an unquoted `: ` inside a value makes the whole document unreadable —
a total loss over one character, and exit `2` (an input error), not a validation verdict.
The parser's wording is engine-specific, so here (and only here) the stable prefix is
asserted and the rest elided, matching `cli-errors.tryscript.md`.

```console
$ $SOFTSCHEMA validate original/repair-unquoted-colon.md 2>&1
softschema validate: [..]
...
? 2
```

With `--repair` the quotes go back in, the file is written, and the document validates.
The `repairs` array is what distinguishes "was already valid" from "was repaired into
validity" — an exit code cannot say which happened.

```console
$ $SOFTSCHEMA validate rescue/repair-unquoted-colon.md --repair
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
  "path": "rescue/repair-unquoted-colon.md",
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
$ cat rescue/repair-unquoted-colon.md
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
$ $SOFTSCHEMA validate drift/repair-scalar-drift.md --repair
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
  "path": "drift/repair-scalar-drift.md",
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
$ cat drift/repair-scalar-drift.md
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
$ $SOFTSCHEMA validate twice/repair-unquoted-colon.md --repair > /dev/null && cp twice/repair-unquoted-colon.md twice/once.md && $SOFTSCHEMA validate twice/repair-unquoted-colon.md --repair
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
  "path": "twice/repair-unquoted-colon.md",
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
$ diff twice/once.md twice/repair-unquoted-colon.md && echo "bytes unchanged"
bytes unchanged
? 0
```

# Journey: an already-valid document is left byte-identical

The no-widening invariant. `--repair` on a document that needs nothing must not reformat
it, requote it, or touch its line endings.

```console
$ $SOFTSCHEMA validate valid/repair-already-valid.md --repair
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
  "path": "valid/repair-already-valid.md",
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
$ diff original/repair-already-valid.md valid/repair-already-valid.md && echo "byte-identical"
byte-identical
? 0
```

# Journey: a missing field is never invented, a near-miss key never renamed

`reason` where the contract wants `rationale` is a *missing field*, not a type error.
Inferring the rename would be guessing intent, so the document is left exactly as
authored, the `repairs` array stays empty, and the verdict stays honest.

```console
$ $SOFTSCHEMA validate missing/repair-missing-required.md --repair
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
  "path": "missing/repair-missing-required.md",
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
$ diff original/repair-missing-required.md missing/repair-missing-required.md && echo "byte-identical"
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
$ $SOFTSCHEMA validate floor/repair-unrepairable.md --repair --contract test.repair:Doc/v1 --envelope data
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
  "path": "floor/repair-unrepairable.md",
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
$ diff original/repair-unrepairable.md floor/repair-unrepairable.md && echo "byte-identical"
byte-identical
? 0
```

# Journey: `--check-repair` reports without writing

What a gate runs when it wants to know whether an artifact *would* be repaired, without
mutating one under review. Exit `1` means something would change; the file does not.

```console
$ $SOFTSCHEMA validate check/repair-unquoted-colon.md --check-repair
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
  "path": "check/repair-unquoted-colon.md",
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
$ diff original/repair-unquoted-colon.md check/repair-unquoted-colon.md && echo "not written"
not written
? 0
```

On a document that needs nothing, it exits `0`.

```console
$ $SOFTSCHEMA validate check-clean/repair-already-valid.md --check-repair
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
  "path": "check-clean/repair-already-valid.md",
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
$ $SOFTSCHEMA validate pure/repair-pure.yaml --repair
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
  "path": "pure/repair-pure.yaml",
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
$ cat pure/repair-pure.yaml
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
$ $SOFTSCHEMA validate original/repair-already-valid.md --repair --check-repair
softschema validate: --repair and --check-repair are mutually exclusive
? 2
```
