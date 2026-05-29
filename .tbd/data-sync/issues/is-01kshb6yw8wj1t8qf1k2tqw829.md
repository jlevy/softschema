---
type: is
id: is-01kshb6yw8wj1t8qf1k2tqw829
title: Restructure docs/softschema-guide.md as operational playbooks
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies:
  - type: blocks
    target: is-01kshb8ac11et3tw1cxxjg2dgf
parent_id: is-01kshb5636qx5g9ha5xaa6b5qb
created_at: 2026-05-26T05:13:10.279Z
updated_at: 2026-05-26T05:53:12.646Z
closed_at: 2026-05-26T05:53:12.644Z
close_reason: completed
---
Per review Finding 4. The guide is currently more concept reference than playbook. Restructure around common workflows the reader actually needs:

- Adopt softschema for an existing Markdown artifact
- Decide which values belong in YAML
- Choose inline frontmatter vs a data sidecar
- Write a contract ID
- Add Python validation
- Validate in CI
- Migrate a non-canonical existing artifact
- Use softschema with agents
- Know when to stop and leave prose as prose
- Common Mistakes
- Relationship To The Python Package

Carry enough rationale to help readers decide, but NOT the full roadmap or future architecture (those stay in the plan).

Consolidates four existing beads — decide whether to keep them separate playbook subtasks of this work or close them in favor of this consolidated effort:
- ss-0cz4 [P1] Lifecycle/continuum walkthrough in guide
- ss-ow97 [P1] Inline-vs-sidecar doctrine in guide
- ss-91vh [P1] Migration recipe (legacy envelope to canonical)
- ss-4e4s [P1] CI integration recipe in development docs

Recommendation: keep the existing beads as concrete children of this restructure, since each contains specific content guidance.
