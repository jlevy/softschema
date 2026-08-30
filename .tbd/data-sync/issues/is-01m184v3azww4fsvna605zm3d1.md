---
type: is
id: is-01m184v3azww4fsvna605zm3d1
title: Write docs/agent-repair.runbook.md
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies:
  - type: blocks
    target: is-01m184v3tye1c77f0mmzfr5fnf
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:34:14.879Z
updated_at: 2026-08-30T01:47:03.212Z
closed_at: 2026-08-30T01:47:03.211Z
close_reason: "Wrote docs/agent-repair.runbook.md with a committed, runnable harness under tests/manual/agent-repair/ (contract, prose form-runbook, template, and the driver/evaluate/feedback/summarize scripts, all ruff-clean). Four phases: templated authoring, prose authoring, the feedback loop, and the truncated-fence regression case, plus expected results and the four failure modes that bite."
resolution: null
duplicate_of: null
---
A manual end-to-end runbook that drives a real low-thinking model at the repair feature
and shows both halves of it working: what repair fixes silently, and what it reports
for the agent to fix.

Audience: a maintainer validating a release, or anyone deciding whether `--repair` earns
its place in their pipeline. It is a manual runbook, not a CI test — it needs a
`GOOGLE_API_KEY` and makes live model calls.

Shape, following docs/e2e-testing.runbook.md:

- What it proves and what it costs (one API key, ~12 calls per phase, a few minutes).
- Phase 0: the contract, the runbook prose, and the template the agent sees. The agent
  must never see the JSON Schema — that is what makes field-name drift real rather than
  planted.
- Phase 1: templated authoring. Expect scalar drift and expect `--repair` to fix it
  unaided, with the `rubric_version: 1.10` trailing zero surviving.
- Phase 2: prose authoring. Expect near-miss field names, expect repair to decline to
  rename them, and expect paired `undeclared_property`/`missing_property` records.
- Phase 3: the feedback loop. Hand the records back to the same model and show it
  reaching valid. Warn explicitly not to truncate the record list — an earlier run
  scored 9 of 12 purely because the harness capped the list at 60 records.
- Phase 4: the regression case from the E2E review — a document whose fence is opened
  and never closed must be reported unreadable by both `validate` and `--check-repair`.
- Expected results with real numbers from the recorded run, and the failure modes worth
  knowing (nested ```markdown/```yaml fences at higher thinking budgets; thought parts
  in the response; prompt ambiguity about the `---` delimiters).

Note that thinking budget barely moves field-name drift: 0 versus 4096 gave 880 versus
747 errors with the same substitution dominating. The lever is naming fields in the
prose exactly as the schema declares them.
