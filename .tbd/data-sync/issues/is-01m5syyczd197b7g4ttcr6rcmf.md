---
type: is
id: is-01m5syyczd197b7g4ttcr6rcmf
title: "PR #65 review A follow-up: fix A1-A5 before the 0.9.0 release (zod 4.6 format leak, CHANGELOG sha256 scope, CHANGELOG precision, pin zod JSON Schema output, harden typescript/cross-impl jobs)"
kind: task
status: closed
priority: 1
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m5rt23qna630vr0y300jnhrb
created_at: 2026-10-25T16:40:18.669Z
updated_at: 2026-10-25T17:03:58.036Z
closed_at: 2026-10-25T17:03:58.035Z
close_reason: "Fixed A1-A5 of PR #65 review A in PR #66 (https://github.com/jlevy/softschema/pull/66), commits c770f2f (compiler: strip zod 4.6 affix formats and restore the earlier format; drop redundant closed-tuple items:false; KitchenSink gains sku/filename/contact/pair, parity.schema.yaml 058b039d->6fafec02; unit test pins other zod 4.6 changes; CHANGELOG A2/A3; spec + TS design doc) and 6faa74e (ci: persist-credentials false + --ignore-scripts in typescript and cross-impl). Local: lint ok, pytest 247 passed, bun test 246 pass, goldens py 80/ts 78/ts-bun 80, cross-impl OK, compile --check no drift in both runtimes. CI run 40214425298: 19/19 checks pass. Reply on #65: issuecomment-6400521286."
resolution: null
duplicate_of: null
---
