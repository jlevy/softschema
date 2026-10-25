---
cwd: ../../..
env:
  NO_COLOR: "1"
---

# Test: compile (Zod) --check finds no drift against the committed canonical sidecar

The TypeScript compiler's source is an idiomatic Zod module export (vs Pydantic
`module:Class` on Python). `--check` compares schema *content*, not YAML bytes, so the
Zod KitchenSink matches the committed `examples/parity/parity.schema.yaml` produced from
Pydantic; the same `schema_sha256` proves exact cross-language schema parity. The large
`schema_yaml` string is elided.

```console
$ $SOFTSCHEMA compile packages/typescript/test/fixtures/parity.ts:KitchenSink --contract example.parity:KitchenSink/v1 --out examples/parity/parity.schema.yaml --check
{
  "drift": false,
  "drift_diff": null,
  "out_path": "examples/parity/parity.schema.yaml",
  "schema_sha256": "eb42fd756915b663235574b8becc406b19c3dfea2f1fd49d2a6712c76dcb2c7e",
  "schema_yaml": [..]
}
? 0
```

# Test: compile --check reports drift for a different contract id

```console
$ $SOFTSCHEMA compile packages/typescript/test/fixtures/parity.ts:KitchenSink --contract wrong:Sink/v1 --out examples/parity/parity.schema.yaml --check
{
  "drift": true,
  "drift_diff": "committed schema at examples/parity/parity.schema.yaml differs from compile output",
  "out_path": "examples/parity/parity.schema.yaml",
  "schema_sha256": "2acd8f866e4aa272351d4bac705d18e5e732a2e0df48bd089d5342a8df5f3cd4",
  "schema_yaml": [..]
}
? 1
```

# Test: compile refuses a --schema-id that validation would refuse (exit 2)

The same refusals and messages as the Python compiler: `--schema-id` becomes the root
`$id`, so a `urn:` without a namespace identifier, a relative id, and a malformed host
exit 2.

```console
$ $SOFTSCHEMA compile packages/typescript/test/fixtures/parity.ts:KitchenSink --contract example.parity:KitchenSink/v1 --out examples/parity/parity.schema.yaml --check --schema-id urn:example
! softschema compile: the root $id must name a lowercase namespace identifier and a name, as in urn:example:name, got "urn:example"
? 2
```

```console
$ $SOFTSCHEMA compile packages/typescript/test/fixtures/parity.ts:KitchenSink --contract example.parity:KitchenSink/v1 --out examples/parity/parity.schema.yaml --check --schema-id schemas/movie.json
! softschema compile: the root $id must be an absolute URI, got "schemas/movie.json"
? 2
```

```console
$ $SOFTSCHEMA compile packages/typescript/test/fixtures/parity.ts:KitchenSink --contract example.parity:KitchenSink/v1 --out examples/parity/parity.schema.yaml --check --schema-id 'http://[::1'
! softschema compile: the root $id must have a lowercase host name or a canonical IP address, an optional non-default port, and no user information, got "http://[::1"
? 2
```
