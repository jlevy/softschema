---
type: is
id: is-01kx670z3q4dppv2xp9s7n38e1
title: Reject non-regular nodes in frozen candidate inventories
kind: bug
status: closed
priority: 1
version: 10
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
  - artifact
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx6gpnxc46fqff8gsxm1atx6
  - type: blocks
    target: is-01kx6makgta5bvsfx08p80kyv4
  - type: blocks
    target: is-01kx6ngnzq2wvb4j39evqcrjs0
  - type: blocks
    target: is-01kx7dqzt6q0sh4n4pxfjx9qj2
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T14:31:08.150Z
updated_at: 2026-07-11T01:49:46.325Z
closed_at: 2026-07-10T18:36:55.881Z
close_reason: Implemented exact regular-node frozen inventory verification with swap and special-node coverage.
---
The transferred verifier skips unexpected FIFOs and other non-regular filesystem nodes because inventory enumeration accepts only regular files. Exact frozen-candidate verification must classify every node without opening it, reject anything not declared and regular, and prove FIFOs cannot block or survive verification.

## Notes

Verifier now lstat-classifies every node; rejects symlinks, non-regular nodes, fake/empty directories, empty/oversized/non-UTF-8 inventories; streams hashes and checksum bytes through descriptor-bound regular-file checks. POSIX verification traverses candidate parents with openat + O_DIRECTORY/O_NOFOLLOW; fallback re-lstats every parent; device/inode identity and a final inventory pass detect swaps. Exact final-file and intermediate-parent symlink swap exploits are regressions. Focused 6 tests plus lint/typecheck pass.
