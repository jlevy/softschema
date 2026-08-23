---
type: is
id: is-01kz7dp91qqbyhctf7eb2r8bv3
title: validate_artifact document parameter is typed Any in Python; the sentinel blocks static checking that the TypeScript ParsedDocument now gets (packages/python/src/softschema/validate.py:373)
kind: chore
status: open
priority: 3
version: 2
labels: []
dependencies: []
created_at: 2026-08-04T22:18:15.991Z
updated_at: 2026-08-22T23:15:35.292Z
---

## Notes

Triaged for the v0.6.2 patch release and deliberately deferred: a P3 chore rather than a bug, and it touches a public API signature.

Nothing is functionally wrong; the _UNREAD sentinel forces document: Any, which loses the static checking the TypeScript ParsedDocument gets. Fixing it properly means giving the sentinel a type the checker can narrow (e.g. a private singleton class plus an alias for the parameter) and deciding whether the public signature changes shape, which is a judgment call about the exported surface rather than a mechanical edit. Left for a release where an API-surface change is in scope.
