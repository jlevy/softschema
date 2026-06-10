---
type: is
id: is-01ksrmbd2yvw5yrqw1r2tjhgts
title: Restore strif for atomic file writes
kind: task
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T01:07:34.109Z
updated_at: 2026-05-29T01:22:01.800Z
closed_at: 2026-05-29T01:22:01.799Z
close_reason: Strif restored as runtime dep (>=3.0,<4); compile.py and generate.py refactored to use strif.atomic_output_file; all 63 tests pass; lint clean; wheel builds.
---
Restore strif as a runtime dependency and route all package file writes through it for atomicity. Background: strif was dropped from runtime deps during the standalone extraction in favor of inline tempfile + Path.replace patterns. Per project policy, all file writes should be atomic, and strif is the right vehicle (zero deps at 3.1.0, safe addition when pinned). Concrete write sites to convert: (1) packages/python/src/softschema/compile.py lines 111-120 currently roll their own tempfile+rename for the schema sidecar write; replace with strif.atomic_output_file or equivalent. (2) packages/python/src/softschema/generate.py line 131 uses path.write_text(new_text) for the in-place regenerate; this is NOT atomic today and risks leaving a partially-written Markdown file on crash. Replace with strif. Acceptance: strif pinned in pyproject.toml runtime deps; compile.py and generate.py write atomically via strif; tests still pass; lint clean; rebuild and verify the wheel still ships correctly.
