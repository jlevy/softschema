---
type: is
id: is-01ktsqtgepqntfmsj8k9hjekr4
title: "P4: Skill hardening (marker format/version stamp, allowed-tools, git-root awareness, @latest justification)"
kind: task
status: in_progress
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:43:11.061Z
updated_at: 2026-06-11T06:20:33.676Z
---
FILE SCOPE: skills/softschema/SKILL.md, cli.py/.ts skill install, test_cli.py.
- Stamp format+version on the DO NOT EDIT marker (wire the currently dead <version> substitution OR delete it AND the vacuous '<version> not in output' assertions).
- allowed-tools: ['Bash(softschema:*)'] in SKILL.md frontmatter.
- skill --install: git-root awareness (walk up to .git, or warn when absent) instead of bare cwd.
- Carry the @latest cool-off justification (or a pin) in the skill text itself.
Refs review Skill MEDIUM(version stamp, dead <version>), LOW(allowed-tools, git-root, @latest).
