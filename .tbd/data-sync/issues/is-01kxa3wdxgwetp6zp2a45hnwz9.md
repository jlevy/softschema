---
type: is
id: is-01kxa3wdxgwetp6zp2a45hnwz9
title: "PR #21 review R3: use structural JSON parity"
kind: bug
status: closed
priority: 2
version: 4
labels: []
dependencies: []
parent_id: is-01kxa3wdphxg0ceb0mydnbz81q
created_at: 2026-07-12T02:53:11.471Z
updated_at: 2026-07-12T03:11:56.711Z
closed_at: 2026-07-12T03:11:56.710Z
close_reason: Cross-runtime JSON is compared structurally with an order-independence regression guard; exact comparisons remain only for text and byte contracts.
---
Formal review R3: replace general stdout byte parity with structural JSON comparison, reserving exact bytes for schema digests and exact text contracts. Update golden/parity docs and tests.
