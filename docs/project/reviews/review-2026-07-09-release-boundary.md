# Release-Boundary Risk Review

**Reviewed:** July 9, 2026\
**Scope:** `ss-o21w` and the final dual-registry recovery/publication closures\
**Status:** Code complete; immutable-release policy, the protected GitHub environment,
registry identity claims, and a final green CI rerun remain release gates

## Decision

The revised workflow has a defensible build-once boundary.
An unprivileged job tests source, creates deterministic metadata, builds each package
once, inventories and hashes the primary subjects, generates artifact-specific SPDX
SBOMs, and transfers the result to an unprivileged installed-artifact smoke job.
PyPI and npm jobs receive the tested transfer, registry OIDC permission, and an exact
preflight-commit checkout used only for the trusted verifier.
They do not resolve project dependencies, rebuild, or execute candidate package
lifecycle scripts. The final boundary pass also binds every recovery bootstrap to the
exact workflow commit before parsing or execution, authenticates the checksum inventory
itself, preflights extraction depth and implied-directory budgets before writes, and
rechecks immutable-release policy immediately before final publication.

Do not use this path for a release until the two registry trusted-publisher records have
been re-certified with the `pypi` and `npm` environment claims and the final
pull-request revision passes every required check.
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
| Declared subject-size amplification | The release-manifest schema caps each subject at 512 MiB; the runtime caps the aggregate at 1 GiB before reading subject files | Schema/runtime boundary agreement tests |
| Source-checkout or consumer-resource shadowing | Wheel/npm resources are package-rooted; installed smoke uses a nested unrelated directory containing malicious colliding docs/skill paths | Installed wheel/npm smoke under Python, Node, and Bun |
| Digest cycle | Build metadata hashes only source inputs; the external manifest hashes primary subjects but not itself; checksums are generated last | Determinism and manifest tests |
| Partial, hidden, redirected, oversized, or verifier-mutated transfer | Python builds outside the transfer directory with no generated `.gitignore`; recursive inventory has a hard node budget and rejects hidden or undeclared files, unexplained directories, POSIX links, Windows reparse redirects, non-regular nodes, missing stable identities, subjects over 512 MiB, and aggregates over 1 GiB; the checksum writer and reader share a 4 MiB ceiling; bounded subject reads use regular-file descriptors, device/inode/size/mtime/ctime snapshots, and component-wise no-follow traversal where available; unprivileged smoke jobs run the exact-commit checkout verifier before the transferred driver or helpers | Workflow regressions, exact-checkout assertions, inventory/output/byte-budget tests, file/parent/checksum swap probes, reparse/special-node tests, and a default-interpreter subprocess that leaves no bytecode nodes |
| Recovery bootstrap or checksum substitution | The checksum, archive, and frozen driver each require exact workflow/ref/commit attestations before parsing or execution; checksum names and bytes are bounded and closed | Recovery-order and hostile-checksum workflow tests |
| Archive path amplification | Recovery preflights depth, file count, conflicting file/directory paths, and every unique implied directory before any archive-driven write | Deep and sparse-parent archive tests |
| OIDC claim overreach | Workflow default is `{}`; only registry jobs receive `id-token: write`; both use tag-scoped GitHub environments with maintainer approval | GitHub API plus static workflow test |

The exact-checkout verifier proves a static transfer: every declared regular file
matched the closed checksum inventory when the trusted verifier read it, and observed
replacement or mutation fails closed.
It does not freeze the directory after returning.
The workflow’s security argument therefore assumes a fresh isolated GitHub-hosted
runner, sequential steps, no candidate code before trusted verification, and no
concurrent same-UID writer.
That is the deliberately narrow Actions threat model; an active local writer that can
mutate verified files after the verifier returns is out of scope.

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
The expanded names match the contexts observed on this pull request exactly.
A failed initial run exposed the verifier-mutation defect now covered by `ss-lp5a`; the
final revision still requires a completely green rerun.
A future missing context must be corrected in the ruleset rather than bypassed.
The same environment inventory did not contain `github-release`; the workflow names it,
but its required reviewer, `v*` restriction, and administrator-bypass policy remain an
explicit live gate rather than a verified control.
The immutable-releases API returned `false`, so both workflow mutation checks currently
fail closed. The Pages API returned 404; neither result is evidence of a configured
publication surface.

## Residual Risks

1. **Registry identity not yet re-certified.** The workflow now carries environment
   claims. PyPI and npm must name the same environments in their trusted-publisher
   records; npm must allow only `npm publish`.
2. **Pinned PyPI action has a transitive floating base.** The reviewed
   `pypa/gh-action-pypi-publish` commit builds its action container from the official
   but floating `python:3.13-slim` image.
   PyPI recommends the action and its OIDC protocol is not reimplemented here.
   Re-review this residual whenever the action pin changes.
3. **The initial draft freeze still depends on Actions retention.** Full SHA checks
   protect action source, while GitHub still owns the artifact service, runner images,
   runtime token, and OIDC issuer.
   The protected draft job converts the 90-day transfer into attested release recovery
   assets; later jobs can restore the exact frozen bytes after the Actions copy expires.
   Provision and re-read the protected `github-release` environment before tagging; the
   first approval must then occur before that expiry because no release mutation is
   authorized before the environment gate.
4. **Single-maintainer approval is not two-person control.** Environment approval is a
   deliberate pause and audit record, but the current maintainer can approve a release
   they initiated. Add a second reviewer when the project has another trusted releaser.
5. **The conformance kit remains draft.** It participates in internal candidate identity
   but is excluded from the public 0.2.x sdist and is not attached to a public GitHub
   release until `ss-6i6d` and `ss-trn7` complete.

## Release Gates

- [x] Observe the new CI matrix on this pull request and confirm every configured
  required context matches exactly.
- [ ] Rerun the final pull-request revision and require every configured context to
  pass.
- [ ] Sign in to PyPI and set workflow `publish.yml`, environment `pypi`.
- [ ] Sign in to npm and set workflow `publish.yml`, environment `npm`, allowed action
  `npm publish`.
- [ ] Create and re-read environment `github-release`; require a reviewer, restrict it
  to `v*` tags, and disallow administrator bypass.
- [ ] Enable repository immutable releases and re-read the API until it returns `true`.
- [ ] Run `workflow_dispatch`; confirm build, manifest, SBOM, transfer, and installed
  smoke jobs pass while both publisher jobs are skipped.
- [ ] In a non-publishing fixture run, remove the Actions candidate after the draft
  freezes and confirm a failed-job rerun restores the attested recovery bundle.
- [ ] Prepare candidate release metadata and run the protected-tag path only after all
  gates above are checked.

## Primary Sources

- [GitHub secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub rulesets](https://docs.github.com/en/rest/repos/rules)
- [GitHub deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Node.js filesystem flags and platform support](https://nodejs.org/api/fs.html#fsconstants)
- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/)
- [PyPI trusted-publisher security model](https://docs.pypi.org/trusted-publishers/security-model/)
- [uv build constraints](https://docs.astral.sh/uv/concepts/projects/build/)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
