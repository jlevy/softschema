---
type: is
id: is-01ksrxxpky39wwrfxre8xb9bwf
title: Freeze SoftschemaBinding for reliable registry equality
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:54:50.877Z
updated_at: 2026-07-10T03:49:08.272Z
closed_at: 2026-05-29T03:55:22.448Z
close_reason: SoftschemaBinding.model_config now includes frozen=True alongside extra=forbid and arbitrary_types_allowed=True. Tests pass.
---
SoftschemaRegistry.register checks existing != binding to detect contract-ID conflicts. If a binding were mutated after registration, the check could miss real conflicts. Add frozen=True to SoftschemaBinding's ConfigDict so post-registration mutation raises instead of going undetected. Bindings are not mutated anywhere in our codebase or in known downstream consumers.
