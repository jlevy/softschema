---
name: softschema
description: >-
  Validate YAML and Markdown artifacts with gradual contracts. Use for Markdown
  with YAML frontmatter or pure YAML records, soft/permissive/enforced schema
  maturity, record enhancement, agent and software pipelines, import staging,
  or running the `softschema` CLI.
allowed-tools: ["Bash(softschema:*)"]
---
<!-- DO NOT EDIT format=f02: written by `softschema skill --install`.
Re-run that command to update.
-->

# softschema Skill

`softschema` adds gradual contracts to YAML data.
The standard profile is Markdown with YAML frontmatter and an optional body.
Pure YAML is also supported when the structured record stands on its own.
This skill gives the working rules; the CLI documents the rest, so load only the command
output you need.

## When to Use

Use softschema when software or agents read values from YAML records whose shape is
still settling, or when a record needs prose context beside its structured payload.
Name a contract, validate the fields that have stabilized, and tighten the contract from
`soft` to `permissive` to `enforced` as consumers come to rely on it.
Skip it when nothing reads the structured values.

## Pick One Runner First

Pick one command prefix, then use it for every command in this skill.
In examples, `$SS ...` means “run the selected prefix with these arguments.”

1. If `softschema --version` works, use `SS='softschema'`.
2. Else if `uvx --version` works, use `SS='uvx softschema@latest'` (Python).
3. Else if `npx --version` works, use `SS='npx -y softschema@latest'` (TypeScript).
4. Else install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh` or
   `brew install uv`) or Node (`brew install node`), then retry.

The two implementations take the same commands and flags and return the same results.
The zero-install forms need no setup and resolve the latest release each time; a project
that runs softschema in CI should add it as a lockfile-pinned dependency instead (see
`$SS docs installation`). `$SS doctor` reports the version, the available runners, and
the recommended prefix.

## Operating Brief

<!-- BEGIN SOFTSCHEMA BRIEF -->
Use soft schemas when humans, agents, or software produce YAML records whose consumed
structure should stabilize over time.

- YAML is authoritative for any consumed value.
  In `frontmatter-md`, the Markdown body is reader-facing.
  Do not parse Markdown body prose or tables for structured fields.
- Choose the artifact profile independently of the contract status: `frontmatter-md`
  when the payload benefits from a Markdown body, `pure-yaml` when the whole artifact is
  structured data.
- The `softschema:` block names the contract (`contract`, the payload contract ID), the
  compiled schema (`schema`, a path relative to the document), the payload key
  (`envelope`), and the maturity (`status`: `soft`, `permissive`, or `enforced`). An
  artifact with all four validates with `$SS validate <artifact>` and no flags.
- Treat status as boundary maturity.
  A bound schema or model checks the payload under every status; `enforced` additionally
  rejects fields the schema does not declare.
  Add a field to the contract when a consumer relies on it, and leave uncertain fields
  outside it until they stabilize.
- After writing an artifact, run `$SS repair <file>`. It quotes a plain value YAML would
  read as structure (an unquoted `: `), escapes a raw control or line-separator
  character inside a value (`"\N"`, `"\x01"`), and quotes a scalar such as `1850` where
  the contract wants a string; then it writes the file and validates.
  It reports what it cannot fix and never guesses at it.
- At a boundary, run `$SS validate <file>`. It never writes.
  Add `--require structural` (or `semantic`, repeatable) when the handoff needs a check
  that actually ran: without it, an artifact with no schema bound can still be `valid`.
- Judge each check by `execution` as well as `ok`: `completed` means the validator ran
  and `ok` is its verdict; `not_run` and `errored` establish nothing.
  Declared status is no evidence that a validator ran, and a record without `execution`
  has unknown execution.
- Write YAML both engines read the same way: core-form numbers (`1000`, not `1_000`),
  printable text with escapes for control characters, spaces rather than tabs, no
  anchors, tags, or `%YAML 1.1`. The refusal message names the line and the fix.
- Date- and timestamp-shaped scalars are strings.
  JSON Schema `format` is annotation-only; use a semantic model or an explicit pattern
  when date validity matters.
- `--model` imports and runs local code; use it only with trusted models.
  `--schema` with a compiled schema executes nothing.
- Read `$SS docs guide` for the mental model and `$SS docs spec` for the exact rules.

<!-- END SOFTSCHEMA BRIEF -->

## Core Workflow

```bash
$SS docs example-artifact > spirited-away.md      # a copyable, self-describing artifact
$SS docs example-schema > movie-page.schema.yaml  # the schema it names
$SS repair spirited-away.md                       # producer: fix, write, validate
$SS validate spirited-away.md --require structural  # consumer: read-only gate
```

- `repair --dry-run` reports what would change without writing; `repair --check` fails
  when anything would change, which is what a review gate wants.
  `repair` takes no `--require`; follow it with `validate --require` when a gate needs
  completed checks.
- Override the document with `--schema`, `--envelope`, `--contract`, `--status`, or
  `--profile` when a run must point elsewhere.
- Compile a schema from a model with
  `$SS compile <module:Model> --contract <id> --out <file>`, and run the same command
  with `--check` in CI to catch drift.

## Reading Results

Exit `0` is valid, `1` is invalid (or, under `repair --check`, something would change),
and `2` means the command could not run: bad options, or an artifact `validate` cannot
read.
`validate` reports an unreadable artifact as one line on stderr and prints no JSON;
`repair` reports the same cause as a JSON record at exit `1`.

The JSON result carries:

- `outcome`: `valid`, `invalid`, or `input_error` (`repair` on a file that is missing or
  not UTF-8; one that does not parse is `invalid`).
- `structural` (JSON Schema) and `semantic` (Pydantic or Zod model), each with
  `execution`, `ok`, `errors`, and `skipped_reason` (why a layer was `not_run`, such as
  `no_schema` or `no_semantic_model`).
- `status`: the effective status; `document_metadata` is what the artifact declared.
- `warnings`, advisory and never a failure: `document-enforcement-not-applied` or
  `document-enforcement-via-model-only` when the status is `enforced` but no schema
  check completed, and `document-status-mismatch` when a caller’s status (such as
  `--status`) differs from the document’s; the library’s advisory metadata mode adds
  `document-contract-mismatch`. Every warning code starts with `document-`.
- `repairs`: `repair_applied` records whose `code` is `yaml_quoted_scalar`,
  `yaml_escaped_character`, or `scalar_conformed`.
- `values`: the payload, when it was read.

Every error has a `kind`. A schema violation is `kind: schema_violation` with a `code`
of `missing_property`, `undeclared_property`, `invalid_value`, or `unmapped_keyword` (a
keyword softschema has no category for yet), a `path`, and, for the first two, the
`property`. Match on `kind`, `code`, `path`, and `property`, never on `message`.
`check_not_completed` means a layer named in `--require` did not run: bind a schema
(`softschema.schema` or `--schema`) or a model.

## Common Refusals and Fixes

| Message or kind | Fix |
| --- | --- |
| `yaml_unsupported_scalar`: plain scalar `1_000`, `0b101`, `-0x10`, or `.5e3` | Write a core number (`1000`, `5`, `-16`, `500.0`) or quote it to keep a string. |
| `unacceptable character #x0085` (any control or line separator) | Run `repair`, which escapes it inside a value; in a key, comment, or block scalar, write the escape the message names inside double quotes. |
| `unacceptable tab character` or `found character '\t'` | Replace the tab with spaces, or quote the value (`"a\tb"`). |
| `mapping values are not allowed here` or `Nested mappings are not allowed` | Run `repair`, which quotes a value holding `: `. |
| `':' ... has no space after it inside a flow collection` (`[a:, b]`) | Add a space after the `:`, or quote the item. |
| `unsupported directive` | Delete the `%YAML 1.1` line or write `%YAML 1.2`. |
| `number_negative_zero` or `number_out_of_range` | Write `0` for `-0`; quote an integer whose magnitude is 2^53 or more, `.inf`, or `.nan` to keep it as a string. |
| `yaml_duplicate_key`, `yaml_alias`, `yaml_merge_key`, `yaml_custom_tag`, `yaml_non_string_key`, `yaml_limit` | Remove the duplicate, anchor, `<<`, or `!!tag`; quote a numeric key (`"1":`); keep nesting under 64 levels. |
| `schema_invalid`, `reason: dialect` | Use `$schema: https://json-schema.org/draft/2020-12/schema` or delete the line; write `dependentRequired` or `dependentSchemas` for `dependencies`, and `type: [..., "null"]` for `nullable`. |
| `schema_invalid`, `reason: resource_identity` (`$id` or `--schema-id`) | Write `https://host/path` with a path and no `#`, lowercase scheme and host, no default port, `file:///path`, or a lowercase `urn:<nid>:<name>`. |
| `schema_invalid`, `reason: reference` | Fix or remove the `$ref`; one that cannot resolve is refused even on a branch the payload never reaches. |
| `schema_missing` | The `schema:` path is relative to the document; pass an absolute path with `--schema`. |
| `envelope_ambiguous` | Add `envelope: <key>` to the `softschema:` block. |

