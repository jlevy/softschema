---
type: is
id: is-01kyx92qar1jne3qgxgk8hnn90
title: Update the spec, guide, and package design docs
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - documentation
dependencies:
  - type: blocks
    target: is-01kyx92x7k2x1ht64n0r3gr05f
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:45:16.631Z
updated_at: 2026-07-31T23:48:16.199Z
closed_at: 2026-07-31T23:48:16.198Z
close_reason: The spec, guide, both package design docs, prior-plan pointer, and delivery-epic linkage match implemented behavior and pass documentation, spelling, formatting, type, and footer checks.
---
Apply the documentation ownership matrix under common-doc-guidelines. Put normative portable decoding and annotation-only format rules in the spec; user migration, model guidance, raw-value behavior, and Zod sidecar regeneration in the guide; scoped ruamel constructor and no FormatChecker in Python design; yaml parser behavior, Date guard, Ajv setting, and targeted Zod override in TypeScript design. Correct frontmatter parser ownership and add a supersession pointer to the v0.3 hardening plan. Keep README and unrelated examples unchanged. Acceptance: present-state wording, low-context orientation, concise cross-links, Title Case headings, standard footers, and no duplicate ownership.

## Notes

All documentation surfaces in the ownership matrix are updated. The plan now points to the delivery epic; running the documentation and claim checks.
