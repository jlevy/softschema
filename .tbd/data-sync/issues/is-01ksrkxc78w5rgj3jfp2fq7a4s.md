---
type: is
id: is-01ksrkxc78w5rgj3jfp2fq7a4s
title: Document no-envelope validate-root signal in spec
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T00:59:54.471Z
updated_at: 2026-05-29T01:22:02.175Z
closed_at: 2026-05-29T01:22:02.174Z
close_reason: Documented in docs/softschema-spec.md (#Validating the frontmatter root under Envelope Selection) and in docs/softschema-python-design.md (#Validating the frontmatter root under Validation). Spec pin only; CLI flag deferred per review note that spec pin is sufficient.
---
Upstream consumer review (2026-05-28) flagged that envelope_key=None on SoftschemaBinding defaults to frontmatter_root (excluding softschema:), but this is implicit. The spec only describes the 'exactly one non-softschema top-level key is the envelope' case. For artifacts with multiple top-level keys that want whole-frontmatter validation, callers have no explicit way to express that beyond relying on the implicit default. Action: (1) Document in docs/softschema-spec.md the rule for envelope resolution when there is no single non-softschema top-level key (i.e., pin the current default behavior). (2) Decide whether to add a CLI flag for softschema validate that names this explicitly (e.g., --envelope=root or --no-envelope). Even just the spec pin is sufficient per the review; CLI surface is nice-to-have.
