---
type: is
id: is-01kyxhhh0kytcjcrqrf42hhw88
title: "PR #24 review R1: pass uv cool-off exceptions in make install"
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/done/plan-2026-07-31-softschema-v040-release.md
labels: []
dependencies: []
parent_id: is-01kyxhhawjbbekecccfyn08s5e
created_at: 2026-08-01T02:13:10.290Z
updated_at: 2026-08-01T03:09:10.896Z
closed_at: 2026-08-01T02:55:17.106Z
close_reason: "Complete: commit 569340d fixed local uv cool-off parity; failure-case and full-suite validation passed; final CI is green and the PR thread is resolved."
---
PR #24 Cursor Bugbot medium finding at Makefile:25-27: when UV_EXCLUDE_NEWER is set, uv replaces the project per-package map, so make install must repeat the reviewed frontmatter-format and strif exceptions just as CI does. Add the flags, verify the global-env case, and update release evidence.

## Notes

R1 fixed locally. Makefile now defines a frozen, no-config UV_SYNC with the fixed project cutoff plus exact frontmatter-format and strif exceptions; lint and test also use the existing frozen no-config UV_RUN. Red reproduction showed plain make install omitted flags. Green reproduction with UV_EXCLUDE_NEWER='14 days' passed, kept uv.lock unchanged, and installed frontmatter-format 0.4.0. Full Python/TypeScript/golden/parity sweep passed; exact v0.4.0 wheel/sdist/npm candidates rebuilt and sdist installed.
