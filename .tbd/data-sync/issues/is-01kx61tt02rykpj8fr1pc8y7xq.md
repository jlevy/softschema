---
type: is
id: is-01kx61tt02rykpj8fr1pc8y7xq
title: Authenticate recovery checksums before parsing them
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
created_at: 2026-07-10T13:00:23.425Z
updated_at: 2026-07-10T13:09:03.447Z
closed_at: 2026-07-10T13:09:03.446Z
close_reason: Recovery checksum inventory now has its own attestation, is verified before parsing, is restricted to exactly the two relative recovery filenames, and is reverified after extraction; malicious filename regression passes.
---
Do not pass mutable draft release checksum contents to sha256sum before authenticity validation. Attest the checksum asset itself with exact workflow/ref/source-digest and verify it before parsing, or use an equivalently frozen strict parser. Cover absolute/traversal filenames and blocking device targets.
