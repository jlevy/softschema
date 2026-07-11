---
type: is
id: is-01kx7s4hfwaw78r56phwekh5qs
title: Reject boolean conformance limit values in JavaScript
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - review
  - parity
  - conformance
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-11T05:06:54.075Z
updated_at: 2026-07-11T05:12:13.328Z
closed_at: 2026-07-11T05:12:13.327Z
close_reason: Made JavaScript numeric type guard explicit, added shared Python/Node/Bun invalid-request coverage, refreshed kit integrity, and passed full suites.
---
Address PR #20 thread PRRT_kwDOSmMwds6QDd0y: JavaScript validateLimitFields must reject boolean values exactly like Python, with a shared invalid-request regression exercised by Node/Bun and Python.
