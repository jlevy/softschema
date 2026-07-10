---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: unsafe whole-number schema bounds are rejected identically (ss-wbnm)

The artifact value `9.0e15` is within the portable safe-integer interval, but the
schema bound `1.0e16` is not. Both implementations inspect the mathematical value
before binary64 conversion and reject the compiled schema with the stable
`schema_invalid/value_domain` result.

```console
$ softschema validate tests/golden/fixtures/big-number.md --schema tests/golden/fixtures/big-number.schema.yaml --contract test.numbers:Big/v1 --envelope data
{
  "contract": {
    "envelope_key": "data",
    "id": "test.numbers:Big/v1",
    "model": null,
    "profile": "frontmatter-md",
    "schema_path": "tests/golden/fixtures/big-number.schema.yaml",
    "status": "enforced"
  },
  "contract_id": "test.numbers:Big/v1",
  "document_metadata": {
    "contract": "test.numbers:Big/v1",
    "envelope": null,
    "schema": null,
    "status": "enforced"
  },
  "path": "tests/golden/fixtures/big-number.md",
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
        "kind": "schema_invalid",
        "message": "compiled schema contains a non-portable YAML value",
        "reason": "value_domain",
        "schema_path": "/properties/big/minimum"
      }
    ],
    "ok": false,
    "skipped_reason": null
  },
  "values": {
    "big": 9000000000000000
  },
  "warnings": []
}
? 1
```
