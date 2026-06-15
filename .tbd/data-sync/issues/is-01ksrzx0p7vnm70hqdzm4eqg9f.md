---
type: is
id: is-01ksrzx0p7vnm70hqdzm4eqg9f
title: "[deferred] Enable UV_NO_BUILD once uv supports per-package allowlist for workspace pkg"
kind: task
status: open
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:25.574Z
updated_at: 2026-06-15T17:49:34.840Z
---
Audit P3. supply-chain-hardening recommends UV_NO_BUILD=1 to refuse sdist installs. As of uv 0.11.x, setting it globally blocks our own editable install ('softschema can't be installed because it is marked as --no-build but has no binary distribution') and uv has no inverse 'build-package' override. Revisit when uv adds such an override, or move CI to install from the built wheel rather than editable.

## Notes

v0.2.2 recheck: uv 0.8.x still exposes only --no-build / --no-build-package (and isolation variants) and NO inverse --build-package, so a global UV_NO_BUILD=1 still breaks our own editable install with no per-package allowlist. Unfixable in our code until uv adds the override. The alternative (install from the built wheel in CI instead of editable) is a non-trivial workflow change — editable installs let the test suite import packages/python/src directly — so it is deferred, not done in this patch. Remains blocked-upstream.
