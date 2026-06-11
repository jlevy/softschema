---
type: is
id: is-01ktsqtgsd9ryf1ag8n7zx80b3
title: "P4: Resource manifest unification + trim bundled topics"
kind: task
status: in_progress
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:43:11.405Z
updated_at: 2026-06-11T06:20:34.022Z
---
FILE SCOPE: a shared manifest resource, pyproject force-include, copy-resources.ts, DOC_TOPICS in both CLIs.
- One manifest consumed by the wheel force-include, the npm copy-resources script, and DOC_TOPICS (remove three hand-maintained copies that already drifted).
- Drop or sanitize the 'agents' and 'publishing' topics: strip the repo-internal tbd integration block from the bundled AGENTS.md so installed-package users do not get 'This repository uses tbd...'.
OPEN QUESTION: dropping topics changes the public docs surface; confirm acceptable in the phase-3 minor bump. Refs review Improvements 5/6/8, Packaging MEDIUM.
