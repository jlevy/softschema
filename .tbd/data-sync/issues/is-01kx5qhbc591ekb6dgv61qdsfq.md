---
type: is
id: is-01kx5qhbc591ekb6dgv61qdsfq
title: Reserve and validate the root compiler metadata block
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - compiler
  - parity
  - conformance
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx5rvw9tdgwa3cdhmgtxad6h
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T10:00:27.780Z
updated_at: 2026-07-10T11:51:32.181Z
closed_at: 2026-07-10T11:51:32.180Z
close_reason: Reserved root x-softschema compiler metadata in both runtimes; hostile metadata and public-profile tests pass.
---
Both compilers currently merge arbitrary model-supplied root x-softschema content, and Python can crash on a non-mapping value, while the public compiled-schema profile permits only contract, schema_sha256, and softschema_format_version. Make root x-softschema reserved compiler output with identical overwrite/rejection semantics across Pydantic and Zod; preserve per-field x-softschema annotations; prove hostile/custom/non-mapping root metadata cannot leak into compiled output and the result validates the conformance profile.
