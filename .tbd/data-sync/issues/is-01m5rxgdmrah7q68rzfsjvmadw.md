---
type: is
id: is-01m5rxgdmrah7q68rzfsjvmadw
title: "PR #64 A3: compile still mutates ruamel's shared SafeRepresenter via frontmatter_format.new_yaml; CHANGELOG overclaims"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxgc8kdy9fz5wgg3ew5vsq
hold: null
hold_until: null
created_at: 2026-10-25T06:55:57.592Z
updated_at: 2026-10-25T07:12:33.271Z
started_at: 2026-10-25T06:56:43.041Z
closed_at: 2026-10-25T07:12:33.271Z
close_reason: "fixed (CHANGELOG) in ce14939: sentence narrowed to the repair emitter; strict xfail guard test_compile_leaves_ruamels_shared_safe_representer_unchanged pins the compile-side leak and activates with the frontmatter-format>=0.4.1 bump (ss-c9bc, this release)."
resolution: null
duplicate_of: null
---
Medium, pre-existing. packages/python/src/softschema/compile.py:171, CHANGELOG.md:17-18. Narrow CHANGELOG; root cause fixed by frontmatter-format 0.4.1 (ss-c9bc).
PR #64. Review A: https://github.com/jlevy/softschema/pull/64#pullrequestreview-5641911619
