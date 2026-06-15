---
type: is
id: is-01ksrxy8j03gb902yraz6reft2
title: "[deferred] Clarify packages/python/README.md vs root README for PyPI users"
kind: task
status: closed
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:55:09.247Z
updated_at: 2026-06-15T17:50:48.837Z
closed_at: 2026-06-15T17:50:48.837Z
close_reason: packages/python/README.md is now a short PyPI-focused entry point (install + correct minimal quickstart + links), not a duplicate of the root README; pyproject still uses the root README as long_description.
---
Audit P2.16. packages/python/README.md is shown on PyPI even though pyproject.toml uses the root README as the long_description. The sub-README content may confuse readers landing on the wheel page. Decide whether to delete the sub-README, slim it to a pointer to the root README, or rewrite as a PyPI-focused entry point. Not release-blocking; pure first-impression polish.
