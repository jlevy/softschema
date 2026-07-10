---
type: is
id: is-01kx6p8va76ncy6ab172ash0gx
title: Force UTF-8 in installed-artifact smoke subprocesses
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - windows
  - packaging
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T18:57:35.046Z
updated_at: 2026-07-10T19:01:49.299Z
closed_at: 2026-07-10T19:01:49.298Z
close_reason: Forced UTF-8 Python subprocess streams and added a real Unicode child-process regression; frozen cold smoke passes.
---
Windows Python CLIs inherit the active console code page, so installed-artifact smoke decoded bundled Unicode guide output as UTF-8 and failed with byte 0x92. Force PYTHONIOENCODING=utf-8 and PYTHONUTF8=1 for every smoke subprocess and prove a real child prints a non-ASCII punctuation mark under a hostile inherited ASCII setting.
