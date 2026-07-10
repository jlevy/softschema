---
type: is
id: is-01kx5ythb4cazvsyfz3r4mbptp
title: Align library parity explanations with idiomatic host APIs
kind: bug
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - architecture
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:07:48.835Z
updated_at: 2026-07-10T12:50:40.018Z
closed_at: 2026-07-10T12:50:40.017Z
close_reason: Development and TypeScript design docs now promise shared semantics/wire/schema/CLI behavior with idiomatic host APIs rather than method-for-method library parity.
---
Development and TypeScript design docs still claim exact/equivalent library API parity despite intentional host-language surfaces such as ContractDescriptor/bindContract. State the actual contract: shared semantics, wire results, schema bytes, and CLI behavior with idiomatic library APIs.
