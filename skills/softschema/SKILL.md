---
name: softschema
description: >-
  Author, inspect, consume, and validate Markdown/frontmatter or pure YAML artifacts
  with typed YAML contracts and inert prose. Use when a task mentions soft schemas,
  softschema, frontmatter, YAML contracts, agent-authored artifacts, artifact validation,
  structured values beside prose, compiled JSON Schema, or the softschema CLI.
---
# softschema Skill

Keep every consumed value in YAML and leave narrative context as inert Markdown.
Use the CLI and bundled docs as the detailed interface; load only the topic needed for
the current job.

<!-- BEGIN SOFTSCHEMA BRIEF -->
## Qualify a Runner

Derive required capabilities first: schema-only, pure YAML, Python/Pydantic, built
JavaScript/Zod, or Bun source TypeScript/Zod.
Try candidates in this order:

```bash
softschema doctor --json
uvx --from 'softschema==0.2.2' softschema doctor --json
npx --yes softschema@0.2.2 doctor --json
bunx --bun softschema@0.2.2 doctor --json
```

Accept a candidate only when protocol `1` reports the needed operation, artifact format,
runtime, and model loader.
For `pure-yaml`, also require `validate --help` to list the profile.
Reuse the complete qualifying command prefix.
If none qualifies, report the missing capability and runtime and say that softschema
must be installed or upgraded to a release that advertises it.
Do not improvise another runner.

## Route the Task

- **Author a contract or artifact:** read `softschema docs guide`, then
  `softschema docs spec` for exact rules and `softschema docs example` for copyable
  paired sources.
- **Validate one or many files:** run `softschema validate --help`; select the profile
  explicitly. Legacy JSON applies when discovery classifies one single explicit path as a
  regular file, including when a later read fails, and for the narrow missing-path or
  broken-symlink `not_found` exception; other discovery failures and batch work use
  diagnostic JSON/JSONL/SARIF.
- **Consume values in application code:** read `softschema docs api` when available;
  otherwise use `softschema docs guide` and the runtime design topic.
  Validate at the boundary and inspect structured result fields, not message prose.
- **Change softschema itself:** read the repository `AGENTS.md` and
  `softschema docs development`; update shared vectors first and keep Python, Node, and
  Bun green.

Validate a self-describing Markdown artifact with:

```bash
softschema validate doc.md
```

## Operating Rules

- Treat YAML/frontmatter as authoritative.
  Never parse Markdown body prose or tables for structured fields.
- Use a mapping with exact quoted `softschema.format: "1"` for new artifacts.
  Use `softschema.contract` for the logical payload contract; it is not a schema path,
  model import, or JSON Schema `$id`.
- Select `frontmatter-md` or `pure-yaml` explicitly.
  A filename suffix never selects a profile.
- Promote a value into YAML only when a downstream consumer needs it.
  Keep analysis, uncertainty, and judgment-heavy context as prose.
- Preserve unknown format-1 extension values as portable data.
  Extensions never authorize imports, retrieval, plugins, or validation behavior.
- Prefer a reviewed compiled schema for untrusted artifacts.
  Model loading imports and executes trusted local Pydantic or Zod code.
- Expect validation to remain offline.
  Only fragments and already-loaded explicit resources are available; never fetch a
  schema because a reference names a URI.
- Keep examples copyable.
  Do not scaffold, install, or mutate a project unless the user requested that action.

Use `softschema docs --list --json` to discover the installed topic set rather than
guessing a resource name.

<!-- END SOFTSCHEMA BRIEF -->

## Install the Skill Safely

Run `softschema skill --install --help`, choose project or personal scope, and preview
every resolved target with `--dry-run` before writing.
Agent selectors replace the default portable project pair.
Never infer a personal install from the current directory, and never overwrite unmanaged
or locally modified content.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
