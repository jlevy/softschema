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
    "envelope": null,
    "schema": null,
    "status": "permissive"
  },
  "outcome": "valid",
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
    "envelope": null,
    "schema": null,
    "status": "permissive"
  },
  "outcome": "invalid",
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
        "code": "undeclared_property",
        "kind": "schema_violation",
        "message": "property 'confidence' is not allowed",
        "path": [],
        "property": "confidence",
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
        "code": "undeclared_property",
        "kind": "schema_violation",
        "message": "property 'fetched_by' is not allowed",
        "path": [
          "meta"
        ],
        "property": "fetched_by",
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
    "envelope": null,
    "schema": null,
    "status": "enforced"
  },
  "outcome": "invalid",
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
        "code": "undeclared_property",
        "kind": "schema_violation",
        "message": "property 'confidence' is not allowed",
        "path": [],
        "property": "confidence",
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
        "code": "undeclared_property",
        "kind": "schema_violation",
        "message": "property 'fetched_by' is not allowed",
        "path": [
          "meta"
        ],
        "property": "fetched_by",
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

# Test: enforced validates a composed schema instead of refusing it

The schema from issue #41: a closed object plus one `if`/`then` rule inside `allOf`.
Composition used to make every document `invalid` with a single
`enforcement_unsupported` record, valid or not. Now `kind: plain` does not trigger the
conditional, and the document passes.

```console
$ softschema validate tests/golden/fixtures/conditional-ok.md --schema tests/golden/fixtures/conditional.schema.yaml
{
  "contract": {
    "envelope_key": "thing",
    "id": "demo:Thing/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/conditional.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "demo:Thing/v1",
  "document_metadata": {
    "contract": "demo:Thing/v1",
    "envelope": null,
    "schema": null,
    "status": "enforced"
  },
  "outcome": "valid",
  "path": "tests/golden/fixtures/conditional-ok.md",
  "profile": "frontmatter-md",
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
    "kind": "plain"
  },
  "warnings": []
}
? 0
```

# Test: enforced reports the conditional's real violation

The same schema with `kind: special`, which fires the conditional and requires `extra`.
The error names the missing property — the actionable one — rather than a generic
message about `allOf`.

```console
$ softschema validate tests/golden/fixtures/conditional-violation.md --schema tests/golden/fixtures/conditional.schema.yaml
{
  "contract": {
    "envelope_key": "thing",
    "id": "demo:Thing/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/conditional.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "demo:Thing/v1",
  "document_metadata": {
    "contract": "demo:Thing/v1",
    "envelope": null,
    "schema": null,
    "status": "enforced"
  },
  "outcome": "invalid",
  "path": "tests/golden/fixtures/conditional-violation.md",
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
        "code": "missing_property",
        "kind": "schema_violation",
        "message": "required property 'extra' is missing",
        "path": [],
        "property": "extra",
        "validator": "required",
        "validator_value": [
          "extra"
        ],
        "value": {
          "kind": "special"
        }
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "kind": "special"
  },
  "warnings": []
}
? 1
```

# Test: enforced still rejects an undeclared key on a composed schema

Closure is not lost by supporting composition: `bogus` is declared nowhere, so it is
rejected. Both this and a simple schema's undeclared key report
`code: undeclared_property`, which is the stable surface to match on.

```console
$ softschema validate tests/golden/fixtures/conditional-undeclared.md --schema tests/golden/fixtures/conditional.schema.yaml
{
  "contract": {
    "envelope_key": "thing",
    "id": "demo:Thing/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/conditional.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "demo:Thing/v1",
  "document_metadata": {
    "contract": "demo:Thing/v1",
    "envelope": null,
    "schema": null,
    "status": "enforced"
  },
  "outcome": "invalid",
  "path": "tests/golden/fixtures/conditional-undeclared.md",
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
        "code": "undeclared_property",
        "kind": "schema_violation",
        "message": "property 'bogus' is not allowed",
        "path": [],
        "property": "bogus",
        "validator": "additionalProperties",
        "validator_value": false,
        "value": {
          "bogus": 1,
          "kind": "plain"
        }
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "bogus": 1,
    "kind": "plain"
  },
  "warnings": []
}
? 1
```

# Test: enforced injects unevaluatedProperties when the schema itself is silent

Every property is declared inside an `allOf` branch and the schema says nothing about
closure, so the overlay must inject the annotation-aware keyword. The other enforced
fixtures carry an explicit `additionalProperties`, which wins and hides this path.

```console
$ softschema validate tests/golden/fixtures/composed-open-ok.md --schema tests/golden/fixtures/composed-open.schema.yaml
{
  "contract": {
    "envelope_key": "composed",
    "id": "demo:Composed/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/composed-open.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "demo:Composed/v1",
  "document_metadata": {
    "contract": "demo:Composed/v1",
    "envelope": null,
    "schema": null,
    "status": "enforced"
  },
  "outcome": "valid",
  "path": "tests/golden/fixtures/composed-open-ok.md",
  "profile": "frontmatter-md",
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
    "first": "Ada",
    "last": "Lovelace"
  },
  "warnings": []
}
? 0
```

# Test: injected closure preserves each undeclared key

Two undeclared keys against the same object produce two normalized records. Native
jsonschema groups the keys while ajv reports them separately; normalization preserves
one record per field in both runtimes.

```console
$ softschema validate tests/golden/fixtures/composed-open-undeclared.md --schema tests/golden/fixtures/composed-open.schema.yaml
{
  "contract": {
    "envelope_key": "composed",
    "id": "demo:Composed/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/composed-open.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "demo:Composed/v1",
  "document_metadata": {
    "contract": "demo:Composed/v1",
    "envelope": null,
    "schema": null,
    "status": "enforced"
  },
  "outcome": "invalid",
  "path": "tests/golden/fixtures/composed-open-undeclared.md",
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
        "code": "undeclared_property",
        "kind": "schema_violation",
        "message": "property 'bogus' is not allowed",
        "path": [],
        "property": "bogus",
        "validator": "unevaluatedProperties",
        "validator_value": false,
        "value": {
          "bogus": 1,
          "first": "Ada",
          "last": "Lovelace",
          "other": 2
        }
      },
      {
        "code": "undeclared_property",
        "kind": "schema_violation",
        "message": "property 'other' is not allowed",
        "path": [],
        "property": "other",
        "validator": "unevaluatedProperties",
        "validator_value": false,
        "value": {
          "bogus": 1,
          "first": "Ada",
          "last": "Lovelace",
          "other": 2
        }
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "bogus": 1,
    "first": "Ada",
    "last": "Lovelace",
    "other": 2
  },
  "warnings": []
}
? 1
```
