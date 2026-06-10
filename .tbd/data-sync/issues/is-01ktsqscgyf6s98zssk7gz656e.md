---
type: is
id: is-01ktsqscgyf6s98zssk7gz656e
title: "P2: Expand shared golden corpus with edge-case fixtures"
kind: task
status: in_progress
priority: 1
version: 8
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqsctqjmexdppec8ddj8rj
  - type: blocks
    target: is-01ktsqsddy9k9d60d4vehwcfkv
  - type: blocks
    target: is-01ktsqsdqeadg067hwcw146k2m
  - type: blocks
    target: is-01ktsqse33ggwht7pgjaszfb31
  - type: blocks
    target: is-01ktsqseetr99vdw14kcb8888b
  - type: blocks
    target: is-01ktsqsexjfpcr1t1j2m7q9jdx
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:34.270Z
updated_at: 2026-06-10T22:11:31.930Z
---
FILE SCOPE: tests/golden/scenarios*/, tests/golden/fixtures/.
Add scenarios/fixtures (same files run by both CLIs wherever possible): non-ASCII frontmatter values; empty and whitespace-only frontmatter; unterminated fence; deeply nested validation-error paths; max-side keywords (maxLength, maxItems, pattern, exclusiveMaximum); a pure-yaml profile scenario; per-impl semantic (--model) scenarios with identical output; at least one full (un-elided) 'docs <topic>' content check. These fixtures must EXPOSE the known divergences for the next bead to close. Follows golden-testing-guidelines (full output, stable fields literal).
