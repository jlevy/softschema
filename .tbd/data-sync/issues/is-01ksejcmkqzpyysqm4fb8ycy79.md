---
type: is
id: is-01ksejcmkqzpyysqm4fb8ycy79
title: Verify bundled docs after rename in Phase 4
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-25T03:20:53.110Z
updated_at: 2026-05-25T03:23:43.676Z
closed_at: 2026-05-25T03:23:43.675Z
close_reason: Phase 4 now checks the wheel for the renamed softschema-python-design.md.
---
Phase 4 release readiness does not verify bundled-resource paths after the design.md rename. Add step: 'Confirm docs/softschema-python-design.md is included in the wheel (uv build then unzip -l dist/*.whl | grep python-design).'
