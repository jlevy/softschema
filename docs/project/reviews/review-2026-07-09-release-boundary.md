# Release-Boundary Risk Review

**Reviewed:** July 9, 2026\
**Scope:** `ss-o21w`, the minimum dual-registry pre-publish boundary\
**Status:** Code complete; registry identity claims and first-run CI validation remain
release gates

## Decision

The revised workflow has a defensible build-once boundary.
An unprivileged job tests source, creates deterministic metadata, builds each package
once, inventories and hashes the primary subjects, generates artifact-specific SPDX
SBOMs, and transfers the result to an unprivileged installed-artifact smoke job.
PyPI and npm jobs receive only the tested transfer and registry OIDC permission.
They do not check out source, resolve project dependencies, rebuild, or execute package
lifecycle scripts.

Do not use this path for a release until the two registry trusted-publisher records have
been re-certified with the `pypi` and `npm` environment claims and one pull request has
established the final required-check context names.
Both registry settings pages required fresh authentication during this review, so their
live claims could not be inspected.

## Threat and Control Review

| Threat | Control | Verification |
| --- | --- | --- |
| Tag or branch without release authority | Active `main` pull-request ruleset; active administrator-only `v*` tag ruleset; workflow checks `github.ref_protected` and peeled-tag reachability from `origin/main` | GitHub API plus workflow tests |
| Mutable third-party workflow code | Every action uses a full commit SHA; repository policy requires SHA pins and allows only GitHub plus the four reviewed external action repositories | GitHub API plus static workflow test |
| Dependency substitution during the build | Frozen runtime locks; build backend and transitives are version/hash locked; project editable install uses the already installed backend without isolation | Constraint build and installed-artifact smoke |
| Rebuild after identity elevation | Package builds occur only in `preflight`; registry jobs download, checksum, select manifest subjects, and publish exact files | Static permission/script test |
| Package/metadata/version divergence | Logical coordinates map separately to PEP 440 and SemVer; candidate expected filenames and subject kinds are exact; package-internal versions and metadata bytes are inspected | Unit tests and artifact smoke |
| Source-checkout or consumer-resource shadowing | Wheel/npm resources are package-rooted; installed smoke uses a nested unrelated directory containing malicious colliding docs/skill paths | Installed wheel/npm smoke under Python, Node, and Bun |
| Digest cycle | Build metadata hashes only source inputs; the external manifest hashes primary subjects but not itself; checksums are generated last | Determinism and manifest tests |
| Partial or hidden transfer | Python builds outside the transfer directory with no generated `.gitignore`; manifest rejects unexpected top-level subjects; recursive checksums cover nested smoke controls | Workflow regression tests |
| OIDC claim overreach | Workflow default is `{}`; only registry jobs receive `id-token: write`; both use tag-scoped GitHub environments with maintainer approval | GitHub API plus static workflow test |

## Live GitHub State

The review configured and then re-read these repository controls:

- ruleset `18755846`, **Protect main**, active with deletion/non-fast-forward
  protection, pull requests, stale-review dismissal, and conversation resolution;
- ruleset `18755847`, **Protect release tags**, active for `refs/tags/v*`, with
  creation, update, deletion, and non-fast-forward restricted to repository
  administrators;
- environments `pypi` and `npm`, each restricted to `v*` tags, requiring maintainer
  approval, and disallowing administrator bypass; and
- Actions enabled with `sha_pinning_required: true`, GitHub-owned actions plus explicit
  allowlist entries for setup-uv, setup-bun, the PyPI publisher, and SBOM action.

The main ruleset requires all Python, golden, TypeScript, cross-implementation, and six
cross-platform artifact-smoke contexts.
Confirm that the expanded names match the first pull-request run exactly; a missing
context blocks merge and must be corrected in the ruleset rather than bypassed.

## Residual Risks

1. **Registry identity not yet re-certified.** The workflow now carries environment
   claims. PyPI and npm must name the same environments in their trusted-publisher
   records; npm must allow only `npm publish`.
2. **Pinned PyPI action has a transitive floating base.** The reviewed
   `pypa/gh-action-pypi-publish` commit builds its action container from the official
   but floating `python:3.13-slim` image.
   PyPI recommends the action and its OIDC protocol is not reimplemented here.
   Re-review this residual whenever the action pin changes.
3. **Same-run artifact service is a platform trust root.** Full SHA checks protect
   action source, while GitHub still owns the artifact service, runner images, runtime
   token, and OIDC issuer.
   Checksums and manifest validation detect transfer corruption inside the modeled
   boundary, not a total GitHub compromise.
4. **Single-maintainer approval is not two-person control.** Environment approval is a
   deliberate pause and audit record, but the current maintainer can approve a release
   they initiated. Add a second reviewer when the project has another trusted releaser.
5. **The conformance kit remains draft.** It participates in internal candidate identity
   but is excluded from the public 0.2.x sdist and is not attached to a public GitHub
   release until `ss-6i6d` and `ss-trn7` complete.

## Release Gates

- [ ] Observe the new CI matrix on this pull request and confirm every configured
  required context matches exactly.
- [ ] Sign in to PyPI and set workflow `publish.yml`, environment `pypi`.
- [ ] Sign in to npm and set workflow `publish.yml`, environment `npm`, allowed action
  `npm publish`.
- [ ] Run `workflow_dispatch`; confirm build, manifest, SBOM, transfer, and installed
  smoke jobs pass while both publisher jobs are skipped.
- [ ] Prepare candidate release metadata and run the protected-tag path only after all
  gates above are checked.

## Primary Sources

- [GitHub secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub rulesets](https://docs.github.com/en/rest/repos/rules)
- [GitHub deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/)
- [PyPI trusted-publisher security model](https://docs.pypi.org/trusted-publishers/security-model/)
- [uv build constraints](https://docs.astral.sh/uv/concepts/projects/build/)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
