---
type: is
id: is-01kxa67yj86egf2n1zqrwspwqj
title: "PR21 Bugbot: quoted scalar fence semantics"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-07-12T03:34:26.119Z
updated_at: 2026-07-12T03:34:26.411Z
closed_at: 2026-07-12T03:34:26.410Z
close_reason: "False positive: ruamel rejects a column-one --- inside a quoted scalar as an unexpected YAML document separator even without Markdown fencing. frontmatter-format also treats it as the closing fence. Indented continuations are legal and covered by the shared regression."
---
Evaluate discussion_r3565583117 claiming a column-one --- can legally occur inside a YAML quoted scalar and should not close frontmatter.
