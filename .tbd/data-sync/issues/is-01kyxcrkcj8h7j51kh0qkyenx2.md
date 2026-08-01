---
type: is
id: is-01kyxcrkcj8h7j51kh0qkyenx2
title: Publish and verify softschema v0.4.0
kind: task
status: closed
priority: 1
version: 7
spec_path: docs/project/specs/active/plan-2026-07-31-softschema-v040-release.md
labels:
  - release-v0.4.0
dependencies: []
parent_id: is-01kyxcr75ap5xpcsm46p8edsq7
created_at: 2026-08-01T00:49:39.217Z
updated_at: 2026-08-01T03:08:56.668Z
closed_at: 2026-08-01T03:08:56.667Z
close_reason: "Complete: v0.4.0 tag, GitHub release, PyPI/npm OIDC publication, byte-level registry verification, exact installs, published quickstarts, and final evidence all succeeded."
---
Commit and push release preparation, wait for main CI, create and push the v0.4.0 tag, monitor publication through both registries, verify GitHub release notes and assets, run post-publish registry and quickstart smokes, then record evidence and sync tracking.

## Notes

Published v0.4.0 end to end. PR #24 merged as c81e4a6; annotated tag v0.4.0 (d311365) peels to that commit; release https://github.com/jlevy/softschema/releases/tag/v0.4.0; publish run 30681078342 passed candidate build/smoke plus both OIDC jobs. Registry bytes equal workflow candidates: wheel a42d8e74703aa1cbd3aaff93e81a6eee73218f7c4b53aa0c319169775175571c, sdist bd8f59b4fa52263091fd7cc5de4319f94af22ba986148023598ce0f0e5291b90, npm 740992b3d09d0d1601d596952a223ba1c46d886169d1142e8e250bcb25f7df97. Exact installs, dependency floors, audits, paired quickstart byte parity, and timestamp-string parity passed. Final evidence PR #25 merged as bd791a4.
