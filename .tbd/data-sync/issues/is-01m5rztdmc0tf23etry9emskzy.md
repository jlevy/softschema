---
type: is
id: is-01m5rztdmc0tf23etry9emskzy
title: "PR #59 E1: walk follows contains where Ajv compiles nothing (minContains 0 no max; min > max)"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rztad5krc4zxt6mw8qwhw7
hold: null
hold_until: null
created_at: 2026-10-25T07:36:22.411Z
updated_at: 2026-10-25T07:46:08.662Z
started_at: 2026-10-25T07:36:27.031Z
closed_at: 2026-10-25T07:46:08.662Z
close_reason: "fixed in 7aded61: contains skip conditions in the walk; unreached vectors both complete; reached cases pinned (inert-contains-dangling-reference-reached, impossible-contains-dangling-reference-reached)"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5642083634. Same root cause as D2.
