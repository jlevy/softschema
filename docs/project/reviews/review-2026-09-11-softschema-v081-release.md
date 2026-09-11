---
title: softschema v0.8.1 Release Review
description: Validation record and evidence for the semantic-serialization patch release
author: Claude, with maintainer direction from Joshua Levy
---
# Review: softschema v0.8.1 Release

**Date:** 2026-09-11

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** Released and externally verified on both registries.

## Decision

Ship v0.8.1 as a **patch**. Nothing is added to or removed from the library API, and
every subcommand’s flag set is byte-identical to v0.8.0, so `publishing.md`’s
reservation of a minor bump for changes that meaningfully shift the API or spec does not
apply. The release carries one correctness fix, one output-text change, and one
dependency bump.

The fix is worth a release on its own because of *where* it landed.
A missing property or a wrong type produces a pydantic error that serializes fine; only
a `model_validator` failure puts a live exception object in `ctx["error"]`. So
`validate --model` and `repair --model` reported ordinary structural problems correctly
and then crashed on the cross-field invariants a semantic model exists to express — the
failure mode was confined to the checks worth running.

## Scope Reviewed

Three changes, all merged to `main` between v0.8.0 and the v0.8.1 tag:

- **[#55](https://github.com/jlevy/softschema/pull/55) — `model_validator` failures are
  reported as plain data.** `validate_semantic` returned `dict(error)` verbatim for each
  pydantic error. The result therefore carried a live `ValueError`, and any caller that
  serialized it died with
  `TypeError: Object of type ValueError is not JSON serializable`. Exceptions in `ctx`
  now render as their message, which is what a reader needs and what the CLI was already
  trying to print. Python only; the TypeScript path was never affected.
- **[#54](https://github.com/jlevy/softschema/pull/54) — `--version` names the
  implementation.** `softschema 0.8.1 (Python)` and `softschema 0.8.1 (TypeScript)`. The
  two packages share a name, a version, and a CLI, so the version line alone could not
  say which runtime answered — the first thing worth knowing when the runtimes are
  suspected of disagreeing.
- **The `fast-uri` override moves to 3.1.6**, closing four high-severity advisories
  against `>=3.1.3 <3.1.6`: host confusion through skipped IDN canonicalization, SSRF
  through malformed IPv6 normalization, SSRF through repeated hostname percent-decoding,
  and host confusion through percent-encoded scheme normalization.
  It is a transitive dependency of ajv, the TypeScript implementation’s schema
  validator, and the advisories fail `npm audit` in the TypeScript job.

The one compatibility question in the set is the `--version` suffix.
The name and version still lead the line, so a pattern anchored to the *end* of the old
output is the only thing that breaks; both packages’ own tests were updated to match,
and no other surface reads that string.

## Validation Record

Runbook Phases 1–4 were run locally against the exact tree that was tagged, before the
release PR was opened.
Every command exited 0.

**Phase 1 — automated sweep (mirrors CI):**

- `make lint-check`: codespell, ruff, `ruff format --check` (39 files), basedpyright 0
  errors / 0 warnings, doc footers, retired CLI surface.
- `uv run pytest`: **247 passed**.
- `uv build`: wheel and sdist.
- `bun run check`: biome, tsc, **243 bun tests**, 820 expect() calls, coverage gate met.
- `bun run build` and `bun run publint`: “All good!”.
- Golden corpus: **80 py / 78 node / 80 bun**.
- `cross-impl parity OK (Python vs TypeScript/Node semantically equal)`.
- `make format-check`: clean on a committed tree.

**Phase 2 — clean-environment installs.** The wheel was installed into a fresh venv and
exercised on both artifact profiles (`frontmatter-md` and `pure-yaml`, exit 0 each),
with `docs --list` and `skill --brief` reading their bundled resources.
`softschema-0.8.1.tgz` was packed through `prepublishOnly` and run under plain Node the
same way. Both print the new `--version` line.

**Phase 3 — quickstart as written.** Python and TypeScript produced byte-identical
output for `docs example-artifact` and `docs example-schema`, and `validate` exited 0 on
each.

**Phase 4 — skill bootstrap.**
`skill --install --scope project --agent portable --agent claude` reported both
`SKILL.md` mirrors as `created` in a scratch repo, and both files were present.

**CI on the release PR ([#56](https://github.com/jlevy/softschema/pull/56)):** all 20
checks green, including the six-way `Artifact smoke` matrix across Linux, macOS, and
Windows on Python 3.11/3.14 and Node 22/24.

**Phase 5 — post-publish verification.** Both registry jobs succeeded in one run.
`uvx softschema@0.8.1 --version` printed `softschema 0.8.1 (Python)` and
`npx -y softschema@0.8.1 --version` printed `softschema 0.8.1 (TypeScript)`; the
quickstart run against the published artifacts produced byte-identical output across the
two.

The fix itself was then confirmed against the *published* packages rather than the
source tree, by running the same cross-field violation through both versions:

- `softschema@0.8.0` — `TypeError: Object of type ValueError is not JSON serializable`,
  traceback, no result.
- `softschema@0.8.1` — `"outcome": "invalid"` with `ctx.error` rendered as the string
  `direction=up but delta=-1.0`.

That comparison is the evidence that the released bytes carry the fix, not just the tree
that produced them.

## Process Notes

- **The tag could not be pushed over git.** `git push origin v0.8.1` failed with
  `RPC failed; HTTP 403` from a proxied session that accepts branch pushes.
  This is the case `publishing.md` step 5 documents: the tag was created instead by
  `gh release create v0.8.1 --target <merge-sha>`, and the resulting ref was verified to
  point at the merge commit `ff0f919` before the publish workflow was watched.
  The workflow’s own tag-vs-candidate version guard passed, which is the independent
  check that the tag sat where it had to.
- **Registry propagation lagged the workflow, as documented.** Immediately after both
  publish jobs reported success, the PyPI simple index did not yet list the 0.8.1 files
  and npm still reported 0.8.0 as `latest`. PyPI caught up within about 20 seconds and
  npm within about 40. Neither is a failure; querying the simple index directly is what
  distinguishes propagation from a real problem.
- **The pre-commit hook’s `generate` step reports drift by design.** flowmark adds blank
  lines inside the `softschema:generated` markers that the generator does not emit, so
  the hook’s `generate` pass reports `drift: true` and rewrites the section back to
  canonical form in the same run.
  The committed tree is clean afterward; `make format-check` on the committed tree is
  the check that matters.
- **The editable dev install reports a stale version.**
  `.venv/bin/softschema-py --version` prints `0.0.1.dev239+01b19ba` rather than the
  derived release version, because the editable install’s metadata predates the commits.
  It affects the development checkout only — the built wheel reported
  `0.8.1.dev7+1dc1f78` pre-tag and the published wheel reports `0.8.1` — but it is worth
  knowing before reading a version off the dev venv.

## Baseline for the Next Release

Counts to compare against, and to investigate on any **drop**:

- Python tests 247; TypeScript tests 243
- Golden corpus: Python 80, Node 78, Bun 80
- basedpyright 0 errors; publint clean; cross-impl parity OK
- CI: 20 checks on the release PR

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
