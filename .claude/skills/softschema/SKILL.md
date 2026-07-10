---
name: softschema
description: >-
  Validate and structure Markdown/YAML artifacts with typed frontmatter contracts.
  Use when an agent or tool must reliably produce, consume, inspect, or validate
  machine-readable values alongside prose, or when using the softschema CLI.
---
<!-- DO NOT EDIT format=f01: written by `softschema skill --install`.
Re-run that command to update.
-->

# softschema Skill

Use this routing skill for Markdown artifacts that keep consumed values in YAML while
leaving explanations and judgment-heavy context as prose.
Load only the bundled guide, specification, or example needed for the current task.

<!-- BEGIN SOFTSCHEMA BRIEF -->
## Select a Capable Command

Derive the required capabilities before running an operation:

- Schema-only validation needs the operation, `json-schema`, and the artifact format.
- A `.py` model needs the `python` runtime and `pydantic` model loader.
- A built `.js` or `.mjs` model needs `node` or `bun` and the `zod` model loader.
- A direct `.ts` model needs `bun` and the `zod` model loader.

Try these discovery commands in order, skipping a fallback whose ecosystem cannot load
the requested model:

```bash
softschema doctor --json
uvx --from 'softschema==0.2.2' softschema doctor --json
npx --yes softschema@0.2.2 doctor --json
bunx --bun softschema@0.2.2 doctor --json
```

An executable name or version string is not enough.
Accept a candidate only when its JSON reports protocol `1`, the required operation, a
supported artifact format, and the required runtime and model loader.
Reuse that candidate’s entire command prefix by replacing the trailing `doctor --json`
arguments. If none qualifies, stop and report the missing capability plus the exact
runtime (uv/Python, Node, or Bun) the user can install.

For example, only after the local candidate qualifies, validate a self-describing file
with:

```bash
softschema validate doc.md
```

## Operating Rules

- Treat YAML/frontmatter as authoritative for every consumed value.
  Never parse Markdown body prose or tables for structured fields.
- Use `softschema.contract` for the payload contract ID. When authoring a new artifact,
  use a mapping and include the exact quoted `softschema.format: "1"` discriminator.
  An absent format is the legacy grammar, not the package or contract version.
  The block can also declare `schema`, `envelope`, and `status`.
- Put extension metadata only in the format-1 `softschema.extensions` mapping.
  Use a canonical lowercase reverse-DNS or HTTPS namespace for each key.
  Preserve unknown portable values without interpreting them; extensions never authorize
  loading code or changing core validation.
- Promote a value into YAML only when a downstream consumer needs it.
  Keep exploratory or judgment-heavy content as prose.
- Validate self-describing artifacts without override flags.
  Use `--schema` only for an explicit compiled-schema override.
  Use `--model` only with trusted local Pydantic or Zod code because model loading
  executes code.
- Read the bundled `guide` for the mental model, `spec` for exact format rules, and
  `example-artifact` plus `example-schema` for copyable inputs.
  Run the qualifying prefix with `docs --list` to discover every topic.
- Keep examples copyable.
  Do not scaffold, install, or mutate a project unless the user explicitly requests that
  workflow.

<!-- END SOFTSCHEMA BRIEF -->

## Optional Skill Installation

Installation has explicit scope and ownership preflight.
Preview a project install with the qualifying prefix followed by
`skill --install --project --dry-run`; review every target, then repeat without
`--dry-run`. Use `--agent NAME` or `--all-agents` to select additional native targets.
Never infer a global install from the current directory.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
