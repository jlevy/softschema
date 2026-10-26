---
type: is
id: is-01kz5wzpdzf8fsk0jp10a8meye
title: parse_yaml parses each document twice
kind: feature
status: closed
priority: 2
version: 3
labels: []
dependencies: []
created_at: 2026-08-04T08:07:04.382Z
updated_at: 2026-10-26T03:17:21.546Z
closed_at: 2026-10-26T03:17:21.530Z
close_reason: "Measured on main 8085986 (C-first, libyaml 0.1.7): parse_yaml vs a single plain ruamel safe C load — small frontmatter 0.54 ms vs 0.24 ms; a 150 KB document 347 ms vs 337 ms (+3%); pure ruamel is 0.75 ms / 1341 ms. The ~12x cost the bead describes predates C-first reading (#62): the event preflight and the load now both run on libyaml, so collapsing to one pass could save at most ~3% on large documents and ~0.3 ms on small ones, while it would mean re-implementing the portable rules (tags, merge keys, aliases, depth, number forms, flow rules) inside construction — the code just hardened across seven review rounds. Not worth the risk; closed as resolved by the C-first reader. Benchmark: scratchpad bench_fstu.py."
resolution: null
duplicate_of: null
---
Event-stream preflight then a second construction pass; roughly 12x more work than a single pass with a C loader. Raised as follow-up in PR #27.

## Notes

Triaged for the v0.6.2 patch release and deliberately deferred: not quickly fixable.

The second pass is not redundant work that can simply be dropped. The event-stream preflight in _portable.parse_yaml is what enforces the portable value domain before construction: explicit tags (yaml_custom_tag), merge keys (yaml_merge_key), aliases and anchors (yaml_alias), and the MAX_DEPTH=64 bound (yaml_limit). Those rules are the cross-runtime portability guarantee, not an optimization, and a single-pass C loader does not expose the events needed to enforce them.

Collapsing to one pass therefore means redesigning how the portable rules are enforced (e.g. a custom constructor that rejects during construction, with matching error codes and identical behavior in the TypeScript port). That is a design change with parity implications across both runtimes, which is exactly what the patch release excluded. Worth doing, but as its own scoped piece of work with the parity process in docs/development.md followed end to end.
