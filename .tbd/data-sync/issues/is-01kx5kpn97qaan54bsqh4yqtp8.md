---
type: is
id: is-01kx5kpn97qaan54bsqh4yqtp8
title: Make deterministic JSON serialization byte-identical across runtimes
kind: bug
status: closed
priority: 1
version: 7
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - serialization
  - typescript
dependencies:
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
  - type: blocks
    target: is-01kx5pdepc8ct3g1bjgnas3wp9
  - type: blocks
    target: is-01kx5zjhrha1r5wkdjq66gseth
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T08:53:27.462Z
updated_at: 2026-07-10T13:10:42.171Z
closed_at: 2026-07-10T11:51:31.808Z
close_reason: Implemented portable canonical JSON serialization; adversarial vectors, goldens, and direct Python/Node byte parity pass.
---
Replace the TypeScript sort-then-JSON.stringify implementation with a runtime-neutral serializer that matches Python json.dumps(sort_keys=True, ensure_ascii=False) for the portable value domain. Cover Unicode code-point ordering, integer-like keys that JavaScript otherwise reorders, compact/pretty output, normalized finite-number spelling, schema hashes, legacy CLI output, diagnostic JSON/JSONL, and shared cross-runtime vectors without changing ordinary existing bytes.
