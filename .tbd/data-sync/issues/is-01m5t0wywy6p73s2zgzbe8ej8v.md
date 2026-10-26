---
type: is
id: is-01m5t0wywy6p73s2zgzbe8ej8v
title: "PR #62 E4: default tier went from 5 s to 22 s against the slow rule"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0wx1zedsf15d8pn6cwkqx
created_at: 2026-10-25T17:14:28.637Z
updated_at: 2026-10-25T17:23:39.882Z
closed_at: 2026-10-25T17:23:39.882Z
close_reason: "fixed in 9f6cb2b: five corpus/generated/code-point comparisons marked slow; default tier 506 passed in ~10 s, slow 21, both modes"
resolution: null
duplicate_of: null
---
Low. Mark test_generated_short_texts_read_as_pure, test_mutated_documents_read_as_pure, test_sampled_code_points_read_as_pure, test_generated_documents_read_as_pure, test_repo_documents_and_vector_texts_read_as_pure slow. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5644280692
