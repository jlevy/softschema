---
type: is
id: is-01m5sv1cptttcz94c8psrnwszs
title: "PR #64 C1: bare CR is a line break for ruamel but content for yaml"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:02.394Z
updated_at: 2026-10-25T16:25:55.978Z
closed_at: 2026-10-25T16:25:55.978Z
close_reason: "Fixed in 04b6c3e (PR #64): a lone CR (\\r not followed by \\n) joins the portable preflight class in both runtimes (rejection over normalization, consistent with the PR); CRLF passes; spec names it; portable_values vectors lone_cr_between_keys, lone_cr_in_flow_scalar, lone_cr_in_block_scalar, crlf_line_endings, escaped_cr."
resolution: null
duplicate_of: null
---
Correctness review C. Make both runtimes agree on a lone CR.
