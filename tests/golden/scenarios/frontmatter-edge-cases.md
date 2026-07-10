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

# Test: whitespace-only frontmatter is a root parse error (exit 1)

A frontmatter block with only whitespace parses as a null root. Both implementations
emit the stable `parse_error/root` record because the readable artifact root is not a
mapping.

```console
$ softschema validate tests/golden/fixtures/whitespace-frontmatter.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data 2>&1
{
  "kind": "parse_error",
  "message": "artifact YAML root must be a mapping",
  "reason": "root",
  "source": "tests/golden/fixtures/whitespace-frontmatter.md"
}
? 1
```

# Test: non-mapping frontmatter is a root parse error on validate (exit 1)

A frontmatter block that parses to a YAML list (or any non-mapping value) is a readable
artifact failure. Both CLIs emit the same `parse_error/root` record instead of treating
list indices as keys.

```console
$ softschema validate tests/golden/fixtures/list-frontmatter.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data 2>&1
{
  "kind": "parse_error",
  "message": "artifact YAML root must be a mapping",
  "reason": "root",
  "source": "tests/golden/fixtures/list-frontmatter.md"
}
? 1
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

# Test: unterminated frontmatter fence is a format parse error (exit 1)

A file that opens a `---` frontmatter fence but never closes it emits the stable
`parse_error/frontmatter` record.

```console
$ softschema validate tests/golden/fixtures/unterminated-fence.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data 2>&1
{
  "kind": "parse_error",
  "message": "artifact frontmatter delimiters are malformed",
  "reason": "frontmatter",
  "source": "tests/golden/fixtures/unterminated-fence.md"
}
? 1
```
