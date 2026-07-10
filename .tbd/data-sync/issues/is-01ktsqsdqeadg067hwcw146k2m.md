---
type: is
id: is-01ktsqsdqeadg067hwcw146k2m
title: "P3: Move binding inference into the libraries (contract/status/envelope, single read)"
kind: feature
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:35.501Z
updated_at: 2026-07-10T03:49:16.707Z
closed_at: 2026-06-11T05:18:55.338Z
close_reason: null
---
FILE SCOPE: validate.py/.ts (new library API), cli.py/.ts (thin callers), models.
- Move contract-from-metadata, status resolution, and single-key envelope inference WITH ambiguity rejection (spec lines 101-110) out of the CLI layer into library API in BOTH packages. CLIs call it; document is read once (removes the double fmf_read).
- Library callers with no envelope_key now get spec behavior (infer single key / reject multi-key ambiguity) instead of a merged multi-key payload (design issue 2).
Golden-first; per-impl scenarios for ambiguous multi-key rejection. Blocked by corpus safety net.
