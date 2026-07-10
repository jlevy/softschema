---
type: is
id: is-01ktsqsd48t9a10k6080xyh3ag
title: "P2: Per-language test gaps (TS generate error paths, pure-yaml, skill --install, mirror drift, typecheck test/)"
kind: task
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:34.888Z
updated_at: 2026-07-10T03:49:16.312Z
closed_at: 2026-06-11T05:18:53.947Z
close_reason: null
---
FILE SCOPE: packages/typescript test files, tsconfig.json; packages/python test if needed.
- Cover generate.ts error paths (missing/unknown kind, missing contract, unterminated marker, renderFieldList, renderVocab).
- Cover pure-yaml parse-error path (validate.ts).
- Cover skill --install (TS) and add a TS mirror-drift test equivalent to test_skill_mirror_drift.py.
- Include 'test' in the TS tsconfig so bun run typecheck sees test files (MEDIUM 4.1).
Refs review TS 4.1/4.2/4.3, Skill 5b.
