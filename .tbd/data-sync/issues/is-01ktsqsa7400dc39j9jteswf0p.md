---
type: is
id: is-01ktsqsa7400dc39j9jteswf0p
title: "P1: TypeScript cli.ts hardening (exit hygiene, EPIPE/SIGINT, safe error casts, --help epilog, --version, resource-root fail-clear)"
kind: task
status: closed
priority: 1
version: 7
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqsdqeadg067hwcw146k2m
  - type: blocks
    target: is-01ktsqsexjfpcr1t1j2m7q9jdx
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:31.908Z
updated_at: 2026-07-10T03:49:14.541Z
closed_at: 2026-06-10T21:56:58.684Z
close_reason: null
---
FILE SCOPE: packages/typescript/src/cli.ts only.
- Replace process.exit(code) after async with process.exitCode = code (avoid piped-stdout truncation, HIGH 1.1).
- Add EPIPE handlers on stdout and stderr; SIGINT handler exits 130.
- Replace (err as Error).message with err instanceof Error ? err.message : String(err) in all catch blocks.
- Add agent --help epilog via commander addHelpText('afterAll', ...) with the SAME text as Python cli.py:107-111 (HIGH: npm bootstrap chain). 
- Add --version (.version(packageVersion())).
- readResource walk-up: named constant (MAX_RESOURCE_WALK_DEPTH) replacing magic 6; raise clear error when unresolved.
PARITY PAIR with P1 python cli.py bead. Unit tests in cli-inprocess.test.ts. Refs review TS 1.1, 2.1, 2.2(magic 6), 6.1, Skill 3b.
