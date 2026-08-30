---
title: Repair as Its Own Command, and Strict Reads
description: Split `validate --repair` into a `repair` command, make strict-versus-checking a property of the command rather than of which flags were passed, and give consuming code a strict `load_artifact`
author: Claude Code, with maintainer direction from Joshua Levy
---
# Feature: Repair as Its Own Command, and Strict Reads

**Date:** 2026-08-30

**Author:** Claude Code, with maintainer direction from Joshua Levy

**Status:** Planned

**Tracking:** `ss-19s5` (epic)

## Overview

`validate --repair` and `validate --check-repair` shipped in the v0.8.0 line and have
not been released. Three problems surfaced while reviewing them, and they share one
cause.

**The flag name is a symptom.** `--check` in this CLI means “do not write; exit 1 on
drift” (`compile --check`, `generate --check`) — a convention that works because those
commands write by default.
`validate` does not write, so the flag had to be compounded into `--check-repair`,
giving `softschema validate --check-repair`: three verbs, two of them synonyms.

**The two flags are not an operation and its dry run.** They have different pass
conditions. `--check-repair` exits 1 when repairs *would* be made even if the document
would validate afterward; `--repair` exits 0 when the result is valid.
Those answer different questions, and fusing them is what forced the compound name.

**Strictness is decided by accident.** The CLI picks strict or lenient behavior by where
a failure lands, not by intent.
`validate` reads eagerly for binding inference, so a read failure escapes as an
exception (exit 2); pass `--contract` and the eager read is no longer needed, the same
failure lands in the verdict path, and the same file now exits 1 with a record.
`--check-repair` has the mirror-image leak: it is the checking mode by definition, but
raises a usage error about `--contract` when it cannot infer a binding.

The library already draws the line correctly — `read_frontmatter_doc` raises,
`validate_artifact` records — and separates the operations into `validate.py` and
`pipeline.py`. The CLI is the only place they are fused.

## Goals

- One command per question, each with a single mode.
- Strict-versus-checking decided by the command, not by which flags were passed.
- Flag names that carry the meaning they already have elsewhere in this CLI.
- Consuming code gets a strict call that cannot be silently ignored.
- Full Python/TypeScript parity: identical surface, verdicts, records, exit classes.
- Mechanical enforcement that the retired surface cannot reappear.

## Non-Goals

- No change to what repair and conform actually do.
  This is surface and failure routing.
- No new dependencies.
- No rewriting of historical review documents.
  They record what was true when written.

## The Surface

### Before

```bash
softschema validate <path>                  # read-only
softschema validate <path> --repair         # repair, conform, write, validate
softschema validate <path> --check-repair   # report what would change; no write
```

### After

```bash
softschema validate <path>            # read-only, strict reads, never writes
softschema repair <path>              # repair, conform, write, validate   exit 0 if valid
softschema repair <path> --dry-run    # same, no write                     exit 0 if valid
softschema repair <path> --check      # same, no write                     exit 1 if anything would change
```

`--repair` and `--check-repair` are removed from `validate`.

### Migration

| Retired | Replacement |
| --- | --- |
| `validate --repair` | `repair` |
| `validate --check-repair` | `repair --check` |
| — | `repair --dry-run` (new) |

## Decisions

**D1 — `repair` is its own command.** The library already separates the operations
(`validate_artifact` in `validate.py`, `repair_and_validate_artifact` in `pipeline.py`);
the CLI now mirrors that.
It also restores `--check` to its exact house meaning, because `repair` writes by
default.

**D2 — `--dry-run` and `--check` both exist, because they are not the same.** This repo
already uses both conventions and they already differ: `skill --install --dry-run`
writes nothing and exits 0; `generate --check` writes nothing and exits 1 on drift.
`--dry-run` suppresses the write and keeps the normal pass condition.
`--check` asserts nothing needed changing.
Shipping only `--check` would leave users reaching for it expecting dry-run semantics
and getting a baffling exit 1 on a document that repaired fine.

**D3 — strictness is a property of the command.**

|  | read failure | rationale |
| --- | --- | --- |
| `validate` | exit 2, one-line stderr, no JSON, **regardless of `--contract`** | the consuming-side gate; an unopenable file is not a failing artifact, it is not an artifact |
| `repair` | record in the result, exit 1, **regardless of whether a binding could be inferred** | the producing-side loop; an unreadable document is the normal case it exists for |

