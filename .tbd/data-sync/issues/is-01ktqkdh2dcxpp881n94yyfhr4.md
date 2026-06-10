---
type: is
id: is-01ktqkdh2dcxpp881n94yyfhr4
title: Prevent softschema skill brief drift from canonical SKILL.md
kind: task
status: open
priority: 2
version: 1
labels:
  - skill
  - tests
dependencies: []
created_at: 2026-06-10T01:47:42.539Z
updated_at: 2026-06-10T01:47:42.539Z
---
Developer feedback: `_brief_skill_text()` in the Python CLI and the TypeScript `SKILL_BRIEF` literal duplicate operating rules from `skills/softschema/SKILL.md`. Either derive the brief from a marked region in the canonical skill source or add tests asserting the brief rules are a subset of the full skill. Preserve the CLI-as-skill pattern: the full SKILL.md remains canonical, mirrors remain generated, and both implementations print equivalent brief guidance.
