---
type: is
id: is-01ksrzx0w8ndkx2avb3qpjgv2c
title: "[deferred] Migrate CLI to Typer + Rich per python-cli-patterns"
kind: task
status: closed
priority: 3
version: 5
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:25.767Z
updated_at: 2026-07-10T03:49:43.131Z
closed_at: 2026-07-10T03:49:43.130Z
close_reason: "Rejected after current-main audit: origin/main's argparse/Commander CLIs already satisfy exact Python/TypeScript golden and byte parity, and the July architecture explicitly retains those adapters. Typer and Rich would add dependencies and framework-specific help/error behavior without a current interactive or styled-output requirement."
---
Audit P3. python-cli-patterns recommends Typer (or argparse + rich_argparse) for CLI and Rich for terminal output. Current CLI uses plain argparse with manual JSON emission. A migration would unlock --format text|json|jsonl, --no-progress, NO_COLOR/CI handling, base command pattern, and CLIError class hierarchy out of the box. Wait for a concrete consumer that benefits before the rework.

## Notes

## Typer vs argparse — codebase-specific analysis (decided: DEFER as of v0.2.2)

Decision: keep argparse for now; revisit only with a concrete consumer that benefits.
This is grounded in softschema's actual constraints, not general framework preference.

### What dominates the decision here
1. Byte-for-byte Python<->TypeScript parity is the project's core invariant, enforced by
   tests/golden (run.sh on py/ts/ts-bun) and cross-impl-diff.sh, which byte-compares
   STDOUT and EXIT CODES for validate/compile/inspect/docs/skill/generate/--version. The
   TS CLI is built on commander.
2. The CLI emits only JSON or plain text — no color by design (TS design doc), and
   cross-impl-diff.sh forces NO_COLOR=1.
3. The repo is deliberately lean (5 runtime deps) and runs a strict 14-day supply-chain
   cool-off with per-package exceptions.

### Pros of Typer (Click + Rich) in the abstract
- Less parser boilerplate: the ~110-line argparse setup becomes typed command functions;
  params get type validation for free.
- Built-ins it would unlock: --format text|json|jsonl, NO_COLOR/CI handling (ss-ief7), a
  CLIError/exit-code hierarchy (ss-h8u4), and styled help.
- Click's CliRunner is ergonomic (though the project tests via the framework-agnostic
  golden corpus, so this is marginal).

### Cons / why it is a poor fit for THIS CLI
- Parity gets HARDER, not easier. Typer is Click-based; Click's --version string
  ('prog, version X'), --help layout (usage line, Rich panels), and usage-error text all
  differ from commander. The harness byte-compares --version stdout and locks exit codes,
  so matching commander means overriding Click's formatting throughout — fighting the
  framework to suppress the very features you adopted it for. argparse's plainer output is
  already tuned to match commander.
- Typer's headline value (Rich styled output) is explicitly unwanted: the CLI is
  JSON-only / no-color by design and the harness sets NO_COLOR=1, so Rich is dead weight
  or actively harmful to parity.
- Dependency + supply-chain cost: argparse is stdlib (0 deps). Typer adds Click (+ Rich
  for Typer[all]), enlarging the runtime surface and the cool-off review burden, against a
  repo that keeps deps minimal. The TS side carries one CLI dep (commander); adding two on
  the Python side widens the asymmetry.
- It re-opens parity risk across every subcommand for a CLI that is already correct and
  golden-locked, with zero functional gain for users (output is unchanged JSON).
- The one concrete item Typer would 'give for free' — the CLIError/exit-code hierarchy
  (ss-h8u4) — is implementable in plain argparse with a small exception class and the
  existing _run_cmd boundary, no new deps, no parity risk. Done in v0.2.2.

### When migrating WOULD pay off (the 'concrete consumer' trigger)
If the CLI gains human-facing styled output, multiple output formats
(--format text|json|jsonl), progress bars, interactive prompts, or grows well beyond its
current 7 subcommands — i.e., when it stops being a lean, JSON-only, parity-locked tool.
Until then argparse is the better fit. Treat any future migration as a MINOR release (not
a patch) because it re-establishes CLI parity.
