---
type: is
id: is-01m18tjw5key5thy17bxmjqq64
title: agent-repair harness reports a correctly-refused artifact as no_structural_verdict
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:54:14.066Z
updated_at: 2026-08-30T18:42:16.880Z
closed_at: 2026-08-30T18:42:16.880Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
Found running the runbook end to end on 2026-08-30. In the prose phase, CROX.md arrived with an unterminated frontmatter fence -- a genuinely truncated model write. Both paths correctly refused it (exit 2, naming the delimiter), which is the fix from PR #52 working on live output.

evaluate.py classified it as 'no_structural_verdict', which reads like a harness failure rather than the correct outcome. summarize.py then lists it beside real verdicts with no indication that refusing was right.

The runbook's Expected Results table does not mention this verdict for Phase 2 either, so a reader hitting it has nothing to compare against.

Suggested: add an 'unreadable_refused' verdict for the case where both plain validate and --check-repair exit 2 naming the same cause, and mention in the runbook that a truncated write in the corpus is expected occasionally and is a pass, not a failure.

Files: tests/manual/agent-repair/evaluate.py, tests/manual/agent-repair/summarize.py, docs/agent-repair.runbook.md
