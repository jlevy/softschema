---
type: is
id: is-01kx6ngnzq2wvb4j39evqcrjs0
title: Use fresh Windows 3.11 candidate file identity
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
  - windows
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T18:44:23.159Z
updated_at: 2026-07-10T18:46:57.360Z
closed_at: 2026-07-10T18:46:57.360Z
close_reason: Used fresh path lstat identity for candidate inventory and added a cached-DirEntry regression; full Python suite passes.
---
Python 3.11 documents that Windows DirEntry.stat returns zero st_dev/st_ino fields. The frozen candidate inventory retained that cached snapshot and then compared it with a descriptor snapshot, causing the Windows 3.11 checksum/junction gate to fail and preventing exact verification. Use a fresh path lstat for inventory identity and keep a regression that forbids cached DirEntry stat.
