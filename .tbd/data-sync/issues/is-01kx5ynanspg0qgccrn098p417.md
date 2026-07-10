---
type: is
id: is-01kx5ynanspg0qgccrn098p417
title: Scope conformance consumer instructions to extracted archives
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - conformance
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:58.168Z
updated_at: 2026-07-10T12:50:39.455Z
closed_at: 2026-07-10T12:50:39.454Z
close_reason: Guide instructions now run the standard-library consumer only against an extracted conformance-kit.tar.gz with copyable shell commands; extracted 135-file smoke passes.
---
docs/softschema-guide.md presents conformance/consumer.py --json as a source-checkout command, but the strict consumer intentionally rejects source-only support files. State that it runs against an extracted published kit and give an archive extraction flow.
