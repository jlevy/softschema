---
type: is
id: is-01m5rtd6b0zmd9sh9d6jt915jh
title: "round_trip_yaml() registers its null representer on ruamel's shared RoundTripRepresenter (_portable.py:304-329), changing every rt YAML in the process; make it per-instance (same bug class as frontmatter-format #8)"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T06:01:46.080Z
updated_at: 2026-10-25T06:26:58.676Z
started_at: 2026-10-25T06:04:17.978Z
closed_at: 2026-10-25T06:26:58.676Z
close_reason: "Fixed in 12f5aeb: round_trip_yaml() now sets yaml.Representer to a module-private RoundTripRepresenter subclass carrying the null representer, so ruamel's shared class is untouched. Regression test test_round_trip_emitter_leaves_other_round_trip_instances_alone (packages/python/tests/test_repair_conform.py) fails on the previous _portable.py and passes after; it checks the shared class registry and a stock YAML(typ='rt') built after softschema ran. Only other registration in the package (_PortableConstructor.add_constructor) is already on a subclass. TypeScript configures its emitter per call (parseRoundTrip/dumpRoundTrip), no shared state."
resolution: null
duplicate_of: null
---
