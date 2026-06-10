---
type: is
id: is-01ktsqsav2t9heta9h49hrqjd0
title: "P1: Packaging bundle parity + DOC_TOPICS-resolves test (ship typescript-design in wheel, movie schema in npm, pytest config)"
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqtgsd9ryf1ag8n7zx80b3
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:32.546Z
updated_at: 2026-06-10T21:43:58.724Z
---
FILE SCOPE: pyproject.toml, packages/typescript/scripts/copy-resources.ts, one test in each package.
- pyproject [tool.hatch.build.targets.wheel.force-include]: add docs/softschema-typescript-design.md (HIGH M1: docs typescript-design crashes from a wheel install).
- copy-resources.ts RESOURCES: add examples/movie_page/movie-page.schema.yaml (npm/wheel symmetry).
- pyproject [tool.pytest.ini_options]: python_files back to test_*.py (not *.py).
- Add a test in BOTH packages asserting every DOC_TOPICS path resolves from the built/bundled artifact (guards future manifest drift).
Refs review Packaging HIGH/MEDIUM, Python L-pytest.
