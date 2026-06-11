---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: status permissive leaves undeclared fields alone

The lenient schema declares `name` and `meta.source` and says nothing about
`additionalProperties`. Under `permissive`, the extension fields (`confidence`,
`meta.fetched_by`) pass.

```console
$ softschema validate tests/golden/fixtures/extra-field-permissive.md --schema tests/golden/fixtures/lenient.schema.yaml
{
  "contract": {
    "envelope_key": "record",
    "id": "test.enforced:Record/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/lenient.schema.yaml",
    "status": "permissive"
  },
  "contract_id": "test.enforced:Record/v1",
  "document_metadata": {
    "contract": "test.enforced:Record/v1",
    "status": "permissive"
  },
  "path": "tests/golden/fixtures/extra-field-permissive.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "permissive",
  "structural": {
    "engine": "json_schema",
    "errors": [],
    "ok": true,
    "skipped_reason": null
  },
  "values": {
    "confidence": "high",
    "meta": {
      "fetched_by": "agent",
      "source": "web"
    },
    "name": "Acme"
  },
  "warnings": []
}
? 0
```

# Test: --status enforced applies the strict-extras overlay

The SAME document and schema under `--status enforced`: object schemas that declare
`properties` but omit `additionalProperties` are validated as closed, so both the root
extension field and the nested one fail, and the status override also emits the
document-status-mismatch warning. Enabling strictness enforces it; the schema itself
is unchanged.

```console
$ softschema validate tests/golden/fixtures/extra-field-permissive.md --schema tests/golden/fixtures/lenient.schema.yaml --status enforced
{
  "contract": {
    "envelope_key": "record",
    "id": "test.enforced:Record/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/lenient.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "test.enforced:Record/v1",
  "document_metadata": {
    "contract": "test.enforced:Record/v1",
    "status": "permissive"
  },
  "path": "tests/golden/fixtures/extra-field-permissive.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "schema_violation",
        "message": "object has properties that are not allowed",
        "path": [],
        "validator": "additionalProperties",
        "validator_value": false,
        "value": {
          "confidence": "high",
          "meta": {
            "fetched_by": "agent",
            "source": "web"
          },
          "name": "Acme"
        }
      },
      {
        "kind": "schema_violation",
        "message": "object has properties that are not allowed",
        "path": [
          "meta"
        ],
        "validator": "additionalProperties",
        "validator_value": false,
        "value": {
          "fetched_by": "agent",
          "source": "web"
        }
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "confidence": "high",
    "meta": {
      "fetched_by": "agent",
      "source": "web"
    },
    "name": "Acme"
  },
  "warnings": [
    {
      "code": "document-status-mismatch",
      "message": "document declares status 'permissive'; contract uses 'enforced'",
      "severity": "warning"
    }
  ]
}
? 1
```

# Test: a document-declared enforced status is self-describing

The same payload whose own metadata says `status: enforced` is rejected with no
flags at all.

```console
$ softschema validate tests/golden/fixtures/extra-field-enforced.md --schema tests/golden/fixtures/lenient.schema.yaml
{
  "contract": {
    "envelope_key": "record",
    "id": "test.enforced:Record/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/lenient.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "test.enforced:Record/v1",
  "document_metadata": {
    "contract": "test.enforced:Record/v1",
    "status": "enforced"
  },
  "path": "tests/golden/fixtures/extra-field-enforced.md",
  "profile": "frontmatter-md",
  "semantic": {
    "errors": [],
    "ok": true,
    "skipped_reason": "no_semantic_model"
  },
  "status": "enforced",
  "structural": {
    "engine": "json_schema",
    "errors": [
      {
        "kind": "schema_violation",
        "message": "object has properties that are not allowed",
        "path": [],
        "validator": "additionalProperties",
        "validator_value": false,
        "value": {
          "confidence": "high",
          "meta": {
            "fetched_by": "agent",
            "source": "web"
          },
          "name": "Acme"
        }
      },
      {
        "kind": "schema_violation",
        "message": "object has properties that are not allowed",
        "path": [
          "meta"
        ],
        "validator": "additionalProperties",
        "validator_value": false,
        "value": {
          "fetched_by": "agent",
          "source": "web"
        }
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "confidence": "high",
    "meta": {
      "fetched_by": "agent",
      "source": "web"
    },
    "name": "Acme"
  },
  "warnings": []
}
? 1
```
