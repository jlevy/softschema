---
type: is
id: is-01ktsqsd48t9a10k6080xyh3ag
title: "P2: Per-language test gaps (TS generate error paths, pure-yaml, skill --install, mirror drift, typecheck test/)"
kind: task
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:34.888Z
updated_at: 2026-06-10T21:42:34.888Z
---
FILE SCOPE: packages/typescript test files, tsconfig.json; packages/python test if needed.
- Cover generate.ts error paths (missing/unknown kind, missing contract, unterminated marker, renderFieldList, renderVocab).
- Cover pure-yaml parse-error path (validate.ts).
- Cover skill --install (TS) and add a TS mirror-drift test equivalent to test_skill_mirror_drift.py.
- Include 'test' in the TS tsconfig so bun run typecheck sees test files (MEDIUM 4.1).
Refs review TS 4.1/4.2/4.3, Skill 5b.
