---
type: is
id: is-01kz5wzm8pjpbqc0nbv6er2jc0
title: "PR #26: maxsize=256 is an unnamed magic number"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wzknpm4nrrjjjramv3x5d
created_at: 2026-08-04T08:07:02.166Z
updated_at: 2026-08-04T08:11:18.866Z
closed_at: 2026-08-04T08:11:18.866Z
close_reason: Now _VALIDATOR_CACHE_SIZE with a docstring.
---
packages/python/src/softschema/validate.py:134 violates general-coding-rules and the local convention (_MAX_PATTERN_LENGTH at validate.py:245). (PR #26)
