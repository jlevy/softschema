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
  "schema_sha256": "6810f0d889ded6f23e4a4f752070928d87b439ae328ae02187b9dfb467b76519",
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
  "schema_sha256": "1deeba6bb029b03492b2a4b58772ce8b3053a343bb89db033cbcbf7edd78d0ab",
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
