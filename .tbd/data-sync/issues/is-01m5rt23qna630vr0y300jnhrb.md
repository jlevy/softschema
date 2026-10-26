---
type: is
id: is-01m5rt23qna630vr0y300jnhrb
title: "Release softschema after #59/#60/#62/#64 merge (bump frontmatter-format if needed, changelog, publish PyPI+npm)"
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-10-25T05:55:42.964Z
updated_at: 2026-10-26T01:43:24.855Z
closed_at: 2026-10-26T01:43:24.855Z
close_reason: "Released softschema 0.9.0: https://github.com/jlevy/softschema/releases/tag/v0.9.0 at 8085986 (main CI 20/20). Publish run 40255278104: build, smoke, PyPI and npm all success (npm provenance logged to sigstore). Verified: uvx softschema@0.9.0 --version -> 'softschema 0.9.0 (Python)'; npx softschema@0.9.0 --version -> 'softschema 0.9.0 (TypeScript)'. Requires frontmatter-format>=0.5.0 (released v0.5.0)."
resolution: null
duplicate_of: null
---

## Notes

Version decision (PR #64 round 2, B3): cut this release as 0.9.0, a minor bump. The portable preflight (raw control/line-separator characters and lone CR rejected in both runtimes) is a normative spec tightening, and documents that validated under 0.8.1 can now be refused. CHANGELOG.md has a Compatibility section with the per-runtime list of newly rejected input, the escapes, an rg command to find affected files, and the message/kind changes. Depends on ss-c9bc (frontmatter-format 0.4.1 floor) per review B7; if the release goes first, add a known-issue line for the compile representer leak instead.
