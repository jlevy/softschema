---
type: is
id: is-01kttt99vzw4djrt56naj92sge
title: TS readFrontmatter should reject non-mapping frontmatter (parity with Python fmf_read)
kind: bug
status: closed
priority: 3
version: 6
spec_path: docs/project/specs/done/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwt2nh1ayey332yy7p5qk
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T07:45:27.423Z
updated_at: 2026-07-10T03:49:22.819Z
---
Pre-existing parity divergence (PR #11 review, my adversarial review Finding 2): a non-mapping YAML frontmatter (e.g. a top-level list) is rejected by Python's fmf_read at read time ('Expected YAML metadata to be a dict, got <class list>', exit 2 via the CLI boundary), but TS readFrontmatter returns {hasFence:true, value:<list>}, so the CLI's inferEnvelope runs Object.keys over the list and emits 'multiple top-level frontmatter keys (candidates: 0, 1)'. Both exit 2 but the wording and conceptual handling differ, and the TS message is nonsensical. Proper fix: make readFrontmatter raise on a non-mapping parse to match Python; this also affects validateArtifact's frontmatter_not_mapping path, so do it golden-first with a shared scenario and reconcile the existing frontmatter_not_mapping test/library kind. Out of scope for the PR #11 review (pre-existing, LOW).
