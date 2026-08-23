---
type: is
id: is-01kz5wzpdzf8fsk0jp10a8meye
title: parse_yaml parses each document twice
kind: feature
status: open
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-08-04T08:07:04.382Z
updated_at: 2026-08-22T23:15:35.025Z
---
Event-stream preflight then a second construction pass; roughly 12x more work than a single pass with a C loader. Raised as follow-up in PR #27.

## Notes

Triaged for the v0.6.2 patch release and deliberately deferred: not quickly fixable.

The second pass is not redundant work that can simply be dropped. The event-stream preflight in _portable.parse_yaml is what enforces the portable value domain before construction: explicit tags (yaml_custom_tag), merge keys (yaml_merge_key), aliases and anchors (yaml_alias), and the MAX_DEPTH=64 bound (yaml_limit). Those rules are the cross-runtime portability guarantee, not an optimization, and a single-pass C loader does not expose the events needed to enforce them.

Collapsing to one pass therefore means redesigning how the portable rules are enforced (e.g. a custom constructor that rejects during construction, with matching error codes and identical behavior in the TypeScript port). That is a design change with parity implications across both runtimes, which is exactly what the patch release excluded. Worth doing, but as its own scoped piece of work with the parity process in docs/development.md followed end to end.
