---
type: is
id: is-01kx6gpnxc46fqff8gsxm1atx6
title: Bound every frozen release-driver read and verify before execution
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
  - artifact
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx6makgta5bvsfx08p80kyv4
  - type: blocks
    target: is-01kx6makrt79cv7a8kntxjqqqg
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T17:20:16.810Z
updated_at: 2026-07-10T18:36:56.604Z
closed_at: 2026-07-10T18:36:56.603Z
close_reason: Bound frozen release-driver reads and enforced trusted verification before candidate execution.
---
The frozen release driver still uses racy unbounded Path.read_bytes calls for manifests, controls, subjects, and npm fixtures, and finalize-release executed a transferred helper before trusted verification. Route all reads through descriptor-bound limit-plus-one readers with explicit budgets, require exact-checkout verification before any candidate helper in every consumer, and add mutation/oversize/ordering regressions.
