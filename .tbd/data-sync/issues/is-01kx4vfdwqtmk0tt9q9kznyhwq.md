---
type: is
id: is-01kx4vfdwqtmk0tt9q9kznyhwq
title: Align TypeScript runtime contracts, model loading, CLI exits, and wire types
kind: feature
status: closed
priority: 2
version: 12
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - typescript
  - api
  - cli
  - parity
dependencies:
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx62r2xrvqzg0518h4q1z4hg
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
child_order_hints:
  - is-01ksrxy9by354mapnjhdgm7zpv
created_at: 2026-07-10T01:50:04.694Z
updated_at: 2026-07-10T13:16:31.655Z
closed_at: 2026-07-10T08:24:34.060Z
close_reason: Implemented and verified in 0e4b404
---
Separate serializable contract descriptors from runtime Zod bindings without breaking 0.2 callers, document and enforce the Node versus Bun model-module policy, normalize Commander usage exits with Python, and replace Record<string, unknown> result surfaces with typed wire contracts.

## Notes

Architecture decision: softschema/core is transitively runtime-neutral, softschema/node is the explicit adapter, and the existing root remains a documented one-minor Node/Bun compatibility facade. Require transitive dependency and exact-export guards plus typed wire contracts, runtime binding separation, exit parity, and Windows-safe imports.

Implementation checkpoint (uncommitted): added exact portable ContractDescriptor plus deprecated Contract aliases; Node-only RuntimeContract/bindContract and preferred validateArtifact overload; named conformance wire/error/result types; runtime-aware Node .js/.mjs versus Bun .ts model loader with encoded POSIX/Windows paths; Commander usage exit 2; declarations/docs/golden coverage. Verified bun run check (439 tests, 95.86% functions/97.26% lines), build, publint, npm pack dry-run, all Python/Node/Bun golden suites, and cross-implementation byte parity. Full repo Python lint currently has a transient failure in concurrent ss-o21w test_release.py work.
