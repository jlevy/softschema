---
type: is
id: is-01m5t0wyexp4hjptb6kdrta753
title: "PR #62 E3: the C-extension smoke step tests whatever PyPI serves that day"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0wx1zedsf15d8pn6cwkqx
created_at: 2026-10-25T17:14:28.189Z
updated_at: 2026-10-25T17:23:39.544Z
closed_at: 2026-10-25T17:23:39.544Z
close_reason: "fixed in 9f6cb2b: smoke step pins --with 'ruamel.yaml>=0.18,<0.20'; six smoke legs green in run 40216036001"
resolution: null
duplicate_of: null
---
Low. ci.yml:103-116. Constrain with --with 'ruamel.yaml>=0.18,<0.20'; optionally the build job's cool-off. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5644280692
