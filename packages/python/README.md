# softschema (Python/Pydantic)

The Python implementation of [softschema](https://github.com/jlevy/softschema) validates
Markdown/frontmatter and pure YAML artifacts against portable JSON Schema and optional
trusted Pydantic models.
The npm TypeScript/Zod package implements the same artifact, CLI, compiled-schema, and
result contracts with idiomatic TypeScript APIs.

This package README follows the artifact version built for PyPI. Repository-wide
quickstarts and agent bootstrap stay on the last dual-registry-verified release instead.

## Install

<!-- BEGIN SOFTSCHEMA CLAIM python-version -->
```bash
uv add softschema==0.2.2
# or: python -m pip install 'softschema==0.2.2'
```
<!-- END SOFTSCHEMA CLAIM python-version -->

Read [Security](https://github.com/jlevy/softschema/blob/main/SECURITY.md) before
validating hostile input with this version.

## Validate an Artifact

Library callers supply a host-owned contract; CLI binding inference is a separate
adapter:

```python
from pathlib import Path

from softschema import Contract, Contracts, SchemaStatus
from softschema.runtime import validate_artifact

contract_id = "example.movies:MoviePage/v1"
registry = Contracts()
registry.register(
    Contract(
        id=contract_id,
        model=MoviePage,
        envelope_key="movie",
        status=SchemaStatus.enforced,
        schema_path=Path("movie-page.schema.yaml"),
    )
)
result = validate_artifact(Path("doc.md"), contract_id=contract_id, registry=registry)
```

The package root keeps existing imports available.
New code may use `softschema.core` for runtime-neutral JSON-compatible behavior and
`softschema.runtime` for YAML, filesystem, Pydantic, and compiled-schema adapters.

## CLI

```bash
softschema validate doc.md
softschema validate doc.yaml --profile pure-yaml
softschema validate docs --recursive --format jsonl
softschema doctor --json
softschema docs --list --json
```

`frontmatter-md` is the default; a filename suffix never selects `pure-yaml`. `--model`
imports and executes trusted local Python code.
Compiled-schema validation is offline and performs no implicit HTTP, file, or
relative-resource retrieval.

## Documentation

- [Guide](https://github.com/jlevy/softschema/blob/main/docs/softschema-guide.md):
  adoption and workflows
- [Spec](https://github.com/jlevy/softschema/blob/main/docs/softschema-spec.md): exact
  language-neutral behavior
- [Library API](https://github.com/jlevy/softschema/blob/main/docs/api.md): paired
  Python and TypeScript entrypoints
- [Python Design](https://github.com/jlevy/softschema/blob/main/docs/softschema-python-design.md):
  implementation decisions
- [0.3 Migration](https://github.com/jlevy/softschema/blob/main/docs/migration-0.3.md):
  compatibility changes

The installed CLI exposes bundled public topics through `softschema docs --list`.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
