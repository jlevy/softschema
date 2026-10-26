---
type: is
id: is-01m5t0dk6a22rt6nn6ktgchjs3
title: "PR #64 E4: block-scalar tracking misses quoted keys, - key: | and non-ASCII keys"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0dhtbty9r2zjty30vcjq9
created_at: 2026-10-25T17:06:05.130Z
updated_at: 2026-10-25T17:26:19.029Z
closed_at: 2026-10-25T17:26:19.029Z
close_reason: "Fixed in ad69d3b (PR #64): block scalar opener recognised by indicator alone (quoted key, '- key: |', non-ASCII key) in both runtimes; vectors next_line_in_block_scalar_after_quoted_key/_in_sequence_mapping/_after_non_ascii_key."
resolution: null
duplicate_of: null
---
Medium. Recognise the opener by the indicator alone; vectors.
