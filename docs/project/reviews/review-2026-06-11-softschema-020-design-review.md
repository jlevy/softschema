# Review: softschema 0.2.0 Design and Polish (Pre-Release)

**Date:** 2026-06-11

**Author:** Claude Code (senior engineering review), decisions by Joshua Levy

**Scope:** Fresh, comprehensive review of the full 0.2.0 design before release: the
rewritten spec, the landed Phase 1/2 work on PR #13, the remaining beads, the CLI and
library surface in both implementations, and every user-facing doc.
Goal: a compelling, wart-free 0.2.0.

## Verdict

The 0.2.0 design is sound and close, but it was not releasable at review time: the
spec’s headline feature (`softschema.schema` binding) was documented but unimplemented,
the spec’s “normative” generated-section text did not match what the renderers actually
emit, a real TS/Python parity bug existed in `enum_table` rendering, and the flagship
“validate with no flags” story had an envelope-shaped hole.
All findings below were resolved in this review cycle (resolutions noted inline).

## Design Findings

**D1 (blocker). The self-describing story had an envelope hole.** With only
`softschema.schema`, “validate with no flags” was true only for single-key artifacts;
any artifact coexisting with host frontmatter (`title:`, `tags:`, …) — including the
flagship movie example — still required `--envelope`. **Decision (maintainer): add an
optional `softschema.envelope` metadata key.** The metadata block becomes the complete
self-description: `contract` (what), `schema` (where), `envelope` (which key), `status`
(how strictly). Precedence mirrors `schema` and keeps host-over-document: `--envelope`
flag > registry `envelope_key` > `softschema.envelope` > single-key inference.
A declared envelope absent from the document is `envelope_mismatch`, as today.

**D2 (confirmed). Schema-resolution precedence: host above document.** `--schema`
flag/argument > host registry binding (library only) > `softschema.schema` >
metadata-only. A document must not silently redirect a host’s validation; in the CLI (no
registry) the chain collapses so no-flag validation still works.
**Decision (maintainer): confirmed as spec’d.**

**D3 (blocker). Spec/code gap.** The spec documented `softschema.schema` while both
implementations still rejected it as an unknown metadata key (spec-first was
intentional, but release-blocking).
**Resolution: implement the binding (with D1’s `envelope`) in both implementations,
golden-first, before 0.2.0.**

**D4. Bounded resolution contradiction.** The plan said both “an absolute path is used
as given” and “a path escaping the doc-dir/cwd bound is rejected” — contradictory.
**Resolution: a metadata `schema` value must be a relative path in the reference CLIs;
absolute paths are rejected (use `--schema` for arbitrary paths).
A relative path resolves from the document’s directory; if the normalized result lies
outside both the document directory and the working directory it is rejected (reported
as `schema_missing` with a message naming the bound).** The spec still requires only
“non-empty string” at the conformance level.

## Correctness Findings

**C1 (parity bug). TS `enum_table` missing pipe escaping.** Python escapes `|` in enum
values (`\\|`); `generate.ts` did not — a value containing `|` would render differently
across implementations and break the GFM table.
**Resolution: port the escaping to TS with a unit test.**

**C2 (spec bug). The spec’s “normative” generated-section text did not match the
renderers.** `field_list` actual format is `- `name` (type, required): description` (not
the em-dash form the spec described); `vocab` renders one `` - `value` `` bullet per
line (not a comma-joined line); the “enum including `null` lists non-null members” claim
does not match `_extract_enum` (an all-string `enum` renders; nullability is the
`anyOf: [{enum}, {type: null}]` shape, whose string branch renders; any other mixed enum
is skipped); the empty-case rows (`_(no enum fields)_`, `_(no fields)_`) were
unspecified.
**Resolution: correct the spec to describe the implementations exactly (they
agree with each other and carry golden coverage).**

**C3. Stale `validate` help text.** Python’s `--model`/`--schema` help still said
“Required unless --x is provided”; metadata-only validation made both optional, and the
new binding makes them overrides.
TS subcommands and options had no descriptions at all.
**Resolution: rewrite Python help for 0.2.0 semantics; add matching Commander
descriptions in TS.**

**C4. Misleading TS test name.** `cli-inprocess.test.ts` “validate with no
implementation exits 2” actually exercises envelope ambiguity.
**Resolution: rename to describe the real behavior.**

## Polish Findings

**P1. Library export asymmetry.** TS `index.ts` lacked `SOFTSCHEMA_FORMAT_VERSION` and
`GeneratedSection` (Python exports both).
**Resolution: export them.** (The TS surface is otherwise legitimately more granular —
engine-specific helpers; noted, not changed.)

**P2. Docs written from the repo-developer’s seat.** README “Try the Python Package”
(`uv sync`, `uv run`, repo-only module paths), every guide playbook
(`uv run softschema`), `installation.md` missing the pin-as-dependency model entirely,
the CI playbook contradicting the pinned-dependency decision, and no doc mentioning the
new binding keys. **Resolution: the README/guide/installation rework (beads ss-kkdl,
ss-dif0) executed in this cycle with the binding story front and center; repo-relative
workflows moved to development docs; `--model` trust note added (model imports execute
local code; `--schema` is the safe path for untrusted input).**

**P3. Example artifact not self-describing.** `spirited-away.md` lacked `schema:` and
(per D1) `envelope:`. **Resolution: the artifact gains both, making the quickstart a
genuine zero-flag `softschema validate spirited-away.md`.**

**P4. `docs example-schema` missing.** The compiled movie schema was bundled but
unaddressable, so no quickstart could be runnable outside the repo.
**Resolution: add the topic in both CLIs + resource manifests (bead ss-hrnm).**

**P5. Test names still saying “sidecar”.** Contributor-facing only.
**Resolution: rename in test files.**

**Noted, intentionally unchanged:** `doctor` output is environment-dependent and stays
outside the golden corpus (unit-tested per language); `inspect` is JSON-only by design;
the TS catch-all error boundary is acceptably close to Python’s broad `_USER_ERRORS`
tuple; Python serializes the result dataclass while TS pre-builds the output mapping
(both byte-identical under golden coverage — a maintenance note, not a bug).

## Release Gate

0.2.0 ships only when: both implementations accept the four-key metadata block with the
precedence above; the movie example validates with zero flags; the golden corpus covers
bind/override/reject/escape cases byte-identically on py, ts, and ts-bun plus the
cross-impl diff; and every user-facing doc teaches the installed-user workflow.

## Release Outcome (2026-06-11)

Released as **0.2.0** to PyPI and npm.
Staged through PR #14 (`claude/release-0.2.0`): npm `package.json` bumped to 0.2.0, CI
green across the full matrix (build 3.11–3.14, golden ×3, typescript, cross-impl),
merged to `main`, tagged `v0.2.0` on the merge commit, and published by `publish.yml`
over OIDC (PyPI + npm in one run).
Full validation per the [end-to-end testing runbook](../../e2e-testing.runbook.md): 142
Python tests, 160 TypeScript tests, golden 46/44/46 (py/ts/ts-bun), cross-impl
byte-identical, and the clean-environment wheel/tarball/quickstart/skill phases.
Post-publish, both registries serve 0.2.0 and the published CLIs report
`softschema 0.2.0`.

Two process corrections fell out of doing the release and are folded into the docs: the
`format-check` make target now runs the full format pipeline before diffing (it
previously reported false drift on a clean tree), and the Phase 5 post-publish smoke
test now overrides the cool-off cutoff to the current instant, runs from outside the
repo, and passes `--refresh` (the prior `$(date +%F)` form excluded a same-day publish).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
