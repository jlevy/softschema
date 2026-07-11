---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: pure YAML metadata-only validation uses the whole remaining mapping

The `softschema` block is metadata and is removed before validation. With no envelope,
the rest of the mapping is the payload. With no model or schema, the validation layers
report their stable skipped reasons.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-metadata-only.yaml --profile pure-yaml
{
  "contract": {
    "envelope_key": null,
    "id": "test.pure:MetadataOnly/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.pure:MetadataOnly/v1",
  "document_metadata": {
    "contract": "test.pure:MetadataOnly/v1",
    "envelope": null,
    "schema": null,
    "status": "soft"
  },
  "path": "tests/golden/fixtures/pure-yaml-metadata-only.yaml",
  "profile": "pure-yaml",
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
    "skipped_reason": "no_schema"
  },
  "values": {
    "count": 2,
    "name": "example"
  },
  "warnings": []
}
? 0
```

# Test: pure YAML without metadata uses the whole mapping

An explicit contract and schema bind a plain YAML mapping that has no `softschema`
block. The profile never requires metadata when the caller supplies the binding.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-no-metadata.yaml --profile pure-yaml --contract test.errors:Sample/v1 --schema tests/golden/fixtures/error-norm.schema.yaml --status enforced
{
  "contract": {
    "envelope_key": null,
    "id": "test.errors:Sample/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": "tests/golden/fixtures/error-norm.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "test.errors:Sample/v1",
  "document_metadata": null,
  "path": "tests/golden/fixtures/pure-yaml-no-metadata.yaml",
  "profile": "pure-yaml",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "title": "Whole mapping payload",
    "year": 2001
  },
  "warnings": []
}
? 0
```

# Test: pure YAML honors a declared envelope

```console
$ softschema validate tests/golden/fixtures/pure-yaml-envelope.yaml --profile pure-yaml
{
  "contract": {
    "envelope_key": "declared",
    "id": "test.errors:Sample/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "enforced"
  },
  "contract_id": "test.errors:Sample/v1",
  "document_metadata": {
    "contract": "test.errors:Sample/v1",
    "envelope": "declared",
    "schema": "error-norm.schema.yaml",
    "status": "enforced"
  },
  "path": "tests/golden/fixtures/pure-yaml-envelope.yaml",
  "profile": "pure-yaml",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "title": "Declared envelope",
    "year": 2001
  },
  "warnings": []
}
? 0
```

# Test: a CLI envelope overrides pure YAML metadata

The explicit `--envelope` flag has higher precedence than
`softschema.envelope`.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-envelope.yaml --profile pure-yaml --envelope override
{
  "contract": {
    "envelope_key": "override",
    "id": "test.errors:Sample/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "enforced"
  },
  "contract_id": "test.errors:Sample/v1",
  "document_metadata": {
    "contract": "test.errors:Sample/v1",
    "envelope": "declared",
    "schema": "error-norm.schema.yaml",
    "status": "enforced"
  },
  "path": "tests/golden/fixtures/pure-yaml-envelope.yaml",
  "profile": "pure-yaml",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "title": "CLI override",
    "year": 2002
  },
  "warnings": []
}
? 0
```

# Test: an explicit contract does not hide a pure YAML contract mismatch

The CLI binding has higher selection precedence, but the document declaration remains
an integrity check. An enforced artifact that declares a different contract is rejected.

```console
$ softschema validate examples/movie_page/spirited-away.yaml --profile pure-yaml --contract wrong:Movie/v1
{
  "contract": {
    "envelope_key": null,
    "id": "wrong:Movie/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "enforced"
  },
  "contract_id": "wrong:Movie/v1",
  "document_metadata": {
    "contract": "example.movies:MoviePage/v1",
    "envelope": null,
    "schema": "movie-page.schema.yaml",
    "status": "enforced"
  },
  "path": "examples/movie_page/spirited-away.yaml",
  "profile": "pure-yaml",
  "semantic": {
    "errors": [],
    "ok": false,
    "skipped_reason": "document_contract_mismatch"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "document_contract_mismatch",
        "message": "document declares 'example.movies:MoviePage/v1'; contract uses 'wrong:Movie/v1'"
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

# Test: a YAML filename never infers the pure YAML profile

The default remains `frontmatter-md`. A `.yaml` file without Markdown frontmatter
therefore needs an explicit `--profile pure-yaml`; the extension alone never changes
the artifact grammar.

```console
$ softschema validate examples/movie_page/spirited-away.yaml 2>&1
softschema validate: missing --contract because the document has no YAML frontmatter
? 2
```

# Test: an unknown profile is a stable usage error

The diagnostic and exit code are identical across Python, Node, and Bun.

```console
$ softschema validate examples/movie_page/spirited-away.yaml --profile yaml 2>&1
softschema validate: invalid profile: yaml
? 2
```

# Test: a non-mapping pure YAML root is a stable parse failure

```console
$ softschema validate tests/golden/fixtures/pure-yaml-list-root.yaml --profile pure-yaml --contract test.pure:Root/v1
{
  "kind": "parse_error",
  "message": "artifact YAML root must be a mapping",
  "reason": "root",
  "source": "tests/golden/fixtures/pure-yaml-list-root.yaml"
}
? 1
```

# Test: a non-portable pure YAML value is a stable parse failure

```console
$ softschema validate tests/golden/fixtures/pure-yaml-value-domain.yaml --profile pure-yaml
{
  "kind": "parse_error",
  "message": "artifact contains a non-portable YAML value",
  "path": "/value",
  "reason": "value_domain",
  "source": "tests/golden/fixtures/pure-yaml-value-domain.yaml"
}
? 1
```

# Test: a coded YAML parser exception is a parse failure

Some YAML parsers attach a string `code` to syntax exceptions. That metadata must not
make a readable document look like a filesystem input failure.

```console
$ softschema validate tests/golden/fixtures/pure-yaml-coded-parser-error.yaml --profile pure-yaml --contract test.pure:Root/v1
{
  "kind": "parse_error",
  "message": "artifact is not valid YAML",
  "reason": "syntax",
  "source": "tests/golden/fixtures/pure-yaml-coded-parser-error.yaml"
}
? 1
```
