---
name: softschema
description: >-
  Validate and structure Markdown/YAML artifacts with frontmatter contracts.
  Mix prose context with machine-readable values without forcing the whole
  document into a hard schema. Use when working with soft schemas, frontmatter
  validation, mixed prose-and-data files, agent pipelines that produce or
  consume Markdown artifacts, or running the `softschema` CLI.
allowed-tools: ["Bash(softschema:*)"]
---
<!-- DO NOT EDIT format=f01: written by `softschema skill --install`.
Re-run that command to update.
-->

# softschema Skill

`softschema` adds and validates structure for Markdown/YAML artifacts that mix prose
context with machine-readable values.
This skill is a routing layer.
The CLI documents itself, so load only the command output you actually need.

## When to Use

A file mixes prose (notes, rationale, summaries) with values that code or a later agent
step needs to read reliably, and those values should be typed or validated without
forcing the rest of the document into a hard schema.

## Pick One Runner First

Pick one command prefix, then use it for every command in this skill.
In examples, `$SS ...` means “run the selected prefix with these arguments.”

1. If `softschema --version` works, use `SS='softschema'`.
2. Else if `uvx --version` works, use `SS='uvx softschema@latest'`.
3. Else if `npx --version` works, use `SS='npx softschema@latest'`.
4. Else install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh` or
   `brew install uv`) or Node (`brew install node`), then retry.

The unpinned `@latest` is a deliberate repo policy, not an oversight: installs resolve
through a release-age cool-off gate (see `$SS docs installation`), which is this
project’s supply-chain control in place of a pinned version.

`$SS doctor` reports the installed version, available runners, and recommended command
prefix.

## Bootstrap

Each command prints material the agent should read and follow:

```bash
$SS --help                  # command listing + entry-point pointers
$SS skill --brief           # compact operating brief
$SS docs guide              # mental model and adoption path
$SS docs spec               # exact artifact format
$SS docs example-artifact   # a copyable example
$SS docs --list             # full topic index
```

## Operating Brief

<!-- BEGIN SOFTSCHEMA BRIEF -->
Use soft schemas when humans or agents write Markdown/YAML artifacts and tools need to
consume some values reliably.

- YAML/frontmatter is authoritative for any consumed value.
  Do not parse Markdown body prose or tables for structured fields.
- The `softschema:` block is the self-description quartet: `contract` (the payload
  contract ID), `schema` (relative path to the compiled schema), `envelope` (the payload
  key), `status` (strictness).
  A fully self-describing artifact validates with `$SS validate doc.md`, no flags.
- Promote a value into YAML only when something consumes it; leave exploratory or
  judgment-heavy content as prose.
- Read `$SS docs guide` for the mental model.
- Read `$SS docs spec` for the exact artifact format.
- Inspect `$SS docs example` and `$SS docs example-artifact` for the copyable movie
  example; `$SS docs example-schema` prints its compiled schema.
- Validate at the boundary with `$SS validate`: no flags for a self-describing artifact;
  `--schema` to override with a compiled schema; `--model` for a Pydantic/Zod model
  (imports and runs local code — trusted models only; `--schema` is the safe path for
  untrusted input). Run `$SS validate --help` for exact syntax.
- Keep examples copyable; do not scaffold or mutate a target project unless the user
  explicitly asks for that workflow.

<!-- END SOFTSCHEMA BRIEF -->

## Install

softschema ships two interchangeable implementations with the same CLI surface; pick the
runtime you already have.
Use a zero-install runner:

```bash
# Python (Pydantic):
uvx softschema@latest --help            # ephemeral
uv tool install softschema             # persistent

# TypeScript (Zod):
npx softschema@latest --help            # ephemeral
```

Both expose the same commands and flags and validate against the same canonical schema;
the only difference is whether models are written as Pydantic or Zod.

## Self-Install (Optional)

Run once per project to install discoverable mirrors of this skill, so any agent working
in the repo finds it natively:

```bash
$SS skill --install
# writes:
#   .agents/skills/softschema/SKILL.md   (Codex, Gemini CLI, cross-agent installers)
#   .claude/skills/softschema/SKILL.md   (Claude Code mirror)
```

The mirrors carry a `DO NOT EDIT` marker.
Re-run `softschema skill --install` to refresh after upgrading.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
