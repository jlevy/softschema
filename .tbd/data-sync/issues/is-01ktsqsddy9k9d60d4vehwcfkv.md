---
type: is
id: is-01ktsqsddy9k9d60d4vehwcfkv
title: "P3: status:enforced optional teeth (additionalProperties overlay at structural layer)"
kind: feature
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqtfectkne673n97a16rkd
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:35.198Z
updated_at: 2026-06-10T21:43:58.142Z
---
DECISION: optional teeth. FILE SCOPE: canonicalize.py/.ts (new apply_enforced_extras/applyEnforcedExtras), validate.py/.ts (thread overlay when effective status is enforced), golden scenario, docs (spec Status Values, guide promotion playbook, design docs).
- Overlay: recursively, any object schema declaring 'properties' but omitting 'additionalProperties' validates as additionalProperties:false. Explicit additionalProperties (true/false/subschema) ALWAYS wins. Free-form mappings (no properties) untouched. Validation-time only; never changes compiled sidecars. Rejected extras flow through existing additionalProperties normalization so cross-language output stays byte-identical.
- Effective status resolution unchanged (caller/--status, then document softschema.status).
- Golden scenario: same extras-bearing doc passes under permissive, fails under --status enforced and under document-declared enforced.
- Rewrite spec Status Values (drop 'does not change validation behavior by itself'), guide playbooks, python/ts design status wording.
Existing fixtures already declare explicit additionalProperties:false so their output is unchanged. Blocked by corpus safety net.
