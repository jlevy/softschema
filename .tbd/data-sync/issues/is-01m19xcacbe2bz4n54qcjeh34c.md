---
type: is
id: is-01m19xcacbe2bz4n54qcjeh34c
title: "Docs: regenerate every derived artifact, in order, and verify parity"
kind: task
status: closed
priority: 1
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcyqz1ddyrpe6jbc0g4xa
  - type: blocks
    target: is-01m19xcz3ktm8yt7ajz1p5ww55
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:19.402Z
updated_at: 2026-08-30T18:42:16.872Z
closed_at: 2026-08-30T18:42:16.872Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
The order matters and getting it wrong yields a green local run and a red cross-impl-diff:

  1. edit canonical sources
  2. make format          # reflows Markdown AND regenerates the skill mirrors
  3. bun run --cwd packages/typescript build    # refreshes packages/typescript/resources/**
  4. ./tests/golden/cross-impl-diff.sh

RESOURCE_PATHS in packages/typescript/src/resources-manifest.ts lists what gets copied: README.md, docs/softschema-{guide,spec,python-design,typescript-design}.md, docs/development.md, docs/installation.md, the movie_page example, and skills/softschema/SKILL.md.

This trap was hit once already this session: 'make format' reflowed the spec, the bundled TypeScript copy went stale, and cross-impl-diff.sh failed on 'docs spec' until the package was rebuilt.
