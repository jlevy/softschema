---
type: is
id: is-01m19xca07vajnjj9f5p9sgy6c
title: "Docs: forward-link the superseded 2026-08-29 repair plan"
kind: chore
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:19.014Z
updated_at: 2026-08-30T18:02:19.014Z
---
docs/project/specs/active/plan-2026-08-29-validate-repair.md describes the --repair/--check-repair surface as implemented. Add a dated status note and a forward link to plan-2026-08-30-repair-command.md. Do NOT rewrite its body -- it records what was true.

The v0.8.0 readiness review already flags that this plan's placement in active/ rather than done/ deserves a deliberate call; make that call while here.

Also do not touch docs/project/reviews/** at all: historical records legitimately name the retired flags, and the enforcement lint must exempt that directory.
