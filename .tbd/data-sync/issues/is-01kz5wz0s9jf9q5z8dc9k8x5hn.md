---
type: is
id: is-01kz5wz0s9jf9q5z8dc9k8x5hn
title: "PR #27: cross-runtime parity broken in the 1000-5000 depth band"
kind: bug
status: closed
priority: 0
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wz06084fc4q0badsavagv
created_at: 2026-08-04T08:06:42.217Z
updated_at: 2026-08-04T08:15:38.740Z
closed_at: 2026-08-04T08:15:38.740Z
close_reason: MAX_DEPTH=64 restored in both runtimes; re-measured 63 valid / 64,65,200,1000 yaml_limit in both.
---
Same document: Python crashes at depth 1000 while TypeScript returns valid; TS rejects only at 50000. tests/vectors/hardening.yaml exists to make this impossible. (PR #27)
