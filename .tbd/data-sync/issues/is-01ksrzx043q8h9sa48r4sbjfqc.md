---
type: is
id: is-01ksrzx043q8h9sa48r4sbjfqc
title: "CI: switch to --frozen install + add pip-audit"
kind: task
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:24.995Z
updated_at: 2026-05-29T04:29:43.100Z
closed_at: 2026-05-29T04:29:43.099Z
close_reason: ci.yml and publish.yml install with --frozen --all-extras and run uvx --from 'pip-audit>=2.7' pip-audit --strict before lint/test/build. Local verification clean ('No known vulnerabilities found').
---
Per supply-chain-hardening rules 3 and 4: install frozen ('uv sync --frozen --all-extras' in ci.yml and publish.yml) and audit after install ('uvx --from pip-audit>=2.7 pip-audit --strict' as a CI step). Catches lockfile drift and surfaces any CVE-flagged dependency before tests/build.
