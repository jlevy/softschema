---
type: is
id: is-01kx6ngnzq2wvb4j39evqcrjs0
title: Use fresh Windows 3.11 candidate file identity
kind: bug
status: closed
priority: 1
version: 5
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
updated_at: 2026-07-10T18:52:37.297Z
closed_at: 2026-07-10T18:52:37.296Z
close_reason: Inventory now uses fresh path lstat for admission and authenticated descriptor snapshots for cross-platform stability comparisons; 775 Python tests pass.
---
Python 3.11 documents that Windows DirEntry.stat returns zero st_dev/st_ino fields. The frozen candidate inventory retained that cached snapshot and then compared it with a descriptor snapshot, causing the Windows 3.11 checksum/junction gate to fail and preventing exact verification. Use a fresh path lstat for inventory identity and keep a regression that forbids cached DirEntry stat.

## Notes

Windows 3.14 CI additionally showed path-stat and fstat timestamp representations differ. Inventory now retains authenticated descriptor metadata so all stability comparisons are descriptor-to-descriptor; path lstat remains admission/identity only.
