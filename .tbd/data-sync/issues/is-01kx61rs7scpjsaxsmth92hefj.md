---
type: is
id: is-01kx61rs7scpjsaxsmth92hefj
title: Bound recovery extraction depth and implicit directories before writes
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:59:17.112Z
updated_at: 2026-07-10T13:09:03.260Z
closed_at: 2026-07-10T13:09:03.259Z
close_reason: Recovery extraction now preflights MAX_RECOVERY_DEPTH and a unique implied-directory plus file node budget before archive-driven writes; deep and sparse-parent regressions pass.
---
Before mkdir or extraction, enforce MAX_RECOVERY_DEPTH on tar member paths and budget every unique implied parent directory against the extraction node limit. Add malicious deep-path and sparse-parent regression archives.
