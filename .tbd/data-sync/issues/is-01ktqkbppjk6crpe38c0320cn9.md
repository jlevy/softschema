---
type: is
id: is-01ktqkbppjk6crpe38c0320cn9
title: Add runner resolution ladder to softschema skill
kind: bug
status: closed
priority: 1
version: 4
labels:
  - skill
  - docs
dependencies: []
created_at: 2026-06-10T01:46:42.769Z
updated_at: 2026-06-10T02:10:57.002Z
---
Developer feedback: the skill Bootstrap section still starts with bare `softschema ...` commands. In a repo where softschema is not on PATH, an agent can dead-end before reaching the Install section. Add an explicit resolution ladder: use `softschema` if present, else `uvx softschema@latest`, else `npx softschema@latest`, else install uv or Node and retry. State that the chosen runner or prefix must be used consistently for every command, and trim the install guidance to one clear recommended path per runtime. Regenerate the .agents and .claude mirrors and keep drift tests passing.

## Notes

Implemented runner selection guidance in the softschema skill, using a single  prefix across commands and pointing agents at doctor for environment checks.
