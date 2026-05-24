---
name: softschema
description: Use soft schemas to add gradual structure and validation to Markdown/YAML artifacts for human, agent, and code workflows.
---
# Softschema Skill

Use this skill when a project has Markdown or YAML artifacts that humans or agents write
and tools need to consume.

## References

Read these repo docs when available:

- `docs/softschema-guide.md` for the concept, mental model, and adoption path.
- `docs/softschema-spec.md` for the exact language-neutral artifact format.
- `examples/movie_page/README.md` for a complete Python-backed example.

## Workflow

1. Identify the artifact and the values downstream consumers actually need.
2. Put those values in YAML frontmatter under one envelope key.
3. Add `softschema.contract` with a stable contract ID.
4. Keep the Markdown body readable for context, sources, caveats, and interpretation.
5. Add a Pydantic model or JSON Schema sidecar only when a boundary needs validation.
6. Validate generated artifacts before relying on them.

## Rules

- Treat YAML/frontmatter as authoritative.
- Do not parse Markdown tables or prose as structured values.
- Prefer contract IDs like `namespace:UpperCamelCaseName/v1`.
- Remember that a contract ID can map to Pydantic, Zod, JSON Schema, or another
  validator.
- Do not harden everything at once. Promote the fields that are actually consumed.
- Keep README content as a short subset of the guide, and put exact format rules in the
  spec.

## Useful Commands

```bash
uv run softschema inspect path/to/artifact.md
uv run softschema validate path/to/artifact.md --model package.module:Model --schema schemas/contract.schema.yaml
uv run softschema compile package.module:Model --contract example:Contract/v1 --out schemas/contract.schema.yaml
```

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
