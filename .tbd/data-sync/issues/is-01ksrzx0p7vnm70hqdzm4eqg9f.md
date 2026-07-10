---
type: is
id: is-01ksrzx0p7vnm70hqdzm4eqg9f
title: "[deferred] Enable UV_NO_BUILD once uv supports per-package allowlist for workspace pkg"
kind: task
status: closed
priority: 3
version: 7
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels: []
dependencies: []
parent_id: is-01kx4scewbgn5d6afebgxd3hha
created_at: 2026-05-29T04:29:25.574Z
updated_at: 2026-07-10T07:18:26.393Z
closed_at: 2026-07-10T07:18:26.392Z
close_reason: Implemented and verified in 99d5250
---
Audit P3. supply-chain-hardening recommends UV_NO_BUILD=1 to refuse sdist installs. As of uv 0.11.x, setting it globally blocks our own editable install ('softschema can't be installed because it is marked as --no-build but has no binary distribution') and uv has no inverse 'build-package' override. Revisit when uv adds such an override, or move CI to install from the built wheel rather than editable.

## Notes

v0.2.2 recheck: uv 0.8.x still exposes only --no-build / --no-build-package (and isolation variants) and NO inverse --build-package, so a global UV_NO_BUILD=1 still breaks our own editable install with no per-package allowlist. Unfixable in our code until uv adds the override. The alternative (install from the built wheel in CI instead of editable) is a non-trivial workflow change — editable installs let the test suite import packages/python/src directly — so it is deferred, not done in this patch. Remains blocked-upstream.

2026-07-09 audit: retained and reparented to ss-o21w. The installed uv 0.11.21 still exposes only --no-build and --no-build-package, with no inverse per-package build allowlist, so global UV_NO_BUILD still conflicts with this workspace's editable package. ss-o21w owns dependency policy, immutable wheel/sdist construction, and clean installed-artifact tests; it must either adopt a wheel-first CI path or record why the global setting remains inapplicable.
