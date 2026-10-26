---
type: is
id: is-01m5rz9bfqfnftd7xvmqvqd15q
title: "PR #62 C3: yaml_parser_mode docstring and installation.md gaps around the gate"
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
created_at: 2026-10-25T07:27:03.159Z
updated_at: 2026-10-25T15:50:32.940Z
started_at: 2026-10-25T07:37:34.006Z
closed_at: 2026-10-25T15:50:32.940Z
close_reason: "fixed in 3d0aa10: yaml_parser_mode docstring names the gate; installation.md warns off the libyaml extra (clibz) and names uv tool install --with ruamel.yaml.clib"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642029532. _portable.py:183-191; docs/installation.md:40-45 (clibz/libyaml extra warning; uv tool install --with).
