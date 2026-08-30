---
title: softschema v0.8.0 Release Readiness Review
description: Pre-release evidence for the validate --repair minor, and the steps still open before tagging
author: Claude, with maintainer direction from Joshua Levy
---
# Review: softschema v0.8.0 Release Readiness

**Date:** 2026-08-29

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** The blocker found by the
[`--repair` end-to-end review](review-2026-08-30-validate-repair-e2e.md) is fixed and
covered. Not yet released — the version bump, the changelog cut, and the manual e2e
phases are still open.

## Decision

Ship the unreleased work as **v0.8.0, a minor**, not a patch.

> **Update, 2026-08-30.** The version call stands, but the release does not.
> End-to-end testing of `--repair` against real agent output found that `validate` and
> `--repair` disagree about whether an unterminated-frontmatter document is readable:
> the producer is told `valid` where the consumer cannot read the file at all.
> That inverts the feature’s premise and is present in both implementations.
> See [the end-to-end review](review-2026-08-30-validate-repair-e2e.md), Finding 1. Fix
> **Fixed** on this branch, with unit and golden coverage in both implementations and
> the runbook re-run green against the fixed build.

`publishing.md` draws the line at “patch bumps cover docs-only changes and small
additive features; reserve minor bumps for changes that meaningfully shift the API or
spec.” The unreleased work crosses it on three counts: `validate` gains `--repair` and
`--check-repair`, a mode that *writes the user’s file*; eight new symbols land on the
public API of each package; and every `ArtifactValidationResult` grows a `repairs`
field. The spec gained 37 lines describing it.
That is an API and spec shift, not a small additive feature.

The change is nonetheless **backward-compatible in behavior**, which is why it is a
minor and not a breaking release.
Evidence below.

## What Changed Since v0.7.0

19 commits, 65 files, +5915 / −588, in three threads.

| Thread | PRs | Substance |
| --- | --- | --- |
| `validate --repair` | #50 → #51 | The headline feature: new `repair`, `conform`, `pipeline`/`repairValidate`, and `portable` modules in both languages, wired through the CLI |
| Docs value proposition | #37 | README rewrite (+253), guide expansion (+442), agent-workflow and schema-maturity framing |
| v0.7.0 release record | #49 | The prior release review, plus the docs-value-prop research brief |

Test infrastructure moved with it: `tests/golden/run.sh` was replaced by
`run_golden_tests.py`, the golden scenarios became `*.tryscript.md` transparent-box
transcripts, and `validate-repair.tryscript.md` (637 lines) runs the new journey against
Python, Node, and Bun.

### What `--repair` does

One escalating pass, writing the file once: parse, quote a scalar whose text YAML reads
as structure, retype a scalar the contract declares `type: string`, then validate.
Verified by hand on `repair-unquoted-colon.md`: `--check-repair` reported the
`yaml_quoted_scalar` repair and exited 1 **without touching the file**; `--repair` wrote
`summary: "Note: actually Q1"`, exited 0, and left the body prose untouched.

## Compatibility Evidence

Rather than trust the changelog, v0.7.0 and `main` were run side by side from a worktree
at the v0.7.0 tree, on the same interpreter, against the same inputs:

| Case | v0.7.0 | main | Reading |
| --- | --- | --- | --- |
| Valid document (`spirited-away.md`) | exit 0, `outcome: valid` | identical but for one added line | compatible |
| Invalid document (`repair-missing-required.md`) | exit 1, structural errors | identical but for one added line | error records unchanged |

The sole difference in both cases is the additive `"repairs": []` key.
Verdicts, exit codes, and error records are byte-identical otherwise.

Both public export surfaces were diffed directly:
`packages/python/src/softschema/__init__.py` and `packages/typescript/src/index.ts` gain
symbols and remove none.

## Validation Record

### CI on `main`

