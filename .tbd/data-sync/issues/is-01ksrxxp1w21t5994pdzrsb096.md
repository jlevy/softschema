---
type: is
id: is-01ksrxxp1w21t5994pdzrsb096
title: Canonicalize doc footers to exact common-doc-guidelines text
kind: task
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:54:50.299Z
updated_at: 2026-05-29T03:55:21.924Z
closed_at: 2026-05-29T03:55:21.923Z
close_reason: Footer text canonicalized to exact common-doc-guidelines.md form across 15 docs + CHANGELOG, SECURITY, CONTRIBUTING; devtools/lint.py accepts only the canonical form and DOC_FOOTER_PATHS extended. Lint passes.
---
Per github.com/jlevy/practical-prose/blob/main/docs/common-doc-guidelines.md the footer must include 'See github.com/jlevy/practical-prose and review guidelines before editing.' on the middle line. Update all 15 existing footer occurrences to canonical text, update devtools/lint.py to expect only that text (single accepted form), and add the canonical footer to CHANGELOG.md, SECURITY.md, and CONTRIBUTING.md while extending DOC_FOOTER_PATHS to cover them.
