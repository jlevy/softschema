# Development

Set up the repo:

```bash
uv sync --all-extras
```

Common workflows:

```bash
make lint
make lint-check
make test
make build
```

Direct commands:

```bash
uv run python devtools/lint.py --check
uv run pytest
uv run softschema docs --list
uv run softschema docs --list --json
uv run softschema skill --brief
uv build
```

The Python package is built from `packages/python/src/softschema`.

Documentation changes should follow the tbd common documentation guidelines. Keep the
README short, keep conceptual guidance in `docs/softschema-guide.md`, and keep exact
format rules in `docs/softschema-spec.md`.

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