This closes both leaks.
`repair` never raises a usage error about `--contract`: the message
`missing --contract because the document could not be read` disappears, because it
advises a flag that would not have helped.

**D4 — exit classes.** Unchanged in meaning, now applied consistently.

| code | meaning |
| --- | --- |
| 0 | valid |
| 1 | invalid — or, under `repair --check`, something would change |
| 2 | could not run: bad flags, a path that does not exist, an unreadable artifact under `validate` |

**D5 — add a strict consuming API.** `load_artifact` / `loadArtifact`: validate, return
the values, raise on anything short of `valid`. Today a consumer must check `outcome`
itself, and one that forgets gets `values: None` and a downstream
`TypeError: 'NoneType' object is not subscriptable` rather than a usable error.
This is additive and separable from D1–D4.

**D6 — the retired surface is enforced, not merely removed.** A lint check fails the
build if `--check-repair` appears outside `docs/project/reviews/`, where historical
records legitimately name it.

## Propagation Map

Derived artifacts are regenerated, never hand-edited, and the order matters.
Getting this wrong produces a green local test run and a red `cross-impl-diff.sh`.

| Canonical | Derives to | Via |
| --- | --- | --- |
| `skills/softschema/SKILL.md` | `.agents/skills/…`, `.claude/skills/…` | `softschema skill --install` (in `make format`); enforced by `test_skill_mirror_drift.py` and `mirror-drift.test.ts` |
| `skills/softschema/SKILL.md` | asserted byte-for-byte in `tests/golden/scenarios/inspect-and-docs.tryscript.md` | golden corpus |
| `README.md`, `docs/*.md` in `RESOURCE_PATHS` | `packages/typescript/resources/**` | `bun run --cwd packages/typescript build` |
| `docs/softschema-spec.md` | compared across implementations as `docs spec` | `cross-impl-diff.sh` |

**Required order:** edit canonical → `make format` (reflows Markdown *and* regenerates
the skill mirrors) → rebuild the TypeScript package → run `cross-impl-diff.sh`.

## Files

**Source.**
`packages/python/src/softschema/{cli.py,repair.py,pipeline.py,validate.py,__init__.py}`;
`packages/typescript/src/{cli.ts,repair.ts,repairValidate.ts,validate.ts,index.ts}`.

**Tests.** `packages/python/tests/test_cli.py`;
`packages/typescript/test/repair-profile-detection.test.ts`;
`tests/golden/scenarios/validate-repair.tryscript.md` (renamed to
`repair.tryscript.md`); `tests/golden/scenarios/inspect-and-docs.tryscript.md`;
`tests/golden/README.md`; `tests/golden/cross-impl-diff.sh`.

**Docs.** `docs/softschema-spec.md`, `docs/softschema-guide.md`,
`docs/softschema-python-design.md`, `docs/softschema-typescript-design.md`,
`docs/agent-repair.runbook.md`, `skills/softschema/SKILL.md`, `CHANGELOG.md`,
`README.md`.

**Manual harness.** `tests/manual/agent-repair/{evaluate.py,feedback.py,summarize.py}`.

**Not touched.** `docs/project/reviews/**` — historical records.
`docs/project/specs/active/plan-2026-08-29-validate-repair.md` gets a forward link and a
status note, not a rewrite.

## Phases

1. **CLI surface.** New `repair` command with `--dry-run` and `--check`; remove both
   flags from `validate`. Both languages, identical surface.
2. **Strict and checking reads.** Close both leaks per D3.
3. **`load_artifact` / `loadArtifact`.** Additive; separable if the release needs
   cutting.
4. **Tests.** Unit coverage in both languages for the new surface and both leak fixes;
   golden scenario renamed and rewritten; `inspect-and-docs` refreshed.
5. **Docs.** All canonical docs, then derived artifacts regenerated in order.
6. **Manual harness.** Update the three scripts; re-run the runbook end to end.
7. **Enforcement.** Lint check per D6.

## Validation

- `pytest`, `bun test`, `tsc --noEmit`, `biome ci`, `publint`
- golden corpus on Python, Node, and Bun; `cross-impl-diff.sh`
- `devtools/lint.py --check`, `make format-check`
- the agent-repair runbook, all four phases, against the rebuilt CLI

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
