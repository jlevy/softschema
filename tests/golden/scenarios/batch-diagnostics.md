---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: recursive no-match is an exact diagnostic-v1 aggregate

The tracked directory has no frontmatter Markdown candidate. Batch discovery fails
closed with a portable no-match input result instead of reporting a false green run.

```console
$ softschema validate tests/golden/fixtures/batch-no-match --recursive
{
  "format": "diagnostic-v1",
  "limits": {
    "max_bundle_bytes": 67108864,
    "max_depth": 128,
    "max_nodes_per_resource": 100000,
    "max_resource_bytes": 8388608,
    "max_resources": 256,
    "max_scalar_codepoints": 1048576
  },
  "ok": false,
  "profile": "frontmatter-md",
  "results": [
    {
      "diagnostics": [
        {
          "category": "input",
          "message": "artifact directory contains no matching files",
          "rule_id": "softschema.input_error.no_matches",
          "severity": "error",
          "source": "tests/golden/fixtures/batch-no-match"
        }
      ],
      "input": {
        "kind": "input_error",
        "message": "artifact directory contains no matching files",
        "reason": "no_matches",
        "source": "tests/golden/fixtures/batch-no-match"
      },
      "outcome": "input_failed",
      "validation": null
    }
  ],
  "summary": {
    "exit_code": 2,
    "input_failed": 1,
    "passed": 0,
    "total": 1,
    "validation_failed": 0
  }
}
? 2
```

# Test: legacy single-file JSON uses portable key and number spelling

This ordinary compatibility-mode result covers integer-like keys, BMP and astral keys,
nested Unicode keys, and the shared small-exponent spelling.

```console
$ softschema validate tests/golden/fixtures/serialization-edge.yaml --profile pure-yaml
{
  "contract": {
    "envelope_key": null,
    "id": "test.serialization:Record/v1",
    "model": null,
    "profile": "pure-yaml",
    "schema_path": null,
    "status": "soft"
  },
  "contract_id": "test.serialization:Record/v1",
  "document_metadata": {
    "contract": "test.serialization:Record/v1",
    "envelope": null,
    "schema": null,
    "status": null
  },
  "path": "tests/golden/fixtures/serialization-edge.yaml",
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
    "10": "ten",
    "2": "two",
    "nested": {
      "10": "ten",
      "2": "two",
      "é": "accent",
      "😀": "face"
    },
    "small": 1e-07,
    "": "bmp",
    "𐀀": "astral"
  },
  "warnings": []
}
```
