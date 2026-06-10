---
type: is
id: is-01ktsqsb4vd1n4f7r2ejccykj8
title: "P1: Trivial cleanups (lint.py UTF-8, dead TS re-export, dead null check)"
kind: task
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:32.858Z
updated_at: 2026-06-10T21:42:32.858Z
---
FILE SCOPE: devtools/lint.py, packages/typescript/src/generate.ts, packages/typescript/src/softField.ts.
- devtools/lint.py: path.read_text(encoding='utf-8').
- generate.ts: remove dead 'export type { FieldInfo }' (re-exported from nowhere; index.ts exports it from schemaView).
- softField.ts: remove dead 'options.order !== null' (order is number|undefined, never null).
Refs review TS 3.2/3.3, Python L5/N-nit.
