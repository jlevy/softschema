---
type: is
id: is-01ksrzx1224nr63bc58dg8gg9n
title: "[deferred] Define CLIError class hierarchy with consistent exit codes"
kind: task
status: open
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:25.953Z
updated_at: 2026-06-15T17:41:51.733Z
---
Audit P3. python-cli-patterns prescribes a CLIError / ValidationError / UserCancelled hierarchy with documented exit codes (0 success, 1 error, 2 validation, 130 SIGINT). Current CLI returns ad hoc 0/1/2. Document the existing codes in the epilog (done in earlier P1 pass) and introduce the class hierarchy when the CLI grows beyond ~6 subcommands or gains interactive prompts.

## Notes

v0.2.2: introduced an explicit UsageError(ValueError) class and documented the 0/1/2 exit-code contract in cli.py; the user-error boundary now excludes bug-indicator types. The full Typer-style CLIError/ValidationError/UserCancelled hierarchy remains deferred with the Typer migration (ss-08np) since the CLI stays argparse-based and JSON-only.
