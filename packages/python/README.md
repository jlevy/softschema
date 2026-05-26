# softschema Python Package

The Python package provides:

- `SoftschemaBinding` and `SoftschemaRegistry`
- `validate_artifact` for Markdown/YAML artifact validation
- `validate_structural` for JSON Schema validation
- `validate_semantic` for Pydantic validation
- `compile_model` for Pydantic-to-JSON-Schema sidecars
- the `softschema` CLI, including bundled docs through `softschema docs` and
  `softschema skill`

The package source lives under `packages/python/src/softschema`, but the root
`pyproject.toml` owns builds and dependency management.

Use the root [Softschema Guide](../../docs/softschema-guide.md) for the concept and
[Softschema Spec](../../docs/softschema-spec.md) for the artifact format.

Installed environments can print the same reference material:

```bash
softschema docs --list
softschema docs --list --json
softschema docs guide
softschema docs example-artifact
softschema skill --brief
```

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
