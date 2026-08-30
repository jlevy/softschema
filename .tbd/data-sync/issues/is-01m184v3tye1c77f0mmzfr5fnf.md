---
type: is
id: is-01m184v3tye1c77f0mmzfr5fnf
title: Run the agent-repair runbook end to end and record the evidence
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies:
  - type: blocks
    target: is-01m184vk6ayjkkpjp9d7ncgnfh
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:34:15.390Z
updated_at: 2026-08-30T01:49:42.409Z
closed_at: 2026-08-30T01:49:42.409Z
close_reason: "Ran all four phases against the fixed build. Phase 1: 9/12 invalid on arrival, 9/9 repaired to valid unaided, rubric_version 1.10 preserved as '1.10', all three conformance guarantees held. Phase 2: 12/12 invalid, 906 paired undeclared_property/missing_property records, 0 renames. Phase 3: 12/12 to valid in one round, 906 errors to 0. Phase 4: both paths exit 2 naming the same cause. Runbook expected-results updated to give both recorded runs and mark which parts are assertions rather than sampled counts."
resolution: null
duplicate_of: null
---
Execute docs/agent-repair.runbook.md as written, against the fixed build, and record
what it produced.

This is the acceptance gate for the epic: the fixes are not done until the runbook a
reader would follow actually produces the results it claims, on the code as shipped.

Record: per-phase counts, the repairs applied, the error codes reported, the feedback
round's before/after, and the Phase 4 regression verdict. Update the runbook's expected
results to the observed numbers if they move.
