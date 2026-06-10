---
type: is
id: is-01ktqkdym0xvxs3t06wr34kden
title: Document softschema skill mirror fan-out policy
kind: task
status: open
priority: 3
version: 1
labels:
  - skill
  - docs
dependencies: []
created_at: 2026-06-10T01:47:56.415Z
updated_at: 2026-06-10T01:47:56.415Z
---
Developer feedback: `.agents/skills/softschema/SKILL.md` and `.claude/skills/softschema/SKILL.md` are byte-identical full copies today. That is fine for two targets, but the project should document the intended model before adding more agent targets: keep full generated copies for portability, use symlinks where supported, or make `.agents/skills` canonical and explain how mirrors reference it. Capture the decision in docs or package design and keep mirror drift tests aligned with the chosen model.
