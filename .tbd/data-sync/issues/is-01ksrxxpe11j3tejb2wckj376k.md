---
type: is
id: is-01ksrxxpe11j3tejb2wckj376k
title: Replace cli._dev_repo_root parents[4] fallback with explicit raise
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:54:50.688Z
updated_at: 2026-07-10T03:49:08.089Z
closed_at: 2026-05-29T03:55:22.270Z
close_reason: cli._dev_repo_root now raises RuntimeError when the upward pyproject.toml search fails instead of returning parents[4]. Tests pass.
---
cli._dev_repo_root used Path(__file__).resolve().parents[4] as a magic-number fallback when the upward pyproject.toml search failed. Replace the fallback with a RuntimeError so misconfiguration surfaces immediately rather than masquerading as an unrelated file-not-found.
