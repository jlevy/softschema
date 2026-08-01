---
type: is
id: is-01kyxfdm15darzr74zeepw4xrv
title: Remove vulnerable fast-uri from the v0.4.0 npm graph
kind: bug
status: closed
priority: 1
version: 8
spec_path: docs/project/specs/done/plan-2026-07-31-softschema-v040-release.md
labels: []
dependencies: []
parent_id: is-01kyxcr75ap5xpcsm46p8edsq7
created_at: 2026-08-01T01:36:05.153Z
updated_at: 2026-08-01T03:09:10.474Z
closed_at: 2026-08-01T02:07:20.587Z
close_reason: "Completed on release commit e21f309: exact frontmatter-format 0.4.0 adoption, fast-uri 3.1.4 security hardening with approved exception, and full local release validation all passed."
---
The final bun audit reports GHSA-4c8g-83qw-93j6 and GHSA-v2hh-gcrm-f6hx against runtime transitive dependency fast-uri >=3.0.0 <3.1.3 through AJV. Verify the patched release and cool-off status, update only the required lock entry, rerun TypeScript checks, package smokes, audit, and release evidence before publication.

## Notes

Approved fix complete: package.json uses an exact root override fast-uri=3.1.4, bun.lock contains only 3.1.4 for Ajv, CI now runs bun audit, and frozen Bun plus clean npm candidate audits report zero vulnerabilities. Clean npm install resolves ajv 8.20.0 -> fast-uri 3.1.4. Reviewed tag 6aeece6, patch 2d50fba, publisher/integrity, and both GHSA records; maintainer approval and exception are documented in changelog, plan, review, and commit/PR record.
