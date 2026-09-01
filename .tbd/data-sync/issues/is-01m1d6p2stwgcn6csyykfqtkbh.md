---
type: is
id: is-01m1d6p2stwgcn6csyykfqtkbh
title: Self-identify Python and TypeScript version output
kind: bug
status: closed
priority: 2
version: 3
labels: []
dependencies: []
created_at: 2026-09-01T00:42:39.801Z
updated_at: 2026-09-01T00:50:04.202Z
closed_at: 2026-09-01T00:50:04.201Z
close_reason: "Implemented self-identifying Python and TypeScript --version output with mirrored regression coverage; PR #54 passed all CI checks."
resolution: null
duplicate_of: null
---
Make both softschema CLI implementations report the shared package version while clearly identifying whether the running implementation is Python or TypeScript. Add mirrored regression coverage for the version flag/output.
