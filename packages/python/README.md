# softschema Python Package

The Python package provides:

- `SchemaBinding` and `SchemaRegistry`
- `validate_artifact` for Markdown/YAML artifact validation
- `validate_structural` for JSON Schema validation
- `validate_semantic` for Pydantic validation
- `compile_model` for Pydantic-to-JSON-Schema sidecars
- the `softschema` CLI

The package source lives under `packages/python/src/softschema`, but the root
`pyproject.toml` owns builds and dependency management.

Use the root [Softschema Guide](../../docs/softschema-guide.md) for the concept and
[Softschema Spec](../../docs/softschema-spec.md) for the artifact format.

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
