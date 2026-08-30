---
type: is
id: is-01m184s19wd17m979jyyh4fzez
title: End-to-end validation of validate --repair
kind: epic
status: open
priority: 1
version: 11
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies: []
child_order_hints:
  - is-01m184sh0j1sn4vms3y0p3ft8m
  - is-01m184t4f55k2qgsm215ve0cdz
  - is-01m184t4z0a98z50dphabs947j
  - is-01m184tjxg9zgfkppdsm13fcsh
  - is-01m184tkby56c2s7phxdzm1kq1
  - is-01m184v3azww4fsvna605zm3d1
  - is-01m184v3tye1c77f0mmzfr5fnf
  - is-01m184vjqxckqhnfdb28gze3b2
  - is-01m184vk6ayjkkpjp9d7ncgnfh
  - is-01m184zv333e0hf9wf6n3b0gbt
created_at: 2026-08-30T01:33:07.260Z
updated_at: 2026-08-30T01:36:50.275Z
---
Close the loop on the `validate --repair` feature before v0.8.0 ships: fix the defect
that end-to-end agent testing found, prove the fix with automated cases, and leave a
runbook that reproduces the whole exercise against a real low-thinking model.

## Background

`--repair` exists so a producing agent can run the same check its consumer will run.
End-to-end testing drove Gemini 2.5 Flash at `thinkingBudget: 0` over a form contract
loosely borrowed from the GTIA v2 `prelim-scan-terms` form in `finterm-ai/trading`,
feeding the agent only a prose runbook and a template so drift arose naturally.

Two halves of the feature came out well and need no change:

- Scalar conform repaired 9 of 12 templated artifacts unaided, preserving the trailing
  zero in `rubric_version: 1.10` as the spec promises.
- Near-miss field names (`query`/`reason` for `term`/`why`) were reported rather than
  renamed, as paired `undeclared_property`/`missing_property` records precise enough
  that the same zero-thinking model fixed all 880 errors across 12 artifacts in one
  feedback round.

One half is broken, and it is the premise of the feature: see the child bugs.

Full findings: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
