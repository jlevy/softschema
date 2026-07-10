---
type: is
id: is-01ksrzx1224nr63bc58dg8gg9n
title: "[deferred] Define CLIError class hierarchy with consistent exit codes"
kind: task
status: closed
priority: 3
version: 5
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:25.953Z
updated_at: 2026-07-10T03:49:43.322Z
closed_at: 2026-07-10T03:49:43.321Z
close_reason: "Implemented to the required boundary and superseded: origin/main has an explicit UsageError boundary and documented 0/1/2 exit contract; ss-b5l4 owns remaining Python/Commander exit parity. A Typer-style exception hierarchy is not required by the settled non-interactive CLI design."
---
Audit P3. python-cli-patterns prescribes a CLIError / ValidationError / UserCancelled hierarchy with documented exit codes (0 success, 1 error, 2 validation, 130 SIGINT). Current CLI returns ad hoc 0/1/2. Document the existing codes in the epilog (done in earlier P1 pass) and introduce the class hierarchy when the CLI grows beyond ~6 subcommands or gains interactive prompts.

## Notes

v0.2.2: introduced an explicit UsageError(ValueError) class and documented the 0/1/2 exit-code contract in cli.py; the user-error boundary now excludes bug-indicator types. The full Typer-style CLIError/ValidationError/UserCancelled hierarchy remains deferred with the Typer migration (ss-08np) since the CLI stays argparse-based and JSON-only.
