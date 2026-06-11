---
type: is
id: is-01kttea6nky74a0g5etzctd972
title: "Rework PR #8 onto post-review main (doctor, runner ladder, brief-from-source)"
kind: task
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-11T04:16:13.991Z
updated_at: 2026-06-11T04:27:26.738Z
closed_at: 2026-06-11T04:27:26.737Z
close_reason: "PR #8 reworked onto post-review main (cd6019c), aligned with latest cli-agent-skill-patterns guideline, CI green"
---
PR #8 (skill setup improvements) conflicts with main after PR #9: --version and TS help epilog already landed; golden updates predate the Node+Bun corpus. Rework on branch codex/softschema-skill-validation-pr: merge main, keep doctor [--json] (unit-tested per language; excluded from byte-parity corpus because output is environment-dependent), $SS runner ladder in SKILL.md, skill --brief derived from marked SKILL.md section (regenerate the corpus brief block), README/installation quick-start text; drop the stray .tbd/config.yml rename. Full gauntlet before push. Relates to ss-s0lt (Phase 4 skill hardening).
