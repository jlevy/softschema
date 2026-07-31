---
type: is
id: is-01kyx6pcpns6mkwcq058xrrdc3
title: Define portable schema-only date format policy
kind: task
status: closed
priority: 3
version: 4
labels:
  - github-22-followup
dependencies: []
created_at: 2026-07-31T23:03:35.380Z
updated_at: 2026-07-31T23:43:04.242Z
closed_at: 2026-07-31T23:43:04.240Z
close_reason: "Decision and implementation folded into issue #22; no follow-up design work remains."
---
Decide whether softschema should keep JSON Schema date/date-time formats annotation-only or define cross-runtime structural enforcement. Current Pydantic compiled date schemas emit only format, while Zod ISO schemas also emit patterns, so schema-only invalid-date behavior differs. Keep this separate from GitHub issue #22 timestamp string normalization.

## Notes

Resolved within GitHub issue #22: softschema keeps JSON Schema Draft 2020-12 format annotation-only across runtimes and statuses; semantic Pydantic/Zod models own calendar validation; explicit portable assertions remain structural; the TypeScript compiler removes only Zod intrinsic ISO patterns and preserves authored regexes.
