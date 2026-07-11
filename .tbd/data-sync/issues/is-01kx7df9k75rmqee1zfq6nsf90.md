---
type: is
id: is-01kx7df9k75rmqee1zfq6nsf90
title: Preserve exact CLI example bytes in artifact smoke
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - ci
  - windows
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-11T01:43:03.526Z
updated_at: 2026-07-11T01:45:16.639Z
closed_at: 2026-07-11T01:45:16.638Z
close_reason: Verified bundled schema topic and wrote Python/npm CLI examples as exact UTF-8 bytes; focused tests, full 779-test suite, lint, and real frozen artifact smoke pass.
---
Windows artifact smoke rewrites CLI example output through text-mode Path.write_text before validation, changing platform bytes and causing the installed schema round trip to fail. Verify the bundled schema output and materialize CLI output as exact UTF-8 bytes for Python and npm smoke paths.
