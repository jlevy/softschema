---
type: is
id: is-01m5rxgg3007w96g4zn1wyhy5d
title: "PR #64 A8: document name sits in different positions across messages; non-UTF-8 diagnostic names no file"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxgc8kdy9fz5wgg3ew5vsq
hold: null
hold_until: null
created_at: 2026-10-25T06:56:00.095Z
updated_at: 2026-10-25T07:12:36.307Z
started_at: 2026-10-25T07:02:48.982Z
closed_at: 2026-10-25T07:12:36.306Z
close_reason: "fixed in eadf5df (option a): every softschema message naming a document uses the backticked-prefix form in both runtimes; non-UTF-8 diagnostic names the path; goldens and unit tests updated; docstring claim now accurate."
resolution: null
duplicate_of: null
---
Low. validate.py:1074,1083,1119; validate.ts:135,171,181; _portable.py:97; portable.ts:61. Option (a): prefix form everywhere; name the path in the non-UTF-8 message.
PR #64. Review A: https://github.com/jlevy/softschema/pull/64#pullrequestreview-5641911619
