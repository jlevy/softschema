---
type: is
id: is-01kx9qd9ghwrm3avgkg2vdf0fj
title: "Step 8: Simplify packaged resources, bootstrap, and skill installation"
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - agents
  - installer
dependencies:
  - type: blocks
    target: is-01kx9qd9qmjfhmv9egzc34rwtj
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:12.528Z
updated_at: 2026-07-12T00:17:07.197Z
closed_at: 2026-07-12T00:17:07.196Z
close_reason: Implemented exact resource resolution, explicit safe installer behavior, collision coverage, and exact verified bootstrap guidance.
---
Resolve installed docs/examples/skills only from package resources, with exact source-checkout overrides. Make installer scope and targets explicit, add dry run, refuse unmanaged or modified files, and use atomic replacement without journals, locks, rollback, or repair. Centralize one exact last-verified zero-install bootstrap version. Acceptance: adversarial consumer-collision package smokes and one concise installer behavior matrix pass through both CLIs.
