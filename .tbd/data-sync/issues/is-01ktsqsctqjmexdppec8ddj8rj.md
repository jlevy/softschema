---
type: is
id: is-01ktsqsctqjmexdppec8ddj8rj
title: "P2: Close cross-language divergences exposed by the corpus"
kind: task
status: in_progress
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:34.583Z
updated_at: 2026-06-11T04:43:54.880Z
---
FILE SCOPE: errors.ts, validate.ts, compile.ts, tests/golden/README.md.
- pyRepr number formatting: exponent zero-padding (1e-7->1e-07), Python's 1e16 exponential threshold (1e20->1e+20), inf/nan vs Infinity/NaN (MEDIUM 1.1). Includes the ss-wbnm whole-number-float case where feasible.
- validate.ts empty-frontmatter '?? {}' coercion -> match Python (no_frontmatter/parse_error) (LOW 1.3).
- unterminated-fence error kind alignment (LOW 1.4).
- compile.ts augmentSchema: merge an existing root x-softschema block instead of replacing (LOW 1.5).
- error-message quoting/'got list' wording where cheap.
- Document any remaining number-format limitation in tests/golden/README.md with the exact value ranges the corpus must avoid.
Blocked by P2 corpus bead (golden-first).
