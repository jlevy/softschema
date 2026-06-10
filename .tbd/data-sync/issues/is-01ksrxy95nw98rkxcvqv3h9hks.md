---
type: is
id: is-01ksrxy95nw98rkxcvqv3h9hks
title: "[deferred] Add 'softschema prime' command for full-context restoration"
kind: task
status: open
priority: 3
version: 1
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:55:09.876Z
updated_at: 2026-05-29T03:55:09.876Z
---
Audit P2.19. cli-agent-skill-patterns suggests a 'prime' command that prints all the context an agent needs to operate on the package (skill, guide, spec, example index). Optional for a small CLI; would be useful when softschema becomes a transitive dep that an agent encounters without the source checkout.
