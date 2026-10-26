---
type: is
id: is-01m5sy45q4fwwn3zxr89rwhxrw
title: Decide whether the portable preflight rejection gets its own record kind (e.g. yaml_unportable_character)
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T16:25:59.268Z
updated_at: 2026-10-26T03:17:22.177Z
closed_at: 2026-10-26T03:17:22.176Z
close_reason: "Decided: keep yaml_parse_error for the portable-preflight rejection. 0.9.0 shipped with that kind and documented it in the spec and the CHANGELOG Compatibility section; introducing a new kind now would change the record contract for consumers matching yaml_parse_error. The diagnostic already names the character, the escape to write and its line/column, so consumers can tell it apart from engine syntax errors without a new kind, and repair no longer needs a distinct kind to target it. Revisit only with a spec change in a minor release."
resolution: null
duplicate_of: null
---
From PR #64 review B6: a distinct kind for the preflight rejection would let consumers tell it from an engine syntax error. It is a contract addition, so it needs a spec decision; repair no longer needs it to target the rejection.
