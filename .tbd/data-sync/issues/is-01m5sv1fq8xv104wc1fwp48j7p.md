---
type: is
id: is-01m5sv1fq8xv104wc1fwp48j7p
title: "PR #64 D7: drop AGENTS.md from the sdist include"
kind: chore
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:05.479Z
updated_at: 2026-10-25T16:25:57.630Z
closed_at: 2026-10-25T16:25:57.630Z
close_reason: "Fixed in 29e50a8 (PR #64): AGENTS.md removed from [tool.hatch.build.targets.sdist] include; uv build --sdist verified the archive no longer contains it; the release-candidate sdist smoke (--version, docs spec) does not read it."
resolution: null
duplicate_of: null
---
Low. pyproject.toml [tool.hatch.build.targets.sdist]; check release-candidate CI job.
