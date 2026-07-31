---
type: is
id: is-01kyx92x7k2x1ht64n0r3gr05f
title: Document the minor-release migration and agent guidance
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - release-content
dependencies:
  - type: blocks
    target: is-01kyx93bh11rmrma1zvkh6m2gy
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:45:22.674Z
updated_at: 2026-07-31T23:48:38.039Z
closed_at: 2026-07-31T23:48:38.038Z
close_reason: "Migration and release content are complete: source and managed skills are byte-identical, reviewed Python goldens pass, and the changelog records the v0.3 baseline plus the v0.4-compatible upgrade path."
---
Update Unreleased notes with the user-visible input expansion, unchanged quoted values, portable string results, annotation-only format policy, and possible one-time Zod sidecar drift. Restore the missing v0.3.0 changelog entry from release history. Add a concise operating rule to the source softschema skill, regenerate both managed project mirrors, and update the reviewed skill --brief golden. Acceptance: no artifact rewrite or migration command is prescribed; agents are told to reinstall mirrors, validate corpora, use semantic models or explicit assertions, and regenerate only affected Zod sidecars.

## Notes

Migration notes, changelog history, source skill, managed mirrors, and the reviewed operating-brief golden are implemented; verifying generated-content and golden ownership.
