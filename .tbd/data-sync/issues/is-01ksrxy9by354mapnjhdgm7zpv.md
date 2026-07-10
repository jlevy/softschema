---
type: is
id: is-01ksrxy9by354mapnjhdgm7zpv
title: "[deferred] Tighten __all__ surface in softschema/__init__.py"
kind: task
status: closed
priority: 3
version: 7
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels: []
dependencies: []
parent_id: is-01kx4vfdwqtmk0tt9q9kznyhwq
created_at: 2026-05-29T03:55:10.077Z
updated_at: 2026-07-10T07:18:26.556Z
closed_at: 2026-07-10T07:18:26.555Z
close_reason: Implemented and verified in 99d5250
---
Audit P2.20. __all__ lists 32 symbols. CONTRIBUTING.md asks new additions to justify themselves. Re-audit before v0.2: are FieldInfo, SFieldMeta, SoftOwner, SoftTier, RepairKind, GeneratedSection all required at top level, or could they live under softschema.schema_view / softschema.sfield / softschema.generate sub-namespaces? Public-surface change so cannot be reverted casually; defer to v0.2.

## Notes

v0.2.2 audit: __all__ exports 32 symbols. Removing any of them (e.g. FieldInfo, SoftFieldMeta, SoftOwner, SoftTier, RepairKind, GeneratedSection) is a backwards-incompatible reduction of the public API, which warrants a MINOR (not patch) bump per semver. Decision: keep the surface intact for the 0.2.2 patch; the TS index.ts and Python __init__.py public surfaces are intentionally mirrored. Tightening (or moving symbols under submodules) is tracked here for a future minor release.

2026-07-09 audit: retained and reparented to ss-b5l4. origin/main intentionally exports the 32-symbol Python surface and mirrors the applicable symbols from the TypeScript root. The July plan preserves public entrypoints and types through v0.3 and defers removals to a documented pre-1.0 release. ss-b5l4 owns API alignment and deprecation guidance, so it is the correct place to decide whether any later surface reduction is justified.
