---
type: is
id: is-01kx4vfebyfym3whq7f3e3x0qs
title: Add batch validation and source-positioned diagnostics
kind: feature
status: in_progress
priority: 2
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - cli
  - diagnostics
  - agents
dependencies:
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:50:05.181Z
updated_at: 2026-07-10T08:25:11.180Z
---
Add deterministic multi-path/recursive discovery under one explicit profile, profile-specific default extensions plus include/exclude globs, canonical display/sort/dedup/symlink rules, diagnostic-v1 aggregate JSON/JSONL, source locations, and SARIF. Preserve exact single-file JSON and enforce 2 input_error > 1 readable failure > 0 success exit precedence.

## Notes

Frozen implementation decisions: columns count Unicode code points; SARIF columnKind=unicodeCodePoints; frontmatter parsing retains exact BOM/CRLF/final-newline substrings; request shape (not post-dedup count) selects legacy versus diagnostic-v1; zero directory matches emit input_error/no_matches and exit 2; invalid globs are usage errors; hidden files participate; explicit regular-file symlinks allowed after target checks, discovered symlinks skipped; global first-identity dedup with device/inode then realpath fallback; no-follow race limitation documented; JSONL has one self-describing record per line and no summary; binding failures continue in diagnostic mode; full official SARIF-schema validation required.
