---
type: is
id: is-01m0vcqpcf8qncrdaw92awc4n0
title: Define the portable JSON Schema-Pydantic-Zod profile
kind: feature
status: open
priority: 3
version: 4
labels: []
dependencies: []
parent_id: null
created_at: 2026-08-25T02:42:04.302Z
updated_at: 2026-10-26T03:33:11.813Z
---
Publish a current normative matrix for the supported portable structural subset. For each construct, identify the canonical Draft 2020-12 form, idiomatic Pydantic and Zod authoring forms, compilation normalization, accept-set caveats, and conformance fixture. Separate compiler-supported constructs from hand-authored JSON Schema validation and from the enforced-overlay topology matrix; replace reliance on the stale completed parity-plan table.

## Notes

Origin: follow-up feature from the PR #44 checked-enforcement review (epic ss-6xya, closed 2026-10-26); not a review finding, so detached from it. Still future and not started at v0.9.0: docs/softschema-spec.md, section "Release-Level Mapping Across JSON Schema, Pydantic, and Zod", says the table is area-level for this release and that a future profile may enumerate each source construct, canonicalization rule, accept-set caveat, and conformance vector. That future profile is this bead. The stale table it should replace is in docs/project/specs/done/plan-2026-06-01-softschema-typescript-zod-parity.md.
