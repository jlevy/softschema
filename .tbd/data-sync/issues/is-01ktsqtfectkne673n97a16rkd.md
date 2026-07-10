---
type: is
id: is-01ktsqtfectkne673n97a16rkd
title: "P4: Doc refresh for the TypeScript port (guide, python-design, plan disposition, publishing, AGENTS footer, CI pins)"
kind: task
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:43:10.028Z
updated_at: 2026-07-10T03:49:18.324Z
closed_at: 2026-06-11T06:33:19.788Z
close_reason: null
---
FILE SCOPE: docs/softschema-guide.md, docs/softschema-python-design.md, docs/project/specs/active/plan-2026-05-24-*, docs/publishing.md, docs/publishing-npm.md, AGENTS.md, docs/development.md.
- guide: 'What Softschema Is' (not Python-only), rename/extend 'Relationship To The Python Package', Further Reading + TS design link, add 'softschema generate' to the CLI list, fix 'a SoftField'.
- python-design: drop 'stage' from module table (SchemaStage gone), update 'future TypeScript port' wording, remove TS from Accepted/Deferred, fix duplicate 'contract' word.
- mark plan-2026-05-24-public-readiness superseded (it describes a pre-TS world while Complete).
- publishing.md: rewrite First-npm-Publish to present state; link publishing-npm.md.
- AGENTS.md: remove duplicate doc-guidelines footer.
- development.md: bump the example GH Actions pins to match the repo's own CI (checkout v6, setup-uv v8).
Refs review Documentation Review (HIGH F4.1/F4.2/F5.1, MEDIUM F4.4/F4.5).
