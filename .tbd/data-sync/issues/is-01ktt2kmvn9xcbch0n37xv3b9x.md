---
type: is
id: is-01ktt2kmvn9xcbch0n37xv3b9x
title: "TS generate: runtime errors must exit 2 with 'softschema generate:' prefix (parity with Python)"
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktt2km937gwscjjj37h82nbr
created_at: 2026-06-11T00:51:40.533Z
updated_at: 2026-07-10T03:49:17.790Z
closed_at: 2026-06-11T00:55:47.429Z
close_reason: null
---
packages/typescript/src/cli.ts:380-383: runGenerate catches runtime errors with 'error: <path>: ...' and returns 1; Python (cli.py) uses 'softschema generate: <path>: ...' and exit 2, reserving 1 for drift (PR #9 finding 1, P1). Fix prefix+exit, add neutral golden scenario for a generate runtime error (stable prefix, engine tail elided), and add the case to tests/golden/cross-impl-diff.sh so the class cannot regress.
