---
type: is
id: is-01ktsqseetr99vdw14kcb8888b
title: "P3: Enforce softschema metadata rules (reject unknown keys; define+validate contract ID)"
kind: feature
status: in_progress
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqtg3vrcjttjqydfz7w989
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:36.250Z
updated_at: 2026-06-11T04:51:14.310Z
---
FILE SCOPE: models.py (SchemaMetadata extra='forbid'), models.ts (reject extra keys), docs/softschema-spec.md.
- Reject unknown keys in the softschema: block in BOTH implementations -> document_softschema_invalid (spec line 86; currently silently accepted, HIGH F2.2). 
- Define 'malformed contract' in the spec: non-empty string minimum; recommended namespace:Name/version form documented as advisory; validate the minimum (HIGH F2.1).
Golden scenario for unknown-key rejection. Blocked by corpus safety net.
