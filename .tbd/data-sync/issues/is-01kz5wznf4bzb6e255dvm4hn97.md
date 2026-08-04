---
type: is
id: is-01kz5wznf4bzb6e255dvm4hn97
title: "PR #26: no cache-clearing escape hatch"
kind: feature
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wzknpm4nrrjjjramv3x5d
created_at: 2026-08-04T08:07:03.396Z
updated_at: 2026-08-04T08:11:19.656Z
closed_at: 2026-08-04T08:11:19.655Z
close_reason: clear_validator_cache() exported and covered by a test.
---
Long-lived processes that regenerate schemas cannot drop entries. Expose cache_clear under a public name. (PR #26)
