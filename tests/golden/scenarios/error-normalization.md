---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: structural error normalization across every keyword

The movie fixture only exercises `minItems`, `minimum`, and `exclusiveMinimum`.
This scenario covers the keywords whose ajv-vs-`jsonschema` normalization diverged
before the parity fixes (epic `ss-jgkf`): missing `required` keys, `multipleOf`,
`type`, `enum`, and `additionalProperties`. Both implementations must emit the same
engine-neutral records, including:

- `required` reports the **full required list** as `validator_value`, once per missing
  key (matching `jsonschema`).
- `additionalProperties` collapses to **one** record per object (ajv reports one per
  extra key; `jsonschema` reports one).
- `multipleOf` carries the divisor as `validator_value` (regression guard for the
  `params.limit` bug that rendered "multiple of None").

The fixture deliberately avoids whole-number floats, whose `2.0`-vs-`2` rendering is a
known, documented JS limitation (`ss-wbnm`) rather than a fixable divergence.

```console
$ softschema validate tests/golden/fixtures/bad-error-norm.md --schema tests/golden/fixtures/error-norm.schema.yaml --contract test.errors:Sample/v1 --envelope data
{
  "contract": {
    "envelope_key": "data",
    "id": "test.errors:Sample/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/error-norm.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "test.errors:Sample/v1",
  "document_metadata": {
    "contract": "test.errors:Sample/v1",
    "status": "enforced"
  },
  "path": "tests/golden/fixtures/bad-error-norm.md",
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
          "count": "x",
          "extra1": 1,
          "extra2": 2,
          "rating": "X",
          "scale": 0.3,
          "step": 7,
          "tags": [
            "a"
          ]
        }
      },
      {
        "kind": "schema_violation",
        "message": "required property ['title', 'year'] is missing",
        "path": [],
        "validator": "required",
        "validator_value": [
          "title",
          "year"
        ],
        "value": {
          "count": "x",
          "extra1": 1,
          "extra2": 2,
          "rating": "X",
          "scale": 0.3,
          "step": 7,
          "tags": [
            "a"
          ]
        }
      },
      {
        "kind": "schema_violation",
        "message": "required property ['title', 'year'] is missing",
        "path": [],
        "validator": "required",
        "validator_value": [
          "title",
          "year"
        ],
        "value": {
          "count": "x",
          "extra1": 1,
          "extra2": 2,
          "rating": "X",
          "scale": 0.3,
          "step": 7,
          "tags": [
            "a"
          ]
        }
      },
      {
        "kind": "schema_violation",
        "message": "value 'x' is not of type 'integer'",
        "path": [
          "count"
        ],
        "validator": "type",
        "validator_value": "integer",
        "value": "x"
      },
      {
        "kind": "schema_violation",
        "message": "value 'X' is not one of ['G', 'PG', 'R']",
        "path": [
          "rating"
        ],
        "validator": "enum",
        "validator_value": [
          "G",
          "PG",
          "R"
        ],
        "value": "X"
      },
      {
        "kind": "schema_violation",
        "message": "value 0.3 is not a multiple of 0.5",
        "path": [
          "scale"
        ],
        "validator": "multipleOf",
        "validator_value": 0.5,
        "value": 0.3
      },
      {
        "kind": "schema_violation",
        "message": "value 7 is not a multiple of 5",
        "path": [
          "step"
        ],
        "validator": "multipleOf",
        "validator_value": 5,
        "value": 7
      },
      {
        "kind": "schema_violation",
        "message": "array is shorter than the minimum of 2 items",
        "path": [
          "tags"
        ],
        "validator": "minItems",
        "validator_value": 2,
        "value": [
          "a"
        ]
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "count": "x",
    "extra1": 1,
    "extra2": 2,
    "rating": "X",
    "scale": 0.3,
    "step": 7,
    "tags": [
      "a"
    ]
  },
  "warnings": []
}
? 1
```