Run [`33279630914`](https://github.com/jlevy/softschema/actions/runs/33279630914) at
`737f28d`: **18 jobs, all success**, including artifact smoke across
ubuntu/macOS/Windows at py3.11/3.14 and node22/24, and the release-candidate build and
smoke jobs that the publish workflow reuses.

### Phase 1 — Local automated sweep

Run against the exact tree that would be tagged.
Everything exits 0.

| Check | Result | v0.7.0 baseline |
| --- | --- | --- |
| `pytest` | 225 passed | 194 |
| `bun test --coverage` | 223 passed, 731 expects, 0 fail | 192 |
| TypeScript line coverage | 97.13% (funcs 96.79%) | 98.02% |
| `lint.py --check` | exit 0 | 0 errors |
| `make format-check` | exit 0 | exit 0 |
| Golden corpus | Python 68, Node 66, Bun 68 | 49 / 47 / 49 |
| `cross-impl-diff.sh` | parity OK | parity OK |
| Working tree | clean | — |

The Node-versus-Python golden gap of 2 is unchanged from v0.7.0 and is expected.

### Repository hygiene

No open pull requests and no open issues.
`main` and the review branch are level.

## Open Before Tagging

None of these is a defect in the code; they are the release steps and two small loose
ends.

0. ~~**Fix the `validate` / `--repair` profile-inference divergence**~~ — done, with a
   second related defect (the misleading missing-contract reason) fixed alongside it.
1. **Bump `packages/typescript/package.json` to `0.8.0`.** It still reads `0.7.0`. The
   Python version derives from the tag, but the npm publish job aborts on a mismatch.
2. **Cut the changelog.** `## Unreleased` becomes `## v0.8.0—<date>`.
3. ~~**Record the package description change.**~~ Done — the changelog now lists it.
   Both `pyproject.toml` and `package.json` read “Gradual contracts for YAML data, with
   optional Markdown context”, the text on the PyPI and npm listing pages.
4. **Run e2e phases 2–4.** The checklist requires clean-environment installs of the
   wheel and npm tarball, the quickstart as written, and the skill bootstrap before
   tagging. CI covers Phase 1 and artifact smoke; it does not cover these.

### Worth a look, not a blocker

**TypeScript line coverage fell 98.02% → 97.13%.** The v0.7.0 review asked that any drop
be investigated. The cause is `conform.ts` at 87.16% lines; `repair.ts` is at 95.00% and
`repairValidate.ts` at 94.12%. All new modules are at 100% *function* coverage, the
floor is 70%, and the CLI flows these modules serve are covered by the golden journey
that line coverage does not see.
The drop is explained, not alarming.

**The repair plan sits in `specs/active/`.** `plan-2026-08-29-validate-repair.md` is
marked “Implemented (phases 1-3); phase 4 and the metaproc coordination deferred”.
The deferred phase justifies keeping it out of `done/`, but every other implemented plan
has moved, so the placement is worth a deliberate call rather than a default.

## Status Addendum — 2026-08-30

The review of PR #52 and a full end-to-end runbook run against the fixed build.
Both are recorded here rather than in the findings above, which stand as written.

### Review of PR #52

Eight findings
([comment](https://github.com/jlevy/softschema/pull/52#issuecomment-5467427098)). The
`--repair` fix itself was confirmed correct: the pre-fix defect reproduces on a worktree
at `origin/main` (`outcome: valid`, `profile: pure-yaml`, exit 0) for a file plain
`validate` refuses.

Chasing one finding — whether `opens_frontmatter_fence` really matches the reader
“exactly”, as its docstring claimed — found a **live second defect** in the sibling
function. `_line_end` / `lineEnd` returned nothing at EOF, so a final line with no
trailing newline was not a line to the offset scan, though it is one to both readers.
`split_frontmatter` therefore reported “no region to rewrite” for a document ending at
its closing fence, and `--repair` silently skipped an artifact it could fix.
Two documents differing by one trailing byte got opposite verdicts.
Fixed, with 3 Python and 3 TypeScript cases each verified to fail against the pre-fix
code, and a golden journey on all three runtimes.

Also fixed: the Node CLI prefixed a frontmatter read failure with
`Error parsing YAML metadata:` where Python did not, so the two CLIs worded the same
failure for the same file differently; and `parseAfterRepair` swallowed every throw,
reporting an internal fault as “the document could not be read”.
Deferred, not blocking: the exit-class difference when `--contract` is supplied
(`ss-qto7`), the missing filename in pure-yaml read errors (`ss-fjow`, pre-existing and
symmetric across both paths), and a harness classification gap (`ss-p5sh`).

### End-to-end runbook run

`docs/agent-repair.runbook.md` against the fixed build, `gemini-2.5-flash` at
`thinkingBudget: 0`.

| Phase | Result |
| --- | --- |
| 1 — templated | 8/12 invalid on arrival, **8/8 repaired unaided**; every repair a single `scalar_conformed` at `['rubric_version']`; `1.10` preserved as `'1.10'` |
| 2 — prose | 11/12 invalid with **408 `undeclared_property` / 408 `missing_property`, exactly paired, 0 renames**; the 12th was a truncated write, correctly refused |
| 3 — feedback | **11/11 to valid in one round**, 816 errors to 0 |
| 4 — regression | both cases exit as specified on Python, Node, and Bun |

Phases 1 and 2 assert the three conformance guarantees on every artifact:
`--check-repair` never wrote, repair is idempotent, and a no-op comes back
byte-identical. All held.

The prose phase produced a truncated agent write on its own — `CROX.md` opened a
frontmatter fence and never closed it — which is the defect PR #52 exists to fix,
occurring naturally a second time.
Against `origin/main` that artifact reports
`missing --contract because the document has no YAML frontmatter`, sending an agent
after a block that is plainly there; against this build it names the delimiter.
Both of that PR’s fixes are confirmed on live model output, not only on fixtures.

### Automated sweep, re-run

| Check | Result | Previous |
| --- | --- | --- |
| `pytest` | 234 passed | 231 |
| `bun test` | 231 pass, 0 fail | 228 |
| `tsc --noEmit` · `biome ci` · `publint` | clean | clean |
| Golden corpus | Python 73, Node 71, Bun 73 | 71 / 69 / 71 |
| `cross-impl-diff.sh` | parity OK | parity OK |
| `lint.py --check` · `make format-check` | exit 0 | exit 0 |

One ordering note for whoever cuts the release: `make format` reflows the Markdown that
the TypeScript package bundles as resources, and does **not** refresh those copies.
`cross-impl-diff.sh` compares `docs spec` output between the two CLIs and fails on the
stale copy until `bun run --cwd packages/typescript build` runs again.
Build after formatting, not before.

### Still open before tagging

Unchanged from the list above: bump `packages/typescript/package.json` to `0.8.0`, cut
the changelog, and run e2e phases 2–4 (clean-environment installs of the wheel and npm
tarball, the quickstart as written, and the skill bootstrap).
Tracked as `ss-txij`.

## Baseline for the Next Release

Counts to compare against, and to investigate on any **drop**:

- Python tests 225; TypeScript tests 223 at 97.13% line coverage
- Golden corpus: Python 68, Node 66, Bun 68
- basedpyright 0 errors; cross-impl parity OK
- CI: 18 jobs on `main`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
