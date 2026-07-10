---
type: is
id: is-01ktsqth49tm7v2s5avwfjrejb
title: "P4: TS library polish (Ajv caching; node-free entry decision + ./cli export; readFrontmatter export)"
kind: task
status: closed
priority: 3
version: 3
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:43:11.752Z
updated_at: 2026-06-11T06:33:21.377Z
closed_at: 2026-06-11T06:33:21.377Z
close_reason: null
---
FILE SCOPE: validate.ts, package.json, index.ts.
- Cache the Ajv instance / compiled validators by schema (validateStructural rebuilds per call; primary library use is many artifacts against one contract).
- Decide node-free '.' entry vs documented Node-only posture; add a './cli' export entry.
- Resolve the half-exported readFrontmatter (export from index as public API or mark @internal).
Refs review TS 3.1, 5.2, 2.6.
