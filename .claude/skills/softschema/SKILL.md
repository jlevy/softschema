---
name: softschema
description: >-
  Validate and structure Markdown/YAML artifacts with frontmatter contracts.
  Mix prose context with machine-readable values without forcing the whole
  document into a hard schema. Use when working with soft schemas, frontmatter
  validation, mixed prose-and-data files, agent pipelines that produce or
  consume Markdown artifacts, or running the `softschema` CLI.
---
<!-- DO NOT EDIT: written by `softschema skill --install`.
Re-run that command to update.
-->

# Softschema Skill

`softschema` adds and validates structure for Markdown/YAML artifacts that mix prose
context with machine-readable values.
This skill is a routing layer.
The CLI documents itself, so load only the command output you actually need.

## When to Use

A file mixes prose (notes, rationale, summaries) with values that code or a later agent
step needs to read reliably, and those values should be typed or validated without
forcing the rest of the document into a hard schema.

## Bootstrap

Each command prints material the agent should read and follow:

```bash
softschema --help                  # command listing + entry-point pointers
softschema skill --brief           # compact operating brief
softschema docs guide              # mental model and adoption path
softschema docs spec               # exact artifact format
softschema docs example-artifact   # a copyable example
softschema docs --list             # full topic index
```

## Operating Rules

- YAML/frontmatter is authoritative for any consumed value.
  Do not parse Markdown body prose or tables for structured fields.
- Use `softschema.contract` (not `schema`) to name the payload contract.
- Promote a value into YAML only when something consumes it; leave exploratory or
  judgment-heavy content as prose.
- Validate at the boundary with `softschema validate` — `--model` for a Pydantic/Zod
  model, `--schema` for a sidecar. Run `softschema validate --help` for exact syntax.

## Install

softschema ships two interchangeable implementations with the same CLI surface — pick
the runtime you already have. Prefer a version-pinned zero-install runner:

```bash
# Python (Pydantic):
uvx softschema@0.1.3 --help            # ephemeral; reproducible
uv tool install softschema==0.1.3      # persistent; lockfile-friendly

# TypeScript (Zod):
npx @softschema/core@0.1.3 --help      # ephemeral; reproducible
```

Both expose the same commands and flags and validate against the same canonical schema;
the only difference is whether models are written as Pydantic or Zod.

## Self-Install (Optional)

Run once per project to install discoverable mirrors of this skill, so any agent working
in the repo finds it natively:

```bash
softschema skill --install
# writes:
#   .agents/skills/softschema/SKILL.md   (Codex, Gemini CLI, cross-agent installers)
#   .claude/skills/softschema/SKILL.md   (Claude Code mirror)
```

The mirrors carry a `DO NOT EDIT` marker and the version that wrote them.
Re-run `softschema skill --install` to refresh after upgrading.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
