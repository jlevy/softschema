---
type: is
id: is-01m5rv2xtf0jn3x37svwk0e5cv
title: "After frontmatter-format 0.4.1 publishes: raise softschema's frontmatter-format floor to >=0.4.1 and move its exclude-newer-package cool-off date"
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m5rt23qna630vr0y300jnhrb
created_at: 2026-10-25T06:13:38.255Z
updated_at: 2026-10-26T01:28:56.594Z
closed_at: 2026-10-26T01:28:56.592Z
close_reason: "Done on claude/release-0.9.0 with frontmatter-format>=0.5.0, not 0.4.1: 0.4.1 was never published and 0.5.0 (PyPI, sdist uploaded 2026-10-25T20:50:58.660308Z) ships the per-instance representers. Floor and cool-off exception moved in 49a0ce7 (pyproject, Makefile, ci.yml x3; uv.lock changes only frontmatter-format 0.4.0 -> 0.5.0; PyPI hashes match the lock and the v0.5.0 tag source). a75ba0f drops the strict xfail on test_compile_leaves_ruamels_shared_safe_representer_unchanged: it passes C-first and with SOFTSCHEMA_PURE_YAML=1 under 0.5.0 and fails under 0.4.0 (shared dict representer)."
resolution: null
duplicate_of: null
---
