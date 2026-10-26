---
type: is
id: is-01m5tepthmf61x98axe1nj5s72
title: "PR #59 review H: merge main, Qodo main-side dispositions, deterministic identity order, CHANGELOG refusals"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T21:15:47.636Z
updated_at: 2026-10-25T21:26:39.729Z
closed_at: 2026-10-25T21:26:39.729Z
close_reason: "Review H addressed: merge 0200abe (main 215f4d9, CHANGELOG resolved), fix ec44d76 (H6 code-point identity order + vectors, H7 CHANGELOG refusals, H2 clib pin in wheel smoke), H2 _try_c_parser declined (intended fallback), H3 thread resolved, H5 correction posted. Pushed ec44d76; CI 40235264918 19/19; MERGEABLE. Gate: pytest 533/1 skipped, pure 533/1 skipped, slow 21, lint pass, bun test 454, typecheck/lint:ci/build/publint clean, goldens py 90/ts 85/ts-bun 90, cross-impl OK. H4 not done (owned elsewhere)."
resolution: null
duplicate_of: null
---
Review H (senior, round 6) on https://github.com/jlevy/softschema/pull/59#issuecomment-6403360059: H1 merge origin/main 215f4d9 (CHANGELOG conflict), H2 dispositions for Qodo summary 6394299598 (_try_c_parser except Exception; ci.yml unbounded ruamel.yaml.clib), H3 resolve r4371456789, H5 448 count, H6 deterministic order for invalid nested ids, H7 name common refusals in CHANGELOG. H4 owned elsewhere.
