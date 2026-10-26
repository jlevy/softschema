---
type: is
id: is-01m5tg5md6zp8chzmyab9xmbh2
title: Python reads YAML 1.1-style numbers (1_000, 0b101, -0x10, +0x10, -0o17, 1_0.5) as numbers; TypeScript reads them as strings
kind: bug
status: closed
priority: 1
version: 2
labels:
  - pr-64
dependencies: []
created_at: 2026-10-25T21:41:21.446Z
updated_at: 2026-10-25T23:11:08.482Z
closed_at: 2026-10-25T23:11:08.482Z
close_reason: "Fixed in 3bbcf3c (PR #64, head ef45250): a plain scalar that ruamel's YAML 1.2 resolver types as a number and the core schema reads as a string, or the reverse (1_000, 1_0.5, -_, 0b101, -0x10, +0x10, -0o17, .5e3), is yaml_unsupported_scalar in both runtimes; %YAML other than 1.2 and directives other than %TAG are yaml_parse_error (1.1 schemas differ; 1.0/1.3 crashed Python with AssertionError). _RUAMEL_NUMBER pinned to ruamel's resolve() over 60,000 scalars. Sweep: 350,355 number-like plain scalars, 0 silent and 0 loud differences (py C-first, pure, TS). Vectors in tests/vectors/hardening.yaml portable_values; spec + CHANGELOG. CI run 40243372151 19/19. Addendum: https://github.com/jlevy/softschema/pull/64#issuecomment-6404713010"
resolution: null
duplicate_of: null
---
Found while fixing PR #64 review F3 (silent, pre-existing, not in review F). ruamel's YAML 1.2 int/float resolver still accepts underscores, 0b binary, and signed hex/octal; the yaml package's core schema (YAML 1.2) does not and returns the plain string. Probe (parse_yaml vs parsePortableYaml, C-first and pure identical): n: 1_000 -> py 1000 / ts '1_000'; n: -0x10 -> -16 / '-0x10'; n: +0x10 -> 16 / '+0x10'; n: -0o17 -> -15 / '-0o17'; n: 0b101 -> 5 / '0b101'; n: 1_0.5 -> 10.5 / '1_0.5'; also -0_0, -0x0, -0o0 -> 0 / string. 0o17, 012, +12 agree. Both documents validate, with different values: a silent cross-runtime difference. Likely fix: give _PortableConstructor/resolver the YAML 1.2 core int and float patterns so these resolve as strings in Python (a Python value change; needs a Compatibility note and shared vectors). Needs a maintainer decision on which reading is right.
