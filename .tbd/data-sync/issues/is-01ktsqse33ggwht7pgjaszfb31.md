---
type: is
id: is-01ktsqse33ggwht7pgjaszfb31
title: "P3: Pure-yaml profile honors metadata + envelope rules (or amend spec)"
kind: feature
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:35.874Z
updated_at: 2026-06-10T21:42:35.874Z
---
FILE SCOPE: validate.py/.ts, docs/softschema-spec.md.
- Implement the spec's stated rule: in pure-yaml, recognize the softschema: metadata block at the document root and apply the same envelope rules, rather than validating the whole root (incl. the softschema block) as payload (design issue 3).
- OPEN QUESTION in spec: if implementation shows whole-root-as-payload is the better contract, amend the spec instead. Resolve before merging.
Golden-first pure-yaml scenarios. Blocked by corpus safety net.
