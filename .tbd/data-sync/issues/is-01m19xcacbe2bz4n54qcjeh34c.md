---
type: is
id: is-01m19xcacbe2bz4n54qcjeh34c
title: "Docs: regenerate every derived artifact, in order, and verify parity"
kind: task
status: open
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcyqz1ddyrpe6jbc0g4xa
  - type: blocks
    target: is-01m19xcz3ktm8yt7ajz1p5ww55
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:19.402Z
updated_at: 2026-08-30T18:02:53.790Z
---
The order matters and getting it wrong yields a green local run and a red cross-impl-diff:

  1. edit canonical sources
  2. make format          # reflows Markdown AND regenerates the skill mirrors
  3. bun run --cwd packages/typescript build    # refreshes packages/typescript/resources/**
  4. ./tests/golden/cross-impl-diff.sh

RESOURCE_PATHS in packages/typescript/src/resources-manifest.ts lists what gets copied: README.md, docs/softschema-{guide,spec,python-design,typescript-design}.md, docs/development.md, docs/installation.md, the movie_page example, and skills/softschema/SKILL.md.

This trap was hit once already this session: 'make format' reflowed the spec, the bundled TypeScript copy went stale, and cross-impl-diff.sh failed on 'docs spec' until the package was rebuilt.
