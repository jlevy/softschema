---
type: is
id: is-01m5sv1a8sn7ksv0kr1v2wrfeb
title: "PR #64 B2: Python repair with schema binding folds raw NEL via round_trip_yaml without preflight"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:31:59.897Z
updated_at: 2026-10-25T16:25:54.339Z
closed_at: 2026-10-25T16:25:54.339Z
close_reason: "Fixed in a7c00d9 (PR #64): conform runs check_portable_text/checkPortableText on the region before the round-trip load in both runtimes (skipped_reason unparsable); unit test per runtime; repair.tryscript.md next-line journey (later updated in b36cf2e to show the escape + conform result) pins py/ts/ts-bun."
resolution: null
duplicate_of: null
---
High. conform.py:298-302, pipeline.py:86-98. Put portable reader in front of conform load + golden.
