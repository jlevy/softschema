---
type: is
id: is-01m5rtckh83srmhyxe09zdvee5
title: "PR #62 B3: C-first trusts any C parser; guards were derived for one clib/libyaml pair"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5yfcqwbhca5tae5pznyy
hold: null
hold_until: null
created_at: 2026-10-25T06:01:26.824Z
updated_at: 2026-10-25T06:29:33.787Z
started_at: 2026-10-25T06:29:29.127Z
closed_at: 2026-10-25T06:29:33.787Z
close_reason: "fixed in 69dd7e7 (#62): C-first gated to libyaml 0.1.7 via ruamel.yaml.clib and CHECKED_RUAMEL_VERSIONS; installation.md reworded"
resolution: null
duplicate_of: null
---
Low. PR #62, review B: https://github.com/jlevy/softschema/pull/62#pullrequestreview-5641769416. _portable.py:129,:145-146; docs/installation.md:39-45; pyproject.toml. Fix: gate C-first on the checked libyaml build and ruamel range; reword installation.md (ruamel 0.18.x installs the extension automatically).
