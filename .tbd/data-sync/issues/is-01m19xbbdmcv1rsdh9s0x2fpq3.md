---
type: is
id: is-01m19xbbdmcv1rsdh9s0x2fpq3
title: "Golden: refresh inspect-and-docs, the corpus README, and cross-impl-diff"
kind: task
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:47.700Z
updated_at: 2026-08-30T18:01:47.700Z
---
- tests/golden/scenarios/inspect-and-docs.tryscript.md asserts the skill text BYTE-FOR-BYTE, so any edit to skills/softschema/SKILL.md breaks it. Update after the skill bead lands.
- tests/golden/README.md has a scenario responsibility table naming validate-repair.tryscript.md; update the row for the rename.
- tests/golden/cross-impl-diff.sh: consider adding a repair case, since it currently compares no repair output at all between implementations.
