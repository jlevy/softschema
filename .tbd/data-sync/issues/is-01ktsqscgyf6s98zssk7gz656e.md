---
type: is
id: is-01ktsqscgyf6s98zssk7gz656e
title: "P2: Expand shared golden corpus with edge-case fixtures"
kind: task
status: closed
priority: 1
version: 12
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
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
updated_at: 2026-07-10T03:49:15.919Z
closed_at: 2026-06-10T22:27:25.727Z
close_reason: null
---
Complete CLI golden coverage: one tryscript corpus run against BOTH CLIs covering every command, flag, and user-error exit path. Follows golden-testing-guidelines (full output, no surgical extraction, patterns only for genuinely variable fields like the version string) and tryscript best practices. Covers validate (ok/structural-fail/overrides/envelope_mismatch), the exit-2 user errors Phase 1 made parity-clean (missing file, malformed frontmatter, malformed metadata, unknown topic, ambiguous envelope, missing impl) asserting exit+empty-stdout where stderr wording is engine-specific, inspect variants, docs <topic>/--json/unknown-topic, skill and skill --brief, generate and generate --check drift, --version with [VERSION] pattern, and per-impl --model semantic-ok scenarios. FUNDAMENTAL stability net; blocks all Phase 3 design beads. Edge-case fixtures + divergence-closing tracked separately (ss-3iz5).
