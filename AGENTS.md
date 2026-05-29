# Agent Instructions

This repo teaches and implements the soft schema pattern.

Start here:

- [Softschema Guide](docs/softschema-guide.md): standalone concept and adoption guide
  for humans and agents.
- [Softschema Spec](docs/softschema-spec.md): exact language-neutral artifact format.
- [Movie page example](examples/movie_page/README.md): complete Python-backed example.

For implementer reference (only when changing the Python package itself):

- [Python Package Design](docs/softschema-python-design.md): module layout, CLI surface,
  validation layers, and ADR-style decisions.
  Skip when only authoring or validating artifacts.

Key rules:

- Treat YAML/frontmatter as the authoritative structured data.
- Do not parse Markdown body prose or tables for consumed values.
- Use `softschema.contract`, not `schema`, in authored artifact metadata.
- Contract IDs name artifact payload contracts, not a specific Python class.
- Keep examples public and practical; do not introduce private business context,
  internal project names, or proprietary domains.
- Use `uv` for Python workflows.

Common commands:

```bash
uv sync --all-extras
uv run python devtools/lint.py --check
uv run pytest
uv build
uv run softschema docs --list
uv run softschema docs --list --json
uv run softschema skill --brief
```

When adding a schema, start by identifying the values downstream consumers actually
need. Promote those values into YAML, validate them at the boundary, and leave the rest
as readable Markdown unless it is truly consumed as data.

Documentation rules:

- Follow `common-doc-guidelines.md` (github.com/jlevy/practical-prose): clear structure,
  concise language, present-state descriptions, and enough context for a low-context
  reader.
- Keep the README as a short subset of `docs/softschema-guide.md`.
- Put exact artifact-format rules in `docs/softschema-spec.md`.
- Keep examples as copyable source files under `examples/`; the CLI may print them, but
  should not scaffold or mutate projects in the first release.
- Include the standard documentation footer in repo docs.
  Do not add it to authored softschema example artifacts.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
