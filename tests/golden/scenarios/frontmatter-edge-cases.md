---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: empty frontmatter is reported as no_frontmatter

An empty frontmatter block (`---\n---`) contains no YAML metadata. Python's
`fmf_read` returns `None` (no metadata), which `validate_artifact` reports as
`no_frontmatter`. The TypeScript implementation must match: the closing fence at
line 1 (zero content lines) is treated as absent frontmatter, not as an empty
mapping.

```console
$ softschema validate tests/golden/fixtures/empty-frontmatter.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data
{
  "contract": {
    "envelope_key": "data",
    "id": "test.errors:Sample/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/error-norm.schema.yaml",
    "status": "soft"
  },
  "contract_id": "test.errors:Sample/v1",
  "document_metadata": null,
  "path": "tests/golden/fixtures/empty-frontmatter.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": false,
    "skipped_reason": "no_frontmatter"
  },
  "status": "soft",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "no_frontmatter",
        "message": "no frontmatter in tests/golden/fixtures/empty-frontmatter.md"
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

# Test: whitespace-only frontmatter is a parse error (exit 2)

A frontmatter block with only whitespace parses as `null` YAML. Python's
`fmf_read` raises `FmFormatError`, surfaced by the CLI as exit 2 with a
diagnostic on stderr. The TS CLI wraps the error differently (extra prefix), so
only the stable `softschema validate:` prefix is asserted.

```console
$ softschema validate tests/golden/fixtures/whitespace-frontmatter.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data 2>&1
softschema validate: [..]
? 2
```

# Test: non-mapping frontmatter is a parse error on validate (exit 2)

A frontmatter block that parses to a YAML list (or any non-mapping value) is rejected
by frontmatter-format's `fmf_read`. The TS implementation must match: `readFrontmatter`
rejects a non-mapping document the same way, so both CLIs exit 2 instead of treating list
indices as keys. The TS CLI wraps the message differently, so only the stable prefix is
asserted.

```console
$ softschema validate tests/golden/fixtures/list-frontmatter.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data 2>&1
softschema validate: [..]
? 2
```

# Test: non-mapping frontmatter is a parse error on inspect (exit 2)

The same non-mapping frontmatter is rejected by `inspect`, not reported with numeric
list-index envelope keys. Both CLIs exit 2; the message wording differs, so only the
stable prefix is asserted.

```console
$ softschema inspect tests/golden/fixtures/list-frontmatter.md 2>&1
softschema inspect: [..]
? 2
```

# Test: unterminated frontmatter fence is a parse error (exit 2)

A file that opens a `---` frontmatter fence but never closes it is a format
error. Python's `fmf_read` raises `FmFormatError`; the CLI reports exit 2. The
error text differs between implementations, so only the prefix and exit code are
asserted.

```console
$ softschema validate tests/golden/fixtures/unterminated-fence.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data 2>&1
softschema validate: [..]
? 2
```
