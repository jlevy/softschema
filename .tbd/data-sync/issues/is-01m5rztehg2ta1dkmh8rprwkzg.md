---
type: is
id: is-01m5rztehg2ta1dkmh8rprwkzg
title: "PR #59 E3: scheme-less relative root $id with nested relative $id is an unlisted engine difference"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rztad5krc4zxt6mw8qwhw7
hold: null
hold_until: null
created_at: 2026-10-25T07:36:23.343Z
updated_at: 2026-10-25T07:46:09.509Z
started_at: 2026-10-25T07:36:27.824Z
closed_at: 2026-10-25T07:46:09.509Z
close_reason: "fixed in 7aded61: relative root $id refused as resource_identity in both (_check_root_identity/checkRootIdentity), consistent with the absolute-URI resource rule; vectors relative-root-id, absolute-root-id-nested-relative-id, urn-root-id"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5642083634. Fix: refuse relative root $id as resource_identity in both if consistent with spec, else pin.
