---
type: is
id: is-01kyxcrk53jy00ree16s3ed202
title: Run v0.4.0 release candidate validation
kind: task
status: closed
priority: 1
version: 8
spec_path: docs/project/specs/done/plan-2026-07-31-softschema-v040-release.md
labels:
  - release-v0.4.0
dependencies: []
parent_id: is-01kyxcr75ap5xpcsm46p8edsq7
created_at: 2026-08-01T00:49:38.978Z
updated_at: 2026-08-01T03:09:09.427Z
closed_at: 2026-08-01T02:07:20.567Z
close_reason: "Completed on release commit e21f309: exact frontmatter-format 0.4.0 adoption, fast-uri 3.1.4 security hardening with approved exception, and full local release validation all passed."
---
Run the full automated sweep, clean wheel and npm tarball installs, docs-as-written quickstart, agent skill bootstrap, and release metadata checks from the repository runbook.

## Notes

Final local release matrix passed on the final locks: Python lint/types and 167 tests; TypeScript 171 tests at 96.06% functions/96.35% lines; Python/Node/Bun goldens 38/36/38; 20 direct parity comparisons; builds and publint; Python, Bun, and clean npm audits; exact v0.4.0 wheel/sdist/npm installs; README quickstart byte parity; skill bootstrap. Candidate SHA-256: wheel 97a039d94328835284de990b13e56ed858b44bcebfe908b7a7cf106618cb63c7, sdist 338fa9869ec23dff8928c7aac045132321bbaf52de234f0f470a65e581429078, npm 740992b3d09d0d1601d596952a223ba1c46d886169d1142e8e250bcb25f7df97.
