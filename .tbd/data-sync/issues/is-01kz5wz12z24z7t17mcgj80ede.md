---
type: is
id: is-01kz5wz12z24z7t17mcgj80ede
title: "PR #27: CI red - stale depth vectors in tests/vectors/hardening.yaml"
kind: bug
status: closed
priority: 0
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wz06084fc4q0badsavagv
created_at: 2026-08-04T08:06:42.527Z
updated_at: 2026-08-04T08:15:39.011Z
closed_at: 2026-08-04T08:15:39.010Z
close_reason: All five depth vectors correct again with the rule restored; 167 pytest and 171 bun test green.
---
build (ubuntu-latest, 3.12) fails test_shared_portable_yaml_vectors on depth_64. Python 166 pass/1 fail; TS 170 pass/1 fail. (PR #27)
