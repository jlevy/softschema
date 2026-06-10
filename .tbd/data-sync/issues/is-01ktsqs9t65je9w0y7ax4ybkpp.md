---
type: is
id: is-01ktsqs9t65je9w0y7ax4ybkpp
title: "P1: Python library + generate internals (structured parse_error on missing file; vocab KeyError; enum-table pipe escape)"
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:31.494Z
updated_at: 2026-06-10T21:56:58.412Z
closed_at: 2026-06-10T21:56:58.412Z
close_reason: null
---
FILE SCOPE: validate.py, generate.py, schema_view.py.
- validate_artifact / _validate_frontmatter_artifact / _validate_pure_yaml_artifact: catch OSError so a missing/unreadable file returns a structured parse_error ArtifactValidationResult instead of raising (HIGH H2). 
- generate vocab pointer to nonexistent field: convert SchemaView.field KeyError into a clean ValueError (or caught error) so regenerate does not leak KeyError.
- _render_enum_table: escape '|' in enum values so a value with a pipe cannot break the Markdown table.
PARITY PAIR with P1 ts validate.ts bead (missing-file structured result). Regression tests in test_core.py/test_generate.py. Refs review H2, M3, N2.
