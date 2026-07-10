# Agent Instructions

This repo teaches and implements the soft schema pattern.

Start here:

- [softschema Guide](docs/softschema-guide.md): standalone concept and adoption guide
  for humans and agents.
- [softschema Spec](docs/softschema-spec.md): exact language-neutral artifact format.
- [Movie Page Example](examples/movie_page/README.md): complete Python-backed example.

softschema ships two interchangeable implementations with the same CLI and library
surface: Python/Pydantic (`softschema`, `softschema-py`) and TypeScript/Zod
(`softschema`, `softschema-ts`). They are held to exact behavioral parity: same flags,
same canonical compiled JSON Schema, same validation results, so authoring an artifact
is identical regardless of which you run.

For implementer reference (only when changing a package itself):

- [Python Package Design](docs/softschema-python-design.md): module layout, CLI surface,
  validation layers, and ADR-style decisions.
- [TypeScript Package Design](docs/softschema-typescript-design.md): the Zod port and
  the Python↔TypeScript API parity table.
- When changing behavior, follow the parity development process (golden-first, then port
  to both) in [docs/development.md](docs/development.md).
  Skip all of this when only authoring or validating artifacts.

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
uv sync --all-extras --no-install-project
uv pip install --no-build-isolation --no-deps --editable .
uv run python devtools/lint.py --check
uv run pytest
uv build --build-constraint build-constraints.txt --require-hashes
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

<!-- BEGIN TBD INTEGRATION format=f06 surface=agents-md -->
## tbd

This repository uses **tbd** for git-native issue tracking (beads), spec-driven
planning, and on-demand engineering guidelines.
As the agent, you operate tbd on the user’s behalf: translate their requests into tbd
actions rather than telling them to run commands.

- Run `tbd prime` to load current project state and the full tbd workflow.
- Run `tbd skill` for the complete reusable tbd skill instructions.
- Run `tbd shortcut --list` and `tbd guidelines --list` for on-demand resources.
- Track all work as beads: `tbd create`, `tbd ready`, `tbd close`, and `tbd sync`.

<!-- END TBD INTEGRATION -->

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
