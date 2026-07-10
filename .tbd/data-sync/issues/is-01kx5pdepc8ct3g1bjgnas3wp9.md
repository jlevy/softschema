---
type: is
id: is-01kx5pdepc8ct3g1bjgnas3wp9
title: Normalize JSON Schema numbers before cross-runtime hashing
kind: bug
status: closed
priority: 1
version: 7
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - compiler
  - canonicalization
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx5qhbc591ekb6dgv61qdsfq
  - type: blocks
    target: is-01kx5zjhrha1r5wkdjq66gseth
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T09:40:51.531Z
updated_at: 2026-07-10T13:10:41.987Z
closed_at: 2026-07-10T11:51:31.996Z
close_reason: Implemented portable compiler-number normalization; paired Python/TypeScript compilation and schema hash parity pass.
---
Equivalent Python/Pydantic and TypeScript/Zod contracts currently produce different schema_sha256 values when one runtime emits integral JSON numbers as floats (for example 10.0) and the other emits integers (10). Normalize portable JSON numeric representation at the canonical compiler boundary without changing JSON semantics; cover negative zero, safe/unsafe integer bounds, nonintegral values, annotations/extensions, and paired MoviePage compilation. Regenerate only intentional compiled examples after proving structural and hash parity.
