---
type: is
id: is-01m5t0wzc75j754e1btwkp6ryn
title: "PR #62 E5: local mirror-CI commands leave out the pure-parser pass"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0wx1zedsf15d8pn6cwkqx
created_at: 2026-10-25T17:14:29.127Z
updated_at: 2026-10-25T17:23:40.189Z
closed_at: 2026-10-25T17:23:40.188Z
close_reason: "fixed in 9f6cb2b: runbook Phase 1 + CI table row, Makefile test-pure (make test runs all three), development.md pure commands"
resolution: null
duplicate_of: null
---
Low. runbook:33, :59-60; Makefile:82-88; development.md:47-48. Add SOFTSCHEMA_PURE_YAML=1 runs of both tiers; table row 'both tiers, C-first and pure'; development.md 'the default tier (add -m slow for the rest)'; optional make test-pure. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5644280692
