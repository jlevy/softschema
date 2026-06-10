---
type: is
id: is-01ktqkd1sgfem2nk4f4evp76sm
title: Add softschema doctor or env runtime probe
kind: feature
status: open
priority: 2
version: 1
labels:
  - cli
  - agents
dependencies: []
created_at: 2026-06-10T01:47:26.895Z
updated_at: 2026-06-10T01:47:26.895Z
---
Developer feedback: agents currently have to manually probe `softschema`, `uvx`, and `npx` to decide how to invoke the tool. Add a deterministic `softschema doctor` or `softschema env` command that reports the installed version, available runners, and recommended invocation in text and JSON. This should collapse runtime detection into one command the skill can call first. Keep Python and TypeScript behavior in parity and include failure-path tests.
