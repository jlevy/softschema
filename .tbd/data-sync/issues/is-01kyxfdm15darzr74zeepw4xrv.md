---
type: is
id: is-01kyxfdm15darzr74zeepw4xrv
title: Remove vulnerable fast-uri from the v0.4.0 npm graph
kind: bug
status: in_progress
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-31-softschema-v040-release.md
labels: []
dependencies: []
parent_id: is-01kyxcr75ap5xpcsm46p8edsq7
created_at: 2026-08-01T01:36:05.153Z
updated_at: 2026-08-01T01:38:13.127Z
---
The final bun audit reports GHSA-4c8g-83qw-93j6 and GHSA-v2hh-gcrm-f6hx against runtime transitive dependency fast-uri >=3.0.0 <3.1.3 through AJV. Verify the patched release and cool-off status, update only the required lock entry, rerun TypeScript checks, package smokes, audit, and release evidence before publication.

## Notes

Release audit found fast-uri 3.1.2 through AJV. GitHub advisories GHSA-4c8g-83qw-93j6/CVE-2026-13676 and GHSA-v2hh-gcrm-f6hx/CVE-2026-16221 both rate high (CVSS 7.5); Bun's summary understates the second affected range, which includes 3.1.3. Minimum safe AJV-compatible version is 3.1.4, published 2026-07-19T07:42:54.497Z by established maintainer Matteo Collina with integrity sha512-8JnbkQ4juDyvYs4mgFGQqg4yCYtFDtUtmp2QIQq11ZZe5CFQ5wcqm1rqDgAh/QdMySuBnPzMUiJUNZG5N/AiQw==. Reviewed source tag v3.1.4 at 6aeece6 and patch 2d50fba; change rejects literal backslashes in URI authority and adds focused regression tests. Version is still about 30 hours short of the 14-day cool-off, so a human-approved security exception is required before updating the lock.
