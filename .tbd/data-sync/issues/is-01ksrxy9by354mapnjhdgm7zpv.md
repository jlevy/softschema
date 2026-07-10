---
type: is
id: is-01ksrxy9by354mapnjhdgm7zpv
title: "[deferred] Tighten __all__ surface in softschema/__init__.py"
kind: task
status: open
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:55:10.077Z
updated_at: 2026-06-15T17:49:35.153Z
---
Audit P2.20. __all__ lists 32 symbols. CONTRIBUTING.md asks new additions to justify themselves. Re-audit before v0.2: are FieldInfo, SFieldMeta, SoftOwner, SoftTier, RepairKind, GeneratedSection all required at top level, or could they live under softschema.schema_view / softschema.sfield / softschema.generate sub-namespaces? Public-surface change so cannot be reverted casually; defer to v0.2.

## Notes

v0.2.2 audit: __all__ exports 32 symbols. Removing any of them (e.g. FieldInfo, SoftFieldMeta, SoftOwner, SoftTier, RepairKind, GeneratedSection) is a backwards-incompatible reduction of the public API, which warrants a MINOR (not patch) bump per semver. Decision: keep the surface intact for the 0.2.2 patch; the TS index.ts and Python __init__.py public surfaces are intentionally mirrored. Tightening (or moving symbols under submodules) is tracked here for a future minor release.
