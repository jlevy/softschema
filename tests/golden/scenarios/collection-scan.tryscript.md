---
cwd: ../../..
env:
  NO_COLOR: "1"
---

# A collection scan reports mixed record outcomes

The records use Markdown, JSON, and pure YAML. The scan follows the explicit
sibling schema, falls back by contract, and reports the unbound record alongside
the completed rejection, a YAML repair, and a scalar conformance.

```console
$ $SOFTSCHEMA scan tests/golden/fixtures/collection --json
{
  "complete": true,
  "contracts": {
    "example:Other/v1": 1,
    "example:Person/v1": 4
  },
  "problems": [
    {
      "code": "schema_unbound",
      "path": "other/stray.yaml"
    },
    {
      "code": "invalid_value",
      "path": "people/bad.json"
    }
  ],
  "schemas": 1,
  "states": {
    "invalid": 1,
    "repaired": 2,
    "unbound": 1,
    "valid": 1
  }
}
? 1
```
