---
type: is
id: is-01m5sy45q4fwwn3zxr89rwhxrw
title: Decide whether the portable preflight rejection gets its own record kind (e.g. yaml_unportable_character)
kind: task
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T16:25:59.268Z
updated_at: 2026-10-25T16:25:59.268Z
---
From PR #64 review B6: a distinct kind for the preflight rejection would let consumers tell it from an engine syntax error. It is a contract addition, so it needs a spec decision; repair no longer needs it to target the rejection.
