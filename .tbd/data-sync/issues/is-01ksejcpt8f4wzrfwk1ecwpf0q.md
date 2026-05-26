---
type: is
id: is-01ksejcpt8f4wzrfwk1ecwpf0q
title: Decide AGENTS.md linkage to python design doc
kind: task
status: closed
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-25T03:20:55.367Z
updated_at: 2026-05-25T03:23:43.837Z
closed_at: 2026-05-25T03:23:43.823Z
close_reason: AGENTS.md now lists the python design doc under 'For implementer reference'.
---
AGENTS.md does not link to docs/softschema-python-design.md. That asymmetry is probably correct (agents using the package do not need implementation rationale) but should be a conscious decision. Document the choice or add a brief reference.
