# Publishing

softschema ships two packages that release **together, under the same version number**:

- **PyPI**: `softschema` (Python/Pydantic), built from `packages/python`.
- **npm**: `softschema` (TypeScript/Zod), built from `packages/typescript`.

A single `vX.Y.Z` Git tag drives both.
The Python wheel and sdist derive their version from the tag via
`uv-dynamic-versioning`; the npm package carries the same version in
`packages/typescript/package.json`. Creating a GitHub release for the tag triggers
[`publish.yml`](../.github/workflows/publish.yml), which publishes both packages (Python
to PyPI and TypeScript to npm) via **trusted publishing (OIDC)** in the same run.
No API tokens are stored in the repo.

## Versioning Convention

- **The two packages always share one version.** Bump `packages/typescript/package.json`
  to `X.Y.Z` in the same commit that prepares the release, so the npm version matches
  the Git tag the Python build derives.
  CI verifies this match before publishing and fails the release on a mismatch.
- **Zero-install examples use an exact last-verified version.** After registry and
  package smoke tests pass, update the pin in the README, installation guide, source
  skill, and both CLI help epilogs.
  Never use an unpinned agent bootstrap command.
- The committed skill mirrors under `.agents/` and `.claude/` are regenerated with the
  explicit project-scope install command; a drift test keeps them in sync with the
  source.
- Patch bumps (`0.1.Z`) cover docs-only changes and small additive features.
  Reserve minor bumps (`0.Y.0`) for changes that meaningfully shift the API or spec.

## Trusted Publishing

Both registries authenticate via OIDC from `publish.yml`; there are **no `*_TOKEN`
secrets** to manage or rotate.
Each is configured once:

**PyPI** (project-level trusted publisher):

- project name: `softschema`
- owner/repo: `jlevy/softschema`
- workflow: `publish.yml`

**npm** (package-level trusted publisher, configured at npmjs.com → `softschema` →
Settings → Trusted Publishing):

- owner/repo: `jlevy/softschema`
- workflow: `publish.yml`

The npm job requests an OIDC `id-token`, runs npm ≥ 11.5.1, and publishes with
`npm publish --access public --provenance`; both auth and the provenance attestation are
OIDC-based, so no token is involved.

## npm Trusted Publishing

Both packages publish automatically from the release workflow over OIDC, with provenance
and no stored token.
npm’s trusted publisher is configured on `jlevy/softschema` → workflow `publish.yml`, so
a tagged release publishes PyPI and npm in one run.

The one-time bootstrap that claimed the npm name and configured trusted publishing has
already been done; the full runbook (for reference, or if the package ever needs
re-bootstrapping) lives in [Publishing npm (bootstrap runbook)](publishing-npm.md).

## Release Checklist

A release is **staged through a pull request**, not pushed straight to `main`: that way
CI runs the full matrix (lint, both test suites, the golden corpus on every runtime, and
the cross-impl parity diff) against the exact tree that will be tagged, before anything
is published. The tag is created on the merge commit only after that PR is green and
merged.

For each release of version `X.Y.Z`:

1. **Branch from `main`:** `git checkout -b claude/release-X.Y.Z`.

2. **Set both package versions to `X.Y.Z`.** Edit `packages/typescript/package.json`
   `"version"` to `X.Y.Z` (the Python version is derived from the tag, so it needs no
   file edit). The two must match or the npm publish step aborts.
   Bump any docs that pin the version (`installation.md`, the guide, README) in the same
   commit.

3. **Run the full validation pass** from the
   [end-to-end testing runbook](e2e-testing.runbook.md): the local automated sweep
   (Phase 1, which mirrors CI) plus the manual phases CI cannot cover —
   clean-environment installs of the wheel and npm tarball, the quickstart as written,
   and the skill bootstrap (Phases 2–4). Everything must exit 0.

4. **Open the release PR and merge once CI is green.** Push the branch, open a PR
   (`release: bump to X.Y.Z`), and wait for every required check to pass before merging
   to `main`. CI on the PR is the gate; do not tag a tree CI has not validated.

5. **Tag the merge commit on `main` and push the tag.** The working tree must be clean
   and the tag must sit on the merged release commit, so the Python version derived from
   git is exactly `X.Y.Z` (the publish workflow’s tag-vs-build guard fails otherwise):

   ```bash
   git checkout main && git pull origin main
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin vX.Y.Z
   ```

   If the environment blocks pushing tags over git (some hosted or proxied checkouts
   allow branch pushes but reject tag refs with a `403`), skip the `git push` and let
   the next step create the tag: passing `--target` with the merge-commit SHA to
   `gh release create` creates the tag at that commit as part of publishing the release.

6. **Create the GitHub release** (this triggers the publish workflow, which publishes to
   both PyPI and npm over OIDC in one run):

   ```bash
   gh release create vX.Y.Z --title "softschema X.Y.Z" --notes-file notes.md
   # when the tag was not pushed in step 5, create it here at the merge commit:
   gh release create vX.Y.Z --target MERGE_SHA --title "softschema X.Y.Z" --notes-file notes.md
   ```

   Write the notes from the release’s behavior and breaking changes (see prior releases
   for the shape: a one-line summary, then sections for breaking changes, new features,
   fixes and hardening, and testing and release safety).
   Use a notes file for multi-section notes; the inline `--notes` flag is fine only for
   a one-liner.

7. **Watch the workflow** until both `Publish to PyPI` and `Publish to npm` report
   success:

   ```bash
   gh run watch <run-id> --exit-status
   ```

8. **Verify both registries** have the new version, then smoke-test the published
   artifacts (end-to-end runbook Phase 5):

   ```bash
   cd /tmp                                   # outside the repo: do not inherit its [tool.uv] cool-off
   ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"       # cutoff = now, so a same-day publish is included
   uvx --refresh --exclude-newer-package "softschema=$ts" softschema@X.Y.Z --version
   npx -y softschema@X.Y.Z --version
   ```

   The `--exclude-newer-package` override is needed because a freshly published version
   sits inside the 14-day supply-chain cool-off; anyone consuming it under that policy
   sees the same friction for ~14 days, which is intentional.
   Three details matter for the smoke test: use a full timestamp at the current moment
   (a date-only `$(date +%F)` is midnight UTC and excludes a version published later the
   same day), run from outside the repo so uv does not apply the project’s own cool-off,
   and pass `--refresh` so uv does not serve a cached index that predates the publish
   (see runbook Phase 5).

   Allow for publish propagation: PyPI updates its JSON API
   (`pypi.org/pypi/softschema/json`) before the **simple index** uv resolves against
   (`pypi.org/simple/softschema/`), so the first `uvx` run right after the workflow
   turns green can fail with `no version of softschema==X.Y.Z` even though the release
   is live. `--refresh` clears uv’s own cache but not PyPI’s CDN edge, so if that
   happens, wait for the simple index to list the new `.whl`/`.tar.gz` and retry
   (usually a few seconds).
   npm propagates quickly and rarely shows this gap.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
