---
type: is
id: is-01kx4scemwng8g758svkrcdnh9
title: Repair and simplify user and agent documentation
kind: task
status: closed
priority: 2
version: 16
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - agents
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx5fvvr8jfgg5bf70vr9h5kj
  - type: blocks
    target: is-01kx61reqsfpmcq0g2nzrz8mj0
  - type: blocks
    target: is-01kx62r2xrvqzg0518h4q1z4hg
  - type: blocks
    target: is-01kx64djwdf2rppmq5gv8qfs1t
  - type: blocks
    target: is-01kx6mdsmq79qctgr6q2e4cm3m
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:30.011Z
updated_at: 2026-07-10T18:25:25.233Z
closed_at: 2026-07-10T11:51:34.731Z
close_reason: Reorganized and verified public docs, paired examples, migration/changelog/security material, claims checks, and major coding-agent skill/instruction compatibility.
---
Reorganize README/guide/spec/design docs under common prose guidance; add paired Python/TypeScript examples, CHANGELOG and migration notes, executable public-claims checks, and dated primary-source alternatives research. Publish tested Codex/Claude/Gemini/Copilot/Cursor/Windsurf/OpenCode/Aider/Cline-Roo compatibility plus verified native/generated instruction shims.

## Notes

Implemented the public docs and agent hardening pass: compact README; task-oriented guide/spec/API/migration/security/changelog; paired Python/Zod model and host examples; evidence-calibrated ten-agent compatibility; AGENTS-derived shims; progressive-disclosure skill and safe-install guidance; machine-checked public claims; registry-safe package README links; current release DAG runbook; compiler-owned root x-softschema and portable Unicode/frontmatter fence rules. Evidence: public docs/footer/link/claims/compiler-fence 30 passed; Python skill/mirror/resources 31 passed; TypeScript docs/bootstrap/movie/API 50 passed plus tsc; skill-creator validates source and both mirrors; nine-target dry-run/install/idempotence/non-clobber smoke passed; installed wheel-from-sdist/npm artifact smoke passed; devtools/lint.py --check passed; public claims 14 claims/18 targets. Hosted conformance IDs intentionally remain draft pending exact namespace publication verification.
