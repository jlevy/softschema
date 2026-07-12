---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: large whole-number float renders canonically and identically (ss-wbnm)

A whole-valued float above 2^53 but below 1e21 renders as a plain integer on both
engines: the value `9.0e15` and the bound `1.0e16` appear as `9000000000000000` and
`10000000000000000` in the `value`, `validator_value`, and synthesized message, with no
trailing fraction and no exponent. This is the reviewer's regression case for the
canonical-number contract; before the 1e16→1e21 threshold fix Python emitted `1e+16` in
`validator_value` while TypeScript emitted the full integer.

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
  "outcome": "invalid",
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
        "kind": "schema_violation",
        "message": "value 9000000000000000 is less than the minimum of 10000000000000000",
        "path": [
          "big"
        ],
        "validator": "minimum",
        "validator_value": 10000000000000000,
        "value": 9000000000000000
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
