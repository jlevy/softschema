---
type: is
id: is-01ktsqsbefac673f2fnda3x2tn
title: "P2: Golden harness runs TS under Node and Bun (run.sh)"
kind: task
status: open
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqsbrrhh45t4tk5gb98jza
  - type: blocks
    target: is-01ktsqsc7c53he9194darnhdzw
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:33.167Z
updated_at: 2026-06-10T21:43:54.501Z
---
FILE SCOPE: tests/golden/run.sh.
- SOFTSCHEMA_IMPL=ts targets 'node $REPO/packages/typescript/dist/cli.js' (the PUBLISHED runtime); add SOFTSCHEMA_IMPL=ts-bun for 'bun ...'. Map per-impl scenario dir: ts and ts-bun both use scenarios-ts/. Keep the 'no per-impl scenarios' guard.
Root cause: today the corpus only runs under Bun; Node (what npm users get) never runs it (design issue 4). Blocks the CI matrix bead.
