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

If the Python CLI is installed, load the same material with:

```bash
softschema skill --brief
softschema docs guide
softschema docs spec
softschema docs example
softschema docs example-artifact
```

## Workflow

1. Identify the artifact and the values downstream consumers actually need.
2. Put those values in YAML frontmatter under one envelope key.
3. Add `softschema.contract` with a stable contract ID.
4. Keep the Markdown body readable for context, sources, caveats, and interpretation.
5. Add a Pydantic model or JSON Schema sidecar only when a boundary needs validation.
6. Validate generated artifacts before relying on them.

## When to Add Structure

Promote a value into YAML when code reads it, QA checks it, a later step depends on it,
a rollup aggregates it, or repeated failures would be caught by a type, enum, range, or
cross-field invariant.

Add a source model or JSON Schema sidecar when field names have stabilized across real
artifacts, multiple consumers rely on the same shape, or the boundary needs visible
failure instead of best-effort interpretation.

Keep prose unstructured when it is exploratory, judgment-heavy, or would force false
precision. A useful soft schema can validate only a few consumed values while leaving
most context in readable Markdown.

## Data Placement

- Use inline frontmatter for small payloads that readers can scan.
- Use a YAML data sidecar when structured payloads become large, machine-generated, or
  distracting in frontmatter.
- Keep routing fields, contract ID, counts, digest or generated metadata, and a short
  summary in frontmatter when a data sidecar is used.
- Treat schema sidecars and data sidecars as different things: schema sidecars describe
  validation contracts; data sidecars hold payload values.
- The first Python package supports schema sidecars. Generic data-sidecar loading is a
  host convention, not built-in softschema behavior.

## Rules

- Treat YAML/frontmatter as authoritative.
- Do not parse Markdown tables or prose as structured values. If code needs a value,
  fix the producer to write it into YAML, a declared data sidecar, or pure data.
- Keep exactly one source of truth for each structured value. Body tables may mirror
  YAML for readers, but consumers must read the YAML.
- Prefer contract IDs like `namespace:UpperCamelCaseName/v1`.
- Remember that a contract ID can map to Pydantic, Zod, JSON Schema, or another
  validator.
- Do not harden everything at once. Promote the fields that are actually consumed.
- Keep README content as a short subset of the guide, and put exact format rules in the
  spec.
- Keep examples copyable. Use `softschema docs example-artifact` or the files under
  `examples/` as references; do not scaffold a target project unless the user explicitly
  asks for that workflow.

## Review Checklist

Before finishing a softschema change, check:

1. Every consumed value is in YAML, a declared YAML data sidecar, or pure data.
2. No code parses Markdown body prose or tables for structured fields.
3. The artifact still reads well for humans and agents.
4. The contract ID names the payload shape, not an implementation wrapper.
5. Boundary validation fails visibly for malformed YAML, contract mismatches, or schema
   violations.
6. Any duplicated field lists, enum values, or schema tables are generated or have a
   clear owner.

## Useful Commands

```bash
uv run softschema inspect path/to/artifact.md
uv run softschema validate path/to/artifact.md --model package.module:Model --schema schemas/contract.schema.yaml
uv run softschema compile package.module:Model --contract example:Contract/v1 --out schemas/contract.schema.yaml
uv run softschema docs --list
uv run softschema skill --brief
```

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
