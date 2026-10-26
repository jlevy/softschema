---
type: is
id: is-01m5v5txqqf74v2cr27qmjxsee
title: Harden Python C-first gate to admit only ruamel.yaml.clib's parser (not clibz)
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-26T03:59:59.222Z
updated_at: 2026-10-26T04:13:10.382Z
started_at: 2026-10-26T04:10:11.156Z
closed_at: 2026-10-26T04:13:10.382Z
close_reason: "Done in PR https://github.com/jlevy/softschema/pull/72 (ready, not merged), head bf8562efbf7e2b1402300e638b9dcd8f280552bb (fix commit 9f7fb12 plus a merge of main 4c60658). The gate now requires CParser.__module__ in CHECKED_C_PARSER_MODULES (ruamel.yaml.clib._ruamel_yaml, _ruamel_yaml). A clibz parser gives pure, with the reason 'ruamel.yaml.clibz is not a checked build; only ruamel.yaml.clib is'. When clibz is installed but unused, the reason says so (detected through importlib.metadata). The libyaml docstring is corrected, the dependency is ruamel-yaml>=0.18,!=0.19.0 (uv.lock requires-dist updated), and CHANGELOG has an Unreleased Fixed entry. ci.yml is unchanged because the wheel's Requires-Dist already excludes 0.19.0. Checked against the real clibz 0.3.7 with main.CParser patched: origin/main gave c-first, this branch gives pure. Local runs: lint --check passed; pytest 597 passed; -m slow 21 passed; PURE 597+21 passed; py goldens 102 passed; cross-impl-diff OK. CI 19/19 pass; Qodo found 0 bugs, 0 rule violations and 0 requirement gaps."
resolution: null
duplicate_of: null
---
The C-first gate admits any CParser that reports libyaml 0.1.7 on ruamel.yaml 0.18-0.19. ruamel.yaml.clibz also reports 0.1.7 but is a different (Zig, free-threaded) build the differential search never covered. Gate on the parser's module identity (_ruamel_yaml / ruamel.yaml.clib._ruamel_yaml); report clibz as not a checked build; exclude ruamel.yaml 0.19.0 (clibz default dep). Branch claude/clib-only-gate.
