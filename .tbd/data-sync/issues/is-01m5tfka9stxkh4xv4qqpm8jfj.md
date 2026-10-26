---
type: is
id: is-01m5tfka9stxkh4xv4qqpm8jfj
title: Make the TypeScript bun test suite hermetic (no in-place rebuild of dist/, measured timeouts)
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T21:31:21.273Z
updated_at: 2026-10-25T21:43:54.785Z
closed_at: 2026-10-25T21:43:54.784Z
close_reason: "Fixed in PR #68 (https://github.com/jlevy/softschema/pull/68), head 7e37bdef463cb8580ebd153795035e47a42a1f09, all CI checks green, Qodo: no issues. Root cause 1: standalone.test.ts and library-entrypoint.test.ts ran 'bun run build' in beforeAll, which deletes then rewrites the shared dist/ and resources/ (bunup clean, copy-resources rmSync), racing every concurrent reader; reproduced on main with 3 parallel bun test runs under a CPU hog (spawned CLIs exited 1 or 0). Root cause 2: CPU-bound 'shared enforcement semantics' takes 1.4-1.8 s idle and up to 7.3 s under contention, past Bun's 5 s default (12 of 18 stressed runs). Fix: per-file private build under node_modules/.cache (test/built-package.ts), file-scoped setDefaultTimeout(30s) for spawn-heavy files, scoped 30 s timeouts with recorded measurements for the enforcement and identity-acceptance tests. Evidence: from clean dist, 10/10 sequential bun test runs pass with 454 tests each; 3/3 parallel runs under yes x nproc pass with 454 each while a loop rebuilt dist 40 times; Bun 1.3.11 alone, with coverage, and 3x parallel under hog all pass with 454; typecheck, lint:ci, build, publint pass; goldens ts 85 passed, ts-bun 90 passed."
resolution: null
duplicate_of: null
---
standalone.test.ts and library-entrypoint.test.ts each ran 'bun run build' in beforeAll, which deletes and rewrites the shared dist/ and resources/ (bunup clean, copy-resources rmSync) while the golden runner, cross-impl-diff.sh, or a concurrent bun test read them. Separately, src/enforced.test.ts 'shared enforcement semantics' (~1.4 s idle) exceeds Bun's 5 s default under CPU contention. Fix: private per-file build under node_modules/.cache, file-scoped spawn timeouts, and a scoped measured timeout for the CPU-bound test. Branch claude/hermetic-bun-test.
