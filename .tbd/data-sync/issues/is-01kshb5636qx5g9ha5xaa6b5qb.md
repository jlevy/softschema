---
type: is
id: is-01kshb5636qx5g9ha5xaa6b5qb
title: Address codex review of standalone docs+design organization
kind: task
status: closed
priority: 1
version: 10
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies: []
child_order_hints:
  - is-01kshb5jkpcg4zf37hd1k89ey4
  - is-01kshb5xk61cvpc18r7tk88n12
  - is-01kshb69gjwxqeter8bt3vbg87
  - is-01kshb6k5nqgyvs71hh2e83dpp
  - is-01kshb6yw8wj1t8qf1k2tqw829
  - is-01kshb7m8fb7a0bcegmqp2c1vj
  - is-01kshb7zwjhyehkvwq9x9v9gc3
  - is-01kshb8ac11et3tw1cxxjg2dgf
created_at: 2026-05-26T05:12:12.132Z
updated_at: 2026-05-26T05:53:13.751Z
closed_at: 2026-05-26T05:53:13.750Z
close_reason: completed
---
Address the 2026-05-26 codex review (docs/project/reviews/review-2026-05-26-softschema-docs-design.md) of the standalone repo's documentation and design organization.

Main thesis: docs/softschema-design.md conflicts with the active public-readiness plan (plan-2026-05-24-softschema-public-readiness.md says not to add a standalone language-neutral design doc for now). Remove it before public release, then restructure the guide as operational playbooks, tighten the spec to normative-only, and update README/AGENTS.md/SKILL.md/CLI to match.

The review aligns with the trading consumer plan (aisw/trading/docs/project/specs/active/plan-2026-05-24-softschema-open-source-adoption.md): same public doc shape, same one-envelope artifact, same status taxonomy. The trading plan also surfaces a seam consideration: it drafted SchemaBinding/Status names, while the current package exports SoftschemaBinding/SoftschemaStatus — confirm before the trading cutover.

Children break down decisions (blocking) and concrete cleanup work. Existing beads ss-0cz4, ss-ow97, ss-91vh, ss-4e4s overlap with the guide-restructure work and should be folded together.
