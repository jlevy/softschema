---
title: softschema v0.7.0 Release Review
description: Validation record and evidence for the enforced-composition minor release
author: Claude, with maintainer direction from Joshua Levy
---
# Review: softschema v0.7.0 Release

**Date:** 2026-08-25

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** Released and externally verified on both registries.

## Decision

Ship v0.7.0 as a **minor**. Ordinary schema verdicts are unchanged, but two surfaces
break in ways `publishing.md` reserves a minor bump for: structural diagnostic records
gain stable `code` and `property` fields and emit one record per affected field, and
callers supplying external `resources` must key them by absolute URI without a fragment.

The release exists because `status: enforced` was unusable on composed schemas.
Issue #41 records the symptom exactly: `allOf` object composition made every artifact
invalid under `enforced`. That is worth a release on its own, and it also settles the
compatibility question — 0.6.2 returned `ok=false` for those schemas *before examining
the document*, so the change moves results from red to green rather than the reverse.

## Scope Reviewed

Merged in #48, tagged at `e014e5b`:

- **#44** — the enforcement work: `enforcement.py` and `enforcement.ts` as new modules,
  annotation-aware closure at supported sites, the support matrix, and the stable
  `code`/`property` error fields.
- **#47** — documentation levelling: the composition material marked as advanced, and
  the research brief linked for depth.
- **`6ccd551`** — release preparation: `packages/typescript/package.json` to `0.7.0` and
  the CHANGELOG v0.7.0 entry cut from `Unreleased`.

### Compatibility evidence gathered for this release

A direct 0.6.2-versus-0.7.0 comparison was run from a worktree at the 0.6.2 tree, using
the same interpreter and the same inputs, rather than relying on the changelog:

| Case | 0.6.2 | 0.7.0 | Reading |
| --- | --- | --- | --- |
| Flat schema, valid / missing / extra | valid / invalid / invalid | identical | the compatibility floor holds |
| Extra key inside a `$ref` target | `invalid`, `validator: additionalProperties`, generic message | `invalid`, `validator: unevaluatedProperties`, `code: undeclared_property`, `property: surprise` | same verdict, different record — this is the break |
| Valid document, `allOf` + `if`/`then` schema | `invalid` (`enforcement_unsupported`) | `valid` | the headline fix; red to green |

The public export surfaces were diffed directly:
`packages/python/src/softschema/__init__.py` and `packages/typescript/src/index.ts` are
byte-identical to 0.6.2.

All nine user-facing `enforcement_unsupported` reasons were cross-checked against both
implementations and the spec, and all nine agree and are documented.
`same_instance` and `nested_instance` appear in both sources but are internal
`_FragmentContext` literals, not user-facing reasons.

## Validation Record

### Phase 1 — Automated sweep (mirrors CI)

Run against the exact release tree: `make lint-check` (codespell, ruff, basedpyright,
doc footers) passed; `uv run pytest` 194 passed; `uv build` produced wheel and sdist;
`bun run check` 192 passed at 98.02% line coverage; `bun run build` and
`bun run publint` clean; golden corpus 49 Python, 47 Node, 49 Bun; `cross-impl-diff.sh`
reported parity OK; `make format-check` exit 0 on the committed tree.

### Phase 2 — Clean-environment installs

Wheel in a fresh venv: `--help`, `docs --list`, `skill --brief`, and both profiles
validate (exit 0, `pure-yaml` resolved).
npm tarball under plain Node v22.22.2: packs as `softschema-0.7.0.tgz`, reports
`softschema 0.7.0`, both profiles validate, bin shebang runs.

### Phases 3–4

Quickstart as written from an empty directory: both implementations exit 0 with zero
flags, and the emitted artifact and schema are byte-identical across them.
Skill bootstrap in a scratch git repo: both `SKILL.md` mirrors reported `created` and
present on disk.

### CI on the release PR

18 jobs, all success, on `6ccd551` — including artifact smoke across
ubuntu/macOS/Windows at py3.11/3.14 and node22/24.

### Publish

Run `32821919899`: `build-candidates`, `smoke-candidates`, `Publish to PyPI`, and
`Publish to npm` all success, over OIDC with no stored tokens.

### Phase 5 — Post-publish registry verification

Both registries carried 0.7.0 with no propagation lag this time; the PyPI simple index
listed both files and npm `dist-tags.latest` was already `0.7.0`. `uvx` and `npx` both
reported `softschema 0.7.0`, the published quickstart ran clean on both implementations
with byte-identical output, and the composed-schema fix was confirmed against the
*published* package: a valid document under an `allOf` + `if`/`then` schema returns
`valid`.

## Process Notes

**`git` and `gh` need opposite proxy settings in this environment.** `gh` works only
with the scoped `NO_PROXY` the session hook prints; `git push` *fails* under it with
`could not read Username for 'https://github.com'`, because the credential-providing
proxy is bypassed. Use `NO_PROXY` for `gh` and leave it unset for git.
Previous release reviews recorded only the `gh` half of this.

**`gh pr create` uses GraphQL, and that quota can be exhausted while REST is
untouched.** The release PR could not be created with `gh pr create`
(`API rate limit already exceeded`) while `gh api rate_limit` showed graphql 0/5000 and
core 5000/5000. Creating the PR with
`gh api repos/OWNER/REPO/pulls --method POST --input payload.json` worked immediately.
Prefer REST for release-critical steps.

**The tag push was blocked again, and the documented fallback worked again.**
`git push origin v0.7.0` was refused with `HTTP 403`.
`gh release create v0.7.0 --target e014e5b` created the tag at the merge commit,
verified against the GitHub ref API before watching the publish run.
Note the exit-code trap: piping that push through `tail` made the shell report
`PUSH_EXIT=0` despite the 403, so verify the remote ref rather than trusting the status.

**Delete the local annotated tag afterward.** As the v0.6.2 review predicted,
`git tag -a v0.7.0` created locally in anticipation left a `tag` object (`38f1445`)
diverging from the lightweight commit ref `gh` created.
Deleting it and refetching reconciled local and remote to the same lightweight ref at
`e014e5b`.

**`uv pip install dist/softschema-*.whl` assumes a clean `dist/`.** A second `uv build`
leaves the previous version’s wheel in place, the glob expands to both, and uv aborts
with `Requirements contain conflicting URLs`. Runbook Phase 2 should `rm -rf dist/`
first.

## Baseline for the Next Release

Counts to compare against, and to investigate on any **drop**:

- Python tests 194; TypeScript tests 192 at 98.02% line coverage
- Golden corpus: Python 49, Node 47, Bun 49
- basedpyright 0 errors; publint clean; cross-impl parity OK
- CI: 18 jobs on the release PR

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