A block scalar that ends the YAML (`body: |` as the last key) keeps its final line
break; write `|-` to drop it.

## Performance

Write clean, readable YAML by default.
A document of tens of KB parses in milliseconds, and each CLI run costs 0.2–1.3 s to
start, so the format matters only for megabytes parsed often (a hot loop, CI over many
files, a service). Then:

- In Python, write bulk data as JSON syntax, which is valid YAML: it reads more than 10
  times faster than block YAML. TypeScript reads both at about 1 s per MB.
- Keep tabs out of block YAML, even in comments; in Python they force the slower pure
  parser.
- In Python, install `ruamel.yaml.clib` (not `ruamel.yaml[libyaml]`) for block YAML 4 to
  7 times faster with identical results:
  `uvx --with ruamel.yaml.clib softschema@latest`, or `uv add ruamel.yaml.clib`. A bare
  `uvx softschema@latest` runs the pure parser; `$SS doctor` shows which is in use.
- Validate many files in one process through the library, not one CLI run per file.

`$SS docs guide` has the measurements and what keeps a file on each fast path.

## Bootstrap

```bash
$SS --help                  # command listing + entry-point pointers
$SS skill --brief           # the operating brief above
$SS docs guide              # mental model, playbooks, and performance
$SS docs spec               # exact artifact format and validation rules
$SS docs --list             # full topic index
```

## Self-Install (Optional)

Run once per project to install discoverable mirrors of this skill, so any agent working
in the repo finds it natively:

```bash
$SS skill --install --scope project --agent portable --agent claude
# writes:
#   .agents/skills/softschema/SKILL.md   (Codex, Gemini CLI, cross-agent installers)
#   .claude/skills/softschema/SKILL.md   (Claude Code mirror)
```

The mirrors carry a `DO NOT EDIT` marker.
Re-run the same command to refresh them after upgrading.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
