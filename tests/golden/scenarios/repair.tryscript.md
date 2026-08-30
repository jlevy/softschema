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
  - {source: ../fixtures/repair-unquoted-colon.md, dest: dry/repair-unquoted-colon.md}
  - {source: ../fixtures/repair.schema.yaml, dest: dry/repair.schema.yaml}
  - {source: ../fixtures/repair-unquoted-colon.md, dest: check/repair-unquoted-colon.md}
  - {source: ../fixtures/repair.schema.yaml, dest: check/repair.schema.yaml}
  - {source: ../fixtures/repair-already-valid.md, dest: check-clean/repair-already-valid.md}
  - {source: ../fixtures/repair.schema.yaml, dest: check-clean/repair.schema.yaml}
  - {source: ../fixtures/repair-pure.yaml, dest: pure/repair-pure.yaml}
  - {source: ../fixtures/repair-unterminated-fence.md, dest: fence/repair-unterminated-fence.md}
  - {source: ../fixtures/repair-ends-at-fence.md, dest: fence/repair-ends-at-fence.md}
  - {source: ../fixtures/repair.schema.yaml, dest: fence/repair.schema.yaml}
  # The BOM journey needs both twins side by side: the whole assertion is that they
  # converge, so the plain one has to be repaired in the same directory to diff against.
  - {source: ../fixtures/repair-bom.md, dest: bom/repair-bom.md}
  - {source: ../fixtures/repair-unquoted-colon.md, dest: bom/repair-unquoted-colon.md}
  - {source: ../fixtures/repair.schema.yaml, dest: bom/repair.schema.yaml}
  - {source: ../fixtures/repair.schema.yaml, dest: pure/repair.schema.yaml}
  # Untouched copies, so the journeys that must prove a file was *not* rewritten have the
  # bytes as authored to diff against.
  - {source: ../fixtures/repair-unquoted-colon.md, dest: original/repair-unquoted-colon.md}
  - {source: ../fixtures/repair-already-valid.md, dest: original/repair-already-valid.md}
  - {source: ../fixtures/repair-missing-required.md, dest: original/repair-missing-required.md}
  - {source: ../fixtures/repair-unrepairable.md, dest: original/repair-unrepairable.md}
  - {source: ../fixtures/repair-unterminated-fence.md, dest: original/repair-unterminated-fence.md}
env:
  NO_COLOR: "1"
---

# Journey: `repair` rescues a document nothing could read

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
$ $SOFTSCHEMA repair rescue/repair-unquoted-colon.md
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
$ $SOFTSCHEMA repair drift/repair-scalar-drift.md
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
$ $SOFTSCHEMA repair twice/repair-unquoted-colon.md > /dev/null && cp twice/repair-unquoted-colon.md twice/once.md && $SOFTSCHEMA repair twice/repair-unquoted-colon.md
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
$ $SOFTSCHEMA repair valid/repair-already-valid.md
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
$ $SOFTSCHEMA repair missing/repair-missing-required.md
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
$ $SOFTSCHEMA repair floor/repair-unrepairable.md --contract test.repair:Doc/v1 --envelope data
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

# Journey: `repair --check` reports without writing

What a gate runs when it wants to know whether an artifact *would* be repaired, without
mutating one under review. Exit `1` means something would change; the file does not.

