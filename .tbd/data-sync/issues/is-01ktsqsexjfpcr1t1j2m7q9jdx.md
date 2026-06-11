---
type: is
id: is-01ktsqsexjfpcr1t1j2m7q9jdx
title: "P3: Metadata-only validate mode (useful from the soft stage)"
kind: feature
status: in_progress
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:36.722Z
updated_at: 2026-06-11T04:52:26.514Z
---
FILE SCOPE: cli.py/.ts, validate.py/.ts.
- softschema validate without --model/--schema performs a metadata-only check: softschema block shape, contract-ID form, envelope presence/uniqueness; exit 0/1 accordingly. Serves the gradual-adoption funnel (design issue 6) and gives the spec metadata rules an enforcement point with no schema.
Golden scenario. Blocked by corpus safety net.
