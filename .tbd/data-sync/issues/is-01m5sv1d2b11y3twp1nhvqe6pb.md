---
type: is
id: is-01m5sv1d2b11y3twp1nhvqe6pb
title: "PR #64 C2: contract-less repair falls back to yaml_parse_error where validate says no_frontmatter/yaml_not_mapping"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:02.763Z
updated_at: 2026-10-25T16:25:56.259Z
closed_at: 2026-10-25T16:25:56.258Z
close_reason: "Fixed in f79c62e (PR #64): contract-less repair fallback derives kind from the profile (no_frontmatter / yaml_not_mapping) and uses validate's message for the pure-yaml case; TS also maps YamlParseError to yaml_parse_error explicitly. Unit tests in both runtimes assert kind+message equality with validate --contract; two repair.tryscript.md journeys."
resolution: null
duplicate_of: null
---
Correctness review C. Align repair record kinds with validate.
