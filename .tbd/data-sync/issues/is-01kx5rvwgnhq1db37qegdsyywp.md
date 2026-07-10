---
type: is
id: is-01kx5rvwgnhq1db37qegdsyywp
title: Harden conformance publication and standalone JSON boundaries
kind: bug
status: closed
priority: 2
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - conformance
  - security
dependencies:
  - type: blocks
    target: is-01kx5v1ydg4ezt3pqwzhyvb61g
  - type: blocks
    target: is-01kx5s2jtk3p7hpympsq3gt07s
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx61kkznyp5d0pn9whrd28pr
  - type: blocks
    target: is-01kx5ykt9xyxf53p1g1dmfhhfz
  - type: blocks
    target: is-01kx64djnhdw2q7x5eg26j66vy
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T10:23:41.588Z
updated_at: 2026-07-10T13:45:54.395Z
closed_at: 2026-07-10T11:51:34.188Z
close_reason: Hardened publication/consumer/adapter boundaries, exact output inventories, confined paths, strict bounded JSON, and live-index verification; hostile tests pass.
---
Red-team the draft conformance publication and standalone consumer boundaries: validate canonical unique source IDs/names and the final index before writes/deploy; refuse output symlink escapes and undeclared kit nodes; bound strict JSON config/schema/index/lock reads and counts; translate deep nesting and oversized integer parse failures deterministically; and cover hostile fixtures before regenerating the integrity lock.
