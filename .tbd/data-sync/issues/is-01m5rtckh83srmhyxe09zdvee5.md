---
type: is
id: is-01m5rtckh83srmhyxe09zdvee5
title: "PR #62 B3: C-first trusts any C parser; guards were derived for one clib/libyaml pair"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5rr5yfcqwbhca5tae5pznyy
created_at: 2026-10-25T06:01:26.824Z
updated_at: 2026-10-25T06:01:26.824Z
---
Low. PR #62, review B: https://github.com/jlevy/softschema/pull/62#pullrequestreview-5641769416. _portable.py:129,:145-146; docs/installation.md:39-45; pyproject.toml. Fix: gate C-first on the checked libyaml build and ruamel range; reword installation.md (ruamel 0.18.x installs the extension automatically).
