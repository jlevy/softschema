---
type: is
id: is-01kxbt8gw93jc00g40h943cjdn
title: Remove source digest from managed skill marker
kind: task
status: closed
priority: 2
version: 3
labels: []
dependencies: []
created_at: 2026-07-12T18:43:30.824Z
updated_at: 2026-07-12T18:49:15.907Z
closed_at: 2026-07-12T18:49:15.907Z
close_reason: Implemented @latest public runner guidance and simplified managed skill installation to the format marker; full release validation passed.
---
Simplify PR #21 skill installation marker by removing source-sha256. Recognize ownership through the explicit DO NOT EDIT format=f02 marker, refresh marked files, and continue refusing unmarked files.
