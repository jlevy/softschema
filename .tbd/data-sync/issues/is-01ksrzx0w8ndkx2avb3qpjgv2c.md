---
type: is
id: is-01ksrzx0w8ndkx2avb3qpjgv2c
title: "[deferred] Migrate CLI to Typer + Rich per python-cli-patterns"
kind: task
status: open
priority: 3
version: 1
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:25.767Z
updated_at: 2026-05-29T04:29:25.767Z
---
Audit P3. python-cli-patterns recommends Typer (or argparse + rich_argparse) for CLI and Rich for terminal output. Current CLI uses plain argparse with manual JSON emission. A migration would unlock --format text|json|jsonl, --no-progress, NO_COLOR/CI handling, base command pattern, and CLIError class hierarchy out of the box. Wait for a concrete consumer that benefits before the rework.
