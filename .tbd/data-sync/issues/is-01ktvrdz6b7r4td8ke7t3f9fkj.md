---
type: is
id: is-01ktvrdz6b7r4td8ke7t3f9fkj
title: "P1: Consumption-model docs (dependency vs zero-install) per design 0"
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwqsbfsd1y9vm6vem0t5q
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T16:32:17.611Z
updated_at: 2026-06-11T20:11:27.298Z
---
Design 0: docs/installation.md gains a decision table (pin as a dependency for projects/CI/library; zero-install uvx/npx for ad-hoc/agent bootstrap) plus pinned recipes for Python (uv add --dev / uv tool install) and Node (npm i -D / npx local); the guide's Validate In CI playbook is rewritten to pin softschema as a consumer dependency (not the repo-relative uv run); the recommendation wording is reused in the README. Reconciles the skill's @latest bootstrap path (stays) with pinned consumer guidance. Shapes the README rework (ss-kkdl).
