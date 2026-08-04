---
type: is
id: is-01kz5wzkz15bqwz9fy5vww4yya
title: "PR #26: (mtime_ns, size) cache key has a staleness window"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wzknpm4nrrjjjramv3x5d
created_at: 2026-08-04T08:07:01.857Z
updated_at: 2026-08-04T08:11:18.598Z
closed_at: 2026-08-04T08:11:18.596Z
close_reason: Cache now keys on schema text; the forced (mtime_ns,size) collision that served stale returns fresh.
---
packages/python/src/softschema/validate.py:134-157. Forcing an identical (mtime_ns, size) serves a stale validator. Reachable via timestamp-preserving copies (cp -p, rsync -t, tar -x, CI cache restore). Fix: key on a blake2b hash of the file bytes. (PR #26)
