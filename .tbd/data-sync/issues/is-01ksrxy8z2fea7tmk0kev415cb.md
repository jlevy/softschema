---
type: is
id: is-01ksrxy8z2fea7tmk0kev415cb
title: "[deferred] Add NO_COLOR/CI env handling if colored CLI output ships"
kind: task
status: open
priority: 3
version: 1
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:55:09.665Z
updated_at: 2026-05-29T03:55:09.665Z
---
Audit P2.18. python-cli-patterns / cli-agent-skill-patterns recommend honoring NO_COLOR and CI env vars. Currently the CLI emits no color, so this is theoretical. If a later release adds Rich-based or otherwise styled output, add the env-var handling alongside it.
