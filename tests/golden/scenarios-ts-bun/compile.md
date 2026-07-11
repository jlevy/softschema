---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: compile (Zod) --check finds no drift against the committed canonical sidecar

The TypeScript compiler's source is an idiomatic Zod module export (vs Pydantic
`module:Class` on Python). `--check` compares schema *content*, not YAML bytes, so the
Zod KitchenSink matches the committed `examples/parity/parity.schema.yaml` produced from
Pydantic; the same `schema_sha256` proves exact cross-language schema parity. The large
`schema_yaml` string is elided.

```console
$ softschema compile packages/typescript/test/fixtures/parity.ts:KitchenSink --contract example.parity:KitchenSink/v1 --out examples/parity/parity.schema.yaml --check
{
  "drift": false,
  "drift_diff": null,
  "out_path": "examples/parity/parity.schema.yaml",
  "schema_sha256": "48ae00cb32db4bc89771113f8b014c5283b154a801aeff33dc138a43ba7415d5",
  "schema_yaml": [..]
}
? 0
```

# Test: compile --check reports drift for a different contract id

```console
$ softschema compile packages/typescript/test/fixtures/parity.ts:KitchenSink --contract wrong:Sink/v1 --out examples/parity/parity.schema.yaml --check
{
  "drift": true,
  "drift_diff": "committed schema at examples/parity/parity.schema.yaml differs from compile output",
  "out_path": "examples/parity/parity.schema.yaml",
  "schema_sha256": "372ca66737e310617d2190f925fab47aebe0e2c27146209b5e8a5e1aad1afb36",
  "schema_yaml": [..]
}
? 1
```
