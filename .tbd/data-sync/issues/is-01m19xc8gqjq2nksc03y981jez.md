---
type: is
id: is-01m19xc8gqjq2nksc03y981jez
title: "Docs: both design docs -- the outcome/exit paragraph and the parity table"
kind: task
status: open
priority: 2
version: 2
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcacbe2bz4n54qcjeh34c
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:17.494Z
updated_at: 2026-08-30T18:02:53.124Z
---
docs/softschema-python-design.md and docs/softschema-typescript-design.md both carry: 'The CLI reads once to infer document binding: readable results map to exits 0 or 1, while access and parse failures use its one-line stderr and exit-2 input boundary.'

That sentence describes the design this epic replaces, and it is the design doc's own statement of the flag-dependent behavior. Rewrite it to state the command-level rule instead.

Also: the Python doc's 'Alignment with python-cli-patterns' exit-code list, and the TypeScript doc's Python-TypeScript API parity table (add load_artifact/loadArtifact).
