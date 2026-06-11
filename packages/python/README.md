# softschema Python Package

The Python package provides:

- `Contract` and `Contracts`
- `validate_artifact` for Markdown/YAML artifact validation
- `validate_structural` for JSON Schema validation
- `validate_semantic` for Pydantic validation
- `compile_model` for Pydantic-to-JSON-Schema compilation
- the `softschema` CLI, including bundled docs through `softschema docs` and
  `softschema skill`

The package source lives under `packages/python/src/softschema`, but the root
`pyproject.toml` owns builds and dependency management.

Use the root [softschema Guide](../../docs/softschema-guide.md) for the concept and
[softschema Spec](../../docs/softschema-spec.md) for the artifact format.

Installed environments can print the same reference material:

```bash
softschema docs --list
softschema docs --list --json
softschema docs guide
softschema docs example-artifact
softschema skill --brief
```

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
