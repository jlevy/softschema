---
title: softschema v0.6.1 Release Review
description: Validation record and evidence for the paired docs-only patch release
author: Claude, with maintainer direction from Joshua Levy
---
# Review: softschema v0.6.1 Release

**Date:** 2026-08-14

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** Released and externally verified on both registries.

## Decision

Ship v0.6.1 as a **patch**, per the `publishing.md` rule that patch bumps cover
docs-only changes. The diff since v0.6.0 is 113 added lines across `README.md` and
`docs/softschema-guide.md` and nothing else: no code, CLI surface, exit class, or
compiled schema output changed.

A docs-only change still warrants a release because both packages bundle the guide and
README as package resources.
`pyproject.toml` force-includes them into the wheel, and the npm package ships
`resources/`. Until a release goes out, `softschema docs guide` from an installed
package does not serve the new content — which is the specific thing verified in Phase 5
below.

## Scope Reviewed

Merged since v0.6.0:

- **#33** — research-loop documentation: a new guide playbook, “Record a Research Loop,”
  and a shorter README section that links to it.
- **#34** — release preparation: `packages/typescript/package.json` to `0.6.1` and the
  CHANGELOG v0.6.1 entry cut from `Unreleased`.

The tag `v0.6.1` sits on `85d09d2`, the #34 merge commit.
Later merges to `main` (#35: tbd tooling upgrade and `publishing.md` notes) landed
**after** the tag and are deliberately not in this release; neither is bundled into
either package, so no re-release is required.

## Validation Record

### Phase 1 — Automated sweep (mirrors CI)

| Check | Result |
| --- | --- |
| `make lint-check` (codespell, ruff, basedpyright, doc footers) | Pass; basedpyright 0 errors |
| `uv run pytest` | 176 passed |
| `uv build` | wheel + sdist |
| `bun run check` (biome, tsc, tests + coverage gate) | 172 passed |
| `bun run build`, `bun run publint` | Pass; publint “All good!” |
| Golden corpus — Python / Node / Bun | 38 / 36 / 38 |
| `cross-impl-diff.sh` | “cross-impl parity OK” |
| `make format-check` | Clean on a clean tree; no generated-section or skill-mirror drift |

All counts match the v0.6.0 floors, as expected for a docs-only change.

### Phase 2 — Clean-environment installs

| Check | Result |
| --- | --- |
| Wheel in a fresh venv: `--version`, `docs --list`, `skill --brief`, full `validate` | All exit 0 |
| `npm pack` tarball under plain Node (runs `prepublishOnly`) | `softschema 0.6.1` from both `dist/cli.js` and the `.bin` shebang; `validate` exit 0 |

### Phases 3–4

| Check | Result |
| --- | --- |
| README quickstart verbatim from an empty directory, both implementations | Artifact and schema output byte-identical across implementations |
| Agent skill bootstrap into a scratch git repo | Both `SKILL.md` mirrors reported `created` and present on disk |

### CI on the release PR

Run 178 on #34: **18/18 jobs green**, including the cross-platform artifact-smoke matrix
(Linux, macOS, Windows × Python 3.11 and 3.14).

### Publish

Workflow run `31820423030`, triggered by publishing the GitHub release, completed in
1m0s with all four jobs green: `build-candidates`, `smoke-candidates`,
`Publish to PyPI`, `Publish to npm`. Both registries published from one tag and one
build over OIDC trusted publishing, with no stored tokens.

### Phase 5 — Post-publish registry verification

| Check | Result |
| --- | --- |
| PyPI latest | `0.6.1` |
| npm latest | `0.6.1` |
| `uvx --refresh --exclude-newer-package "softschema=<now>" softschema@0.6.1 --version` | `softschema 0.6.1` |
| `npx -y softschema@0.6.1 --version` | `softschema 0.6.1` |
| `docs guide` from the published PyPI artifact contains the research-loop playbook | Present |
| `docs guide` from the published npm artifact contains the research-loop playbook | Present |
| `docs readme` from the published PyPI artifact contains the README section | Present |

The last three are the ones that matter for this release: they confirm the new content
reaches an installed package from the real registries, not merely a local build.

## Risk Review

| Risk | Control | Residual risk |
| --- | --- | --- |
| Patch bump hides a behavior change | Diff since tag confined to two Markdown files; full parity and golden suites re-run | None |
| Package versions diverge | `packages/typescript/package.json` set to `0.6.1`; publish guard compares tag against both built artifacts | None after guard passes |
| Only one registry publishes | Rerun failed jobs against the retained checksummed candidate | Not exercised; both succeeded |
| Registry index propagation lags | `--refresh` plus a now-timestamped cool-off override | None; both resolved first try |
| Docs ship stale in the package | Phase 5 greps the published artifacts for the new sections | None |

## Process Notes

Two issues cost significant time and are worth recording so the next release avoids
them.

**A stale `ensure-gh-cli.sh` produced a false credential verdict.** The repo was pinned
to tbd 0.3.0, whose gh setup script reported `Token may be invalid or expired` for a
valid token. `gh auth status` resolves identity over GraphQL, so where a session proxy
intercepts GitHub and restricts GraphQL, gh misreports the token.
This sent the release down a multi-hour path of reinstalling gh and inspecting token
scopes before the direct channel turned out to be open.
Fixed in #35 by upgrading to tbd 0.6.1, whose script reports
`GH_TOKEN is VALID, but this session's proxy intercepts GitHub API calls` and prints the
scoped `NO_PROXY` recipe.

**`git push --dry-run` gave a false pass on the tag push.** It reported `[new tag]` for
a ref the server then refused with 403, because the dry run stops at ref advertisement
before receive-pack.
The tag was ultimately created by `gh release create --target <merge-sha>`, which
`publishing.md` step 5 already prescribes for this case.
Both traps are now documented in the release checklist (#35).

## Baseline for the Next Release

Counts to compare against, and to investigate on any **drop**:

- Python tests 176; TypeScript tests 172
- Golden corpus: Python 38, Node 36, Bun 38
- basedpyright 0 errors; publint clean; cross-impl parity OK
- CI: 18 jobs on the release PR

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
