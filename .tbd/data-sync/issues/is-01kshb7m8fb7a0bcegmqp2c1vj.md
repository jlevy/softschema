---
type: is
id: is-01kshb7m8fb7a0bcegmqp2c1vj
title: Update README, AGENTS.md, SKILL.md, CLI topics after design-doc decision
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
created_at: 2026-05-26T05:13:32.174Z
updated_at: 2026-05-26T05:53:11.523Z
closed_at: 2026-05-26T05:53:11.514Z
close_reason: completed
---
Blocked by ss-wut9 (design-doc fate decision). Specifics depend on the decision, but the work surfaces:

1. README.md line 125: 'guide, spec, design, and workflow docs' — update to match the surviving doc set.
2. README.md line 138-144 Docs links: verify Python Package Design link is present and no orphaned Softschema Design link.
3. AGENTS.md lines 14: confirms only python-design is referenced. Already aligned.
4. skills/softschema/SKILL.md: verify no reference to the deleted file.
5. packages/python/src/softschema/cli.py: bundled docs already only reference softschema-python-design.md (line 44). Verify after the design-doc removal.
6. docs/softschema-python-design.md companions table at the top: drop the row for the deleted file.
7. Find every reference to clean up:
   rg 'softschema-design|Softschema Design|durable design reference' .

Trivial work once the decision lands, but explicit because the wording leaks into multiple files.
