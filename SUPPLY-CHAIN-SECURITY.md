# Supply-Chain Security

softschema publishes one Python package and one npm package from the same protected Git
tag. The release boundary is designed so package-registry credentials cannot influence
the build and source-controlled code cannot run after a job receives registry identity.

## Release Boundary

The publish workflow accepts only stable `vX.Y.Z` and release-candidate `vX.Y.Z-rc.N`
tags. A publishing tag must be protected, point to a commit reachable from `main`, and
match the logical, Python, and npm coordinates in `release-metadata.json`.

The unprivileged preflight job then:

1. installs the frozen Python dependency set from a cold cache with sdist builds
   disabled, then installs the reviewed checkout, and installs the frozen TypeScript
   dependency set without lifecycle scripts;
2. validates and tests the source, audits the frozen Python environment for every known
   advisory, and audits the Bun dependency graph at `moderate` severity or higher;
3. creates a deterministic conformance archive and source-derived build identity;
4. embeds the same release and build metadata bytes in the sdist, wheel, and npm
   tarball;
5. builds each package once with pinned tools and hash-locked Python build dependencies;
6. resolves a cold npm artifact consumer with pinned npm, an exact 14-day cutoff, and
   lifecycle scripts disabled, then audits and records its exact package lock;
7. creates an SPDX SBOM and an external manifest owning the primary artifact digests;
   and
8. recursively checksums and uploads one immutable same-run transfer.

An unprivileged job downloads and verifies the complete checksum inventory before any
candidate installation, then installs and executes those exact bytes from an unrelated
directory. The ordinary CI artifact matrix follows the same build-once transfer pattern
across its Python, Node, Bun, and operating-system combinations.
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
- `pip-audit==2.10.0` is itself installed from `uv.lock`; pinned Bun supplies its audit
  implementation. The Python tool and its msgpack security floor live in a dedicated
  `audit` dependency group that only the audit and publish-preflight jobs install;
  ordinary build, golden, and artifact jobs do not carry the audit toolchain.
  Python has no common severity value across the selected advisory source, so any known
  Python vulnerability fails.
  Bun and the npm artifact consumer fail on moderate, high, or critical advisories.
  Collection or audit failures also fail; there is no best-effort downgrade.
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

Published libraries and reproducible development environments have different version
policies:

- Python runtime requirements carry a reviewed minimum and an incompatible-major or
  incompatible-minor upper bound.
  This lets consumers receive compatible fixes without claiming support for an untested
  future line.
- npm runtime requirements retain caret ranges for the same compatible-update behavior.
- Development and audit inputs are exact lockfile resolutions.
  Build requirements are additionally version- and hash-pinned in
  `build-constraints.txt`.

Python CI pins uv 0.11.21 and separates trusted local construction from third-party
installation:

1. Build the local wheel with `build-constraints.txt` and `--require-hashes` before
   enabling the install prohibition.
2. Run `UV_NO_BUILD=1 uv sync --frozen --no-cache --no-install-project` so every
   third-party dependency must have a locked wheel.
   `--no-cache` is mandatory because uv may otherwise reuse a locally built wheel while
   `--no-build` is set.
3. Install the exact local wheel with
   `UV_NO_BUILD=1 uv pip install --no-build --no-deps`.
4. Before tests import it, verify that `direct_url.json` names that wheel and that every
   installed file’s size and SHA-256 digest match the wheel’s `RECORD`. Then run all
   commands with `uv run --no-sync` so uv cannot replace the verified environment.

The release preflight applies the same cold-cache, no-sdist rule to third-party
dependencies, then installs the reviewed checkout as an explicit local exception.
This preserves the rule that source-derived build identity exists before either
publishable package is built.
The candidate wheel is subsequently built once and its installed bytes pass the same
verifier in the unprivileged smoke job.

The npm artifact consumer is also resolved exactly once in the unprivileged builder:

1. Require the npm version bundled with the pinned release Node runtime.
2. Compute and record an exact UTC cutoff at least 14 days old.
3. Resolve only `file:../<candidate>.tgz` with
   `npm install --package-lock-only --ignore-scripts --before=<cutoff>` in a sanitized
   npm environment.
4. Reject every local, Git, HTTP, credentialed, or unintegrity-protected transitive
   entry. The sole local entry must match the candidate tarball’s SHA-512 integrity;
   every other entry must have an exact version, npmjs.org HTTPS URL with no explicit
   port, and SHA-512 integrity.
5. Run `npm audit --package-lock-only --audit-level=moderate` without suppressing its
   exit status.
6. Transfer the consumer manifest, lockfile, policy record, tarball, and recursive
   checksums together. Each downstream job revalidates them and runs
   `npm ci --ignore-scripts`; it never resolves dependency versions again.

The policy record owns the resolver version, cutoff, registry, resolution/install/audit
flags, tarball digests, and manifest/lockfile digests.
Ambient npm environment and user/global configuration are excluded from resolution and
installation.

The skill conformance dependency is the hash-locked `skills-ref==0.1.1` wheel rather
than a Git source dependency.
Its validator matches agentskills commit `38a2ff82958afee88dadf4831509e6f7e9d8ef4e`
(reviewed 2026-07-09); the wheel adds explicit UTF-8 reads and the corrected package
version.
A compatibility test pins its registry URL, wheel digest, size, upload time, and
the exact allowed `uv.lock` cool-off exceptions.

## Primary References

- npm documents the
  [`before` resolver cutoff](https://docs.npmjs.com/cli/v11/using-npm/config/),
  [`--package-lock-only`](https://docs.npmjs.com/cli/v11/commands/npm-install/), frozen
  [`npm ci`](https://docs.npmjs.com/cli/v11/commands/npm-ci/), and lockfile
  [`resolved` and `integrity` fields](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/).
- PyPA documents the
  [`pip-audit` environment, strict collection, and exit-code behavior](https://github.com/pypa/pip-audit).
- Bun documents
  [`bun audit`, severity filtering, and failure exit codes](https://bun.sh/docs/pm/cli/audit).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
