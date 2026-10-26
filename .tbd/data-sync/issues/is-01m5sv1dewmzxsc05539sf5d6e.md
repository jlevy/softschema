---
type: is
id: is-01m5sv1dewmzxsc05539sf5d6e
title: "PR #64 C3: surrogate pair as two \\\\u escapes valid in TS, rejected in Python"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:03.164Z
updated_at: 2026-10-25T16:25:56.565Z
closed_at: 2026-10-25T16:25:56.565Z
close_reason: "Fixed in f79c62e (PR #64): Python constructor joins a surrogate pair written as two \\u escapes (as JSON and the yaml package do); a lone surrogate is still rejected. Spec sentence; vectors escaped_surrogate_pair, escaped_lone_surrogate, escaped_reversed_surrogates."
resolution: null
duplicate_of: null
---
Correctness review C. Align per YAML 1.2.
