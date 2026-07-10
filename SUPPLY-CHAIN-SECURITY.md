# Supply-Chain Security

softschema publishes one Python package and one npm package from the same protected Git
tag. The release boundary is designed so package-registry credentials cannot influence
the build and source-controlled code cannot run after a job receives registry identity.

## Release Boundary

The publish workflow accepts only stable `vX.Y.Z` and release-candidate `vX.Y.Z-rc.N`
tags. A publishing tag must be protected, point to a commit reachable from `main`, and
match the logical, Python, and npm coordinates in `release-metadata.json`.

The unprivileged preflight job then:

1. installs the frozen Python and TypeScript dependency sets;
2. validates and tests the source;
3. creates a deterministic conformance archive and source-derived build identity;
4. embeds the same release and build metadata bytes in the sdist, wheel, and npm
   tarball;
5. builds each package once with pinned tools and hash-locked Python build dependencies;
6. creates an SPDX SBOM and an external manifest owning the primary artifact digests;
   and
7. uploads one immutable same-run transfer.

An unprivileged job downloads, verifies, installs, and executes those exact bytes from
an unrelated directory.
Only then can the `pypi` and `npm` environment jobs request an OIDC identity.
Those jobs do not check out source, install project dependencies, build, or run package
lifecycle scripts.

Manual workflow dispatches exercise the entire build and smoke path but cannot publish.

## Source-Controlled Controls

- Every third-party action is pinned to a full commit SHA with a reviewed-version
  comment.
- `build-constraints.txt` pins every Python build dependency and acceptable distribution
  hash. Release builds use `uv build --require-hashes`.
- `bun.lock` and `uv.lock` are installed frozen.
- `CODEOWNERS` identifies workflows, build constraints, lockfiles, release metadata, and
  release tooling as maintainer-owned review surfaces.
  In this single-maintainer repository it is advisory; required CI and pull-request
  rules are the enforceable merge gates.
- Dependabot proposes grouped updates for GitHub Actions, uv, and npm.
  Reviewers must re-establish the release-age policy and verify upstream source before
  accepting an update; automation does not merge dependency updates.
- Package allowlists and installed-artifact smoke tests reject internal planning state,
  stale generated files, and source-checkout-dependent resources.

The PyPI publishing action is pinned, but its upstream action currently derives a
container from a floating official Python image.
PyPI recommends the action and its OIDC protocol is intentionally not reimplemented
here. Treat that transitive image as a documented residual risk and review it whenever
the action pin changes.

## Required GitHub and Registry Settings

Source control cannot fully describe these controls.
Repository administrators must keep the following live settings aligned with the
workflow:

- Protect `main`; require pull requests, required CI checks, conversation resolution,
  and no force pushes or deletions.
- Protect `v*` tags so only release maintainers can create or update them.
- Require full-length SHA pins for GitHub Actions and allow only the action owners used
  by the workflows.
- Configure `pypi` and `npm` environments to accept only protected `v*` tags, require
  maintainer approval where the repository plan supports it, and disallow bypass.
- Configure PyPI and npm trusted publishers for `jlevy/softschema`, workflow
  `publish.yml`, and the matching `pypi` or `npm` environment claim.
  Grant the npm publisher only package-publish authority.
- Enable the dependency graph, Dependabot alerts, secret scanning, and push protection.

Before a release, compare these settings with the checklist in
[Publishing](docs/publishing.md).
A missing environment, tag rule, or trusted-publisher claim is a release blocker, not a
reason to widen workflow permissions.

## Dependency Policy

Routine development honors the reviewed `exclude-newer` cutoff in `pyproject.toml`. This
reduces exposure to newly compromised releases but does not make floating package
selectors safe for every consumer: a consumer controls its own resolver, cache, and
policy. Agent bootstrap instructions therefore derive immutable ecosystem-specific pins
from release metadata; every advertised executable bootstrap command uses those pins.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
