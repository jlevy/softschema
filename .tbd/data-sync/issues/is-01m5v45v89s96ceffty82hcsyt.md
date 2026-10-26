---
type: is
id: is-01m5v45v89s96ceffty82hcsyt
title: "Skill: document opt-in narrow pre-approval for the uvx and npx fallback runners (GitHub #61)"
kind: task
status: open
priority: 3
version: 1
labels: []
dependencies: []
created_at: 2026-10-26T03:30:59.977Z
updated_at: 2026-10-26T03:30:59.977Z
---
GitHub issue #61 (https://github.com/jlevy/softschema/issues/61), open since 2026-10-24 and filed by the maintainer.

The problem, still present at v0.9.0: `skills/softschema/SKILL.md` (and its `.claude/` and `.agents/` mirrors) picks `softschema` first, then `uvx softschema@latest` (line 31), then `npx -y softschema@latest` (line 32). Its `allowed-tools` (line 8) names only `Bash(softschema:*)`. In a fresh environment, choosing a documented fallback runner prompts for permission even when the native command was pre-approved.

The issue asks for:

- A documented or generated, host-appropriate way to opt in to narrow pre-approval of exactly those runner prefixes.
- No broad permission for generic uv, brew, curl, or arbitrary package execution, and no silent rewrite of project permissions.
- A test that the runner prefixes the skill selects agree with the narrow allow-rule examples.

The issue says this can wait for a later skill refresh. The skill sources and mirrors are generated together (`make format` reinstalls the mirrors), so edit `skills/softschema/SKILL.md` and regenerate. Close the issue with the PR.
