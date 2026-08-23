---
type: is
id: is-01m0pxqc0sw9tjvv4egq9w6p6a
title: "PR #42 review R1: allOf + \\$ref extension idiom falsely rejects declared keys"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m0pxqbkgrdn1bkyr2d76w67k
created_at: 2026-08-23T09:02:47.321Z
updated_at: 2026-08-23T09:17:54.193Z
closed_at: 2026-08-23T09:17:54.192Z
close_reason: "Fixed in 5aa2037: reference-aware definition closure (clause 4)."
resolution: null
duplicate_of: null
---
canonicalize.py _DEFINITION_KEYWORDS reset. allOf: [{\$ref: #/\$defs/Base}, {properties: {extra}}] — Base closes with additionalProperties:false and rejects extra, declared one branch over. Verified: {street, extra} valid under soft, invalid under enforced, BOTH engines (py 2 records, ajv 1 — also an unlisted deviation). Refused on main, so this is a regression from loud-refusal to wrong-specific-answer. Fix: reference-aware definition closure.
