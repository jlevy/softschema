---
type: is
id: is-01m5rz9ejqfj699wcvzvwzhns4
title: "PR #62 D2: record the checked ruamel.yaml.clib releases, not just libyaml 0.1.7"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rz95cv2g6jbq8knpb9z5t2
hold: null
hold_until: null
created_at: 2026-10-25T07:27:06.327Z
updated_at: 2026-10-25T15:50:34.053Z
started_at: 2026-10-25T07:37:35.853Z
closed_at: 2026-10-25T15:50:34.053Z
close_reason: "fixed in 3d0aa10 (option 1): CHECKED_LIBYAML_VERSION docstring, installation.md and the fuzz header record clib 0.2.8 (ruamel 0.18.10) and 0.2.15 (0.19.1) and that a new clib release needs the fuzz rerun"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642060738. _portable.py:151-179; docs/installation.md:48. Record 0.2.8 and 0.2.15 in the docstring and docs.
