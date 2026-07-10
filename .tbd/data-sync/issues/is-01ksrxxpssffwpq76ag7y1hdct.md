---
type: is
id: is-01ksrxxpssffwpq76ag7y1hdct
title: Evaluate audit-flagged redundant tests
kind: task
status: closed
priority: 3
version: 4
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:54:51.064Z
updated_at: 2026-07-10T03:49:09.620Z
closed_at: 2026-05-29T03:55:22.621Z
close_reason: Both tests evaluated and kept. test_no_undocumented_codes_emitted is a guard against undocumented codes leaking from emit paths (distinct from per-code tests). test_sfield_movie_example covers the 'instruction' field which test_schema_view does not check.
---
Audit flagged test_warning_codes.py:97 (test_no_undocumented_codes_emitted_in_smoke_run) and test_sfield.py:85 (test_sfield_movie_example_genres_block_present) as possibly redundant. Conclusion: keep both. The warning-codes smoke test is a guard against undocumented codes leaking from emit paths (different invariant from the per-code tests). The sfield test asserts the 'instruction' field is preserved into the committed sidecar, which test_schema_view's softmeta retrieval test does not check.