```console
$ $SOFTSCHEMA repair check/repair-unquoted-colon.md --check
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
$ $SOFTSCHEMA repair check-clean/repair-already-valid.md --check
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
$ $SOFTSCHEMA repair pure/repair-pure.yaml
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

# Journey: an unterminated fence is refused by both commands, in each one's own voice

A document that opens frontmatter and never closes it is what a truncated agent write
leaves behind. It is a frontmatter-md document the reader rejects — not a fenceless
`pure-yaml` artifact whose leading `---` happens to be a YAML document-start marker.

This journey exists because the two readings once diverged: `validate` refused the file
while the repair path detected `pure-yaml`, parsed the whole thing, and reported `valid`.
The producer was told its artifact was fine while its consumer could not open it, which
inverts the premise of repair. Both implementations diverged the same way, so
`cross-impl-diff.sh` stayed clean through it; only a transcript pinning the expected
verdict catches this class of defect.

The two commands still answer differently, and that is the design rather than a
leftover. `validate` is the consuming-side gate: an artifact it cannot open is not a
failing artifact, it is not an artifact, and it says so in one line and exits 2.

This message is softschema's own, not the YAML engine's, so it is asserted in full rather
than elided. Elsewhere in this file `[..]` hides an engine-specific tail because PyYAML
and the `yaml` npm package word a malformed document differently; there is no such excuse
here, and eliding it would leave the journey matching any usage error at all — including
the wrong one this journey exists to catch.

```console
$ $SOFTSCHEMA validate fence/repair-unterminated-fence.md 2>&1
softschema validate: Delimiter `---` for end of frontmatter not found: `fence/repair-unterminated-fence.md`
? 2
```

`repair` refuses it too, and names the same cause — but as a record, at exit 1. An
unreadable document is this command's normal input, and the agent that just wrote the file
needs the diagnosis in a form it can act on. Note `contract_id`: the document declares no
contract legibly, and none is invented for it.

```console
$ cd fence && $SOFTSCHEMA repair repair-unterminated-fence.md --check
{
  "contract": null,
  "contract_id": "",
  "document_metadata": null,
  "outcome": "invalid",
  "path": "repair-unterminated-fence.md",
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
        "message": "Delimiter `---` for end of frontmatter not found: `repair-unterminated-fence.md`"
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

Reporting "the document has no YAML frontmatter" would send an agent looking for a block
that is plainly there, and naming `--contract` would advise a flag that cannot help. The
record does neither.

```console
$ diff original/repair-unterminated-fence.md fence/repair-unterminated-fence.md && echo "byte-identical"
byte-identical
? 0
```

# Journey: a document ending at its closing fence is still repaired

A file whose last byte is the closing `---`, with no trailing newline, is an ordinary
shape for agent-written text. It differs from a well-formed artifact by one byte, and
the repair verdict must not.

It once did. The offset scan behind `split_frontmatter` treated "no newline left" as
"no closing fence", so it reported no region to rewrite and `--repair` skipped an
artifact it could fix — while the reader, which splits into lines and keeps a final
unterminated one, read the same frontmatter without complaint. That is the same
detector-versus-reader disagreement as the journey above, one function over.

```console
$ cd fence && $SOFTSCHEMA repair repair-ends-at-fence.md --check
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
  "path": "repair-ends-at-fence.md",
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

Writing it quotes the scalar and leaves the fence exactly as authored. The last four
bytes are still a newline and the closing `---`, with nothing after it: repair rewrote
the metadata region and did not normalize the file's ending.

```console
$ cd fence && $SOFTSCHEMA repair repair-ends-at-fence.md > /dev/null && tail -c 4 repair-ends-at-fence.md | od -c | head -1
0000000  \n   -   -   -
? 0
```

# Journey: a leading byte order mark is stripped, not read as a fenceless document

`bom/repair-bom.md` is `bom/repair-unquoted-colon.md` with three bytes in front of it:
`EF BB BF`, a UTF-8 byte order mark. It is invisible, it is legal, and ordinary editors
and shell redirections write it, so it arrives on real agent output. The two files must
get the same verdict, and after repair they must be the same file.

They once were not, and the split ran between the two runtimes rather than between two
code paths. TypeScript decodes with `TextDecoder("utf-8")`, whose default
`ignoreBOM: false` means "strip it"; Python's `bytes.decode` kept the mark as a U+FEFF
character. Every fence check in the codebase — `opens_frontmatter_fence`,
`split_frontmatter`, and both readers — asks whether a first line equals `---`, and
`"\ufeff---"` does not. So `npx softschema` read this artifact and `uvx softschema`
called it fenceless, then reported *"missing `--contract` because the document has no
YAML frontmatter"*: a block that is plainly there, and a flag that could not have helped.

That is the same wrong answer as the unterminated-fence journey above, arrived at from
the other side, and it is why the fix belongs in `read_utf8` / `readUtf8` — the one
function both runtimes route every artifact and schema read through — rather than in each
fence comparison.

Unlike that journey, this divergence was one runtime against the other, so
`cross-impl-diff.sh` can see it. It could not before, because nothing in the corpus
carried a BOM. This fixture is what gives it something to compare.

```console
$ cd bom && $SOFTSCHEMA repair repair-bom.md --check
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
  "path": "repair-bom.md",
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

`validate` reaches the same read verdict, which is the property the repair path exists to
share with it. It still refuses this document — the unquoted `: ` is a real parse failure
until repair puts the quotes back — but it refuses it *for that reason*. The regression is
the other message, so that is what the assertion names; the parse failure's own wording is
engine-specific and is not pinned here.

```console
$ cd bom && $SOFTSCHEMA validate repair-bom.md 2>&1 | grep -q "has no YAML frontmatter" && echo "WRONG: called fenceless" || echo "not called fenceless"
not called fenceless
? 0
```

Repairing both twins lands them on identical bytes: the write emits the decoded text, so
the mark does not survive a rewrite in either runtime. A document needing no repair is
never written at all, so a clean BOM artifact keeps its mark — stripping happens on read,
not as a normalization pass over the tree.

```console
$ cd bom && $SOFTSCHEMA repair repair-bom.md > /dev/null && $SOFTSCHEMA repair repair-unquoted-colon.md > /dev/null && diff repair-bom.md repair-unquoted-colon.md && echo "byte-identical"
byte-identical
? 0
```

With the mark gone and the scalar quoted, the consuming-side gate opens on the artifact
that arrived with three extra bytes.

```console
$ cd bom && $SOFTSCHEMA validate repair-bom.md | grep -E '"(outcome|contract_id)"'
  "contract_id": "test.repair:Doc/v1",
  "outcome": "valid",
? 0
```

```console
$ cd bom && head -c 3 repair-bom.md | od -c | head -1
0000000   -   -   -
? 0
```

# Journey: `--dry-run` reports the same change and passes on the verdict

`--dry-run` and `--check` suppress the same write and assert different things.
`--check` fails a document that needed repairing, which is what a gate wants; `--dry-run`
keeps the ordinary pass condition, which is what an agent asking "what would this do?"
wants. The journey above shows this artifact failing `--check` at exit 1; here the same
artifact, unchanged on disk, passes `--dry-run` at exit 0 while reporting the identical
repair.

Shipping only `--check` would leave a caller reaching for it expecting these semantics and
getting a baffling exit 1 on a document that repairs fine.

```console
$ cd dry && $SOFTSCHEMA repair repair-unquoted-colon.md --dry-run
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
  "path": "repair-unquoted-colon.md",
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

It reported the repair without performing it:

```console
$ diff original/repair-unquoted-colon.md dry/repair-unquoted-colon.md && echo "byte-identical"
byte-identical
? 0
```

# Journey: the two write-suppressing flags are mutually exclusive

They suppress the same write and assert different things, so passing both asks two
questions at once. The message is softschema's own and identical in both implementations,
so it is asserted in full: the exclusion is checked by hand rather than with argparse's
mutually exclusive group, whose wording Commander cannot reproduce.

```console
$ $SOFTSCHEMA repair original/repair-already-valid.md --dry-run --check
softschema repair: --dry-run and --check are mutually exclusive
? 2
```
