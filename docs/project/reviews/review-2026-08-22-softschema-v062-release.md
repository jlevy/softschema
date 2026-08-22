---
title: softschema v0.6.2 Release Review
description: Validation record and evidence for the pure-yaml profile patch release
author: Claude, with maintainer direction from Joshua Levy
---
# Review: softschema v0.6.2 Release

**Date:** 2026-08-22

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** Released and externally verified on both registries.

## Decision

Ship v0.6.2 as a **patch**. The release fixes a defect in the CLI’s binding layer and
adds a cache; no public behavior is removed or renamed, so `publishing.md`’s reservation
of a minor bump for public API changes does not apply.
Two surfaces grow, both additively: the `inspect` JSON output gains a `profile` key, and
the TypeScript package exports `clearValidatorCache`.

The fix is worth a release on its own because the defect was **silent**. A project could
adopt pure-YAML datasets, mark them `status: enforced`, wire `softschema validate` into
CI, and get a passing build that validated nothing — the exact failure `status` exists
to prevent. That is not a degraded check; it is the absence of one, reported as success.

## Scope Reviewed

Merged in #39, tagged at `5da09d8`:

- **`a5db704`** — profile resolution in both CLIs (#38).
- **`d209338`** — memoized compiled schemas in TypeScript `validateStructural`.
- **`24ec18f`** — release preparation: `packages/typescript/package.json` to `0.6.2` and
  the CHANGELOG v0.6.2 entry cut from `Unreleased`.

### Why detection, and not a `profile:` metadata key

The issue proposed three fixes.
This release takes detection (its option 1) plus an explicit `--profile` flag (option
3), and deliberately **not** a `profile:` key in the metadata block (option 2).

The spec’s Metadata table is a closed four-key set — `contract`, `schema`, `envelope`,
`status` — and `SchemaMetadata` enforces it with `extra="forbid"`, so unknown keys are a
validation error. Adding a fifth key is a spec change, not a patch.
The issue reasonably inferred precedent from the v0.6.0 changelog’s reference to
`profile: frontmatter-md`, but that refers to a code-level `Contract(profile=...)`
workaround for the single-read path, not to a document key; such a key would have been
rejected by the metadata parser.

Detection also keeps the stronger property: the spec’s promise that a fully
self-describing artifact validates with no flags is now true for **both** profiles,
where a metadata key would have required every pure-yaml artifact to declare something
new.

### Ordering the detection rules

The file name is checked **before** the frontmatter fence, which is the non-obvious
part. A YAML document may legitimately open with the `---` document-start marker, which
the frontmatter reader scans as the start of a fence and then rejects for having no
closing delimiter. Checking the name first means a `*.yaml` file is never misread that
way.

The content rule requires a root `softschema:` block rather than merely parsing as a
mapping. That is what separates a pure-yaml artifact from prose that happens to parse as
YAML, and it preserves the existing `no_frontmatter` diagnostic for a Markdown document
without frontmatter.

### Two defects found while fixing the reported one

- **Envelope inference reached pure-yaml.** The spec exempts the profile from single-key
  inference and multi-key ambiguity rejection, because a pure-yaml artifact’s whole root
  minus the metadata block is the payload.
  Without this, the issue’s own two-key reproduction would have been rejected as
  ambiguous the moment the profile was resolved correctly — a fix that swapped one wrong
  answer for another.
- **`inspect` was equally blind**, reporting `metadata: null` for a pure-yaml artifact’s
  root metadata block.
  It now resolves the profile through the same code path as `validate`, so the two
  commands cannot disagree about what a file is.

## Validation Record

### Phase 1 — Automated sweep (mirrors CI)

| Check | Result |
| --- | --- |
| `make lint-check` (codespell, ruff, basedpyright, doc footers) | Pass; basedpyright 0 errors |
| `uv run pytest` | 176 passed |
| `uv build` | wheel + sdist |
| `bun run check` (biome, tsc, tests + coverage gate) | 176 passed |
| `bun run build`, `bun run publint` | Pass; publint “All good!” |
| Golden corpus — Python / Node / Bun | 44 / 42 / 44 |
| `cross-impl-diff.sh` | “cross-impl parity OK” |
| `make format-check` | Exit 0 on a clean tree |

Golden counts rose by 6 on every runtime: five new pure-yaml scenarios in
`metadata-binding.md` and one in `inspect-and-docs.md`. TypeScript tests rose by 4, the
validator-cache unit tests.

One `make format-check` detail worth not re-investigating next time: its log contains
`"drift": true` for the `enum_table` section, because the target runs `flowmark --auto`
and then `softschema generate`, and generate rewrites what flowmark reflowed.
The net result is a fixed point, which is what the target actually asserts with
`git diff --exit-code`. `main` at `9cd14cd` produces the identical log; it is not drift.

### Phase 2 — Clean-environment installs

| Check | Result |
| --- | --- |
| Wheel in a fresh venv: `--version`, `docs --list`, `skill --brief` | All exit 0 |
| Wheel: `validate` on the frontmatter-md example, zero flags | Exit 0 |
| Wheel: `validate` on a pure-yaml artifact, zero flags | Exit 0, `profile: pure-yaml` |
| `npm pack` tarball under plain Node (runs `prepublishOnly`) | `softschema 0.6.2` from both `dist/cli.js` and the `.bin` shebang |
| Tarball: `validate` on frontmatter-md and pure-yaml, zero flags | Both exit 0 |

The pure-yaml case was added to this phase for this release: the defect was in the CLI
binding, so proving it from an installed package rather than the source tree is the
check that matters.

### Phases 3–4

| Check | Result |
| --- | --- |
| README quickstart verbatim from an empty directory, both implementations | Artifact and schema output byte-identical across implementations |
| Agent skill bootstrap into a scratch git repo | Both `SKILL.md` mirrors reported `created` and present on disk |

### Parity sweep on profile detection

Beyond the golden corpus, both CLIs were run directly against 14 detection edge cases
and agreed on every one: a `*.yaml` file opening with `---`, a pure-yaml artifact with
no `*.yaml` name, plain Markdown, Markdown that parses as a YAML mapping without a
`softschema:` block, empty and list-root YAML, malformed YAML, multi-key pure-yaml, both
`--profile` overrides, and the name forms `.yaml` (a dotfile), `UPPER.YAML`, and
`x.tar.yaml`.

That last group found a real divergence before it shipped: TypeScript’s natural
`endsWith(".yaml")` treats a file named exactly `.yaml` as a YAML file, while Python’s
`Path.suffix` treats a leading dot as part of the name and returns `""`. TypeScript now
implements `Path.suffix` semantics, so both fall through to content detection there.

Two differences remain and are expected: operating-system file-error text (`[Errno 2]`
vs `ENOENT`) and enum-flag rejection wording (argparse’s usage block vs a one-line
message). Both are pre-existing conventions — `--status` already behaves this way — and
the golden corpus asserts only their stable boundary and exit class.

### CI on the release PR

Run `32604238924` on #39: **18/18 jobs green**, including the cross-platform
artifact-smoke matrix (Linux, macOS, Windows × Python 3.11 and 3.14).

### Publish

Workflow run `32604564449`, triggered by publishing the GitHub release, completed with
all four jobs green: `build-candidates`, `smoke-candidates`, `Publish to PyPI`,
`Publish to npm`. Both registries published from one tag and one build over OIDC trusted
publishing, with no stored tokens.

### Phase 5 — Post-publish registry verification

| Check | Result |
| --- | --- |
| `uvx --refresh --exclude-newer-package "softschema=<now>" softschema@0.6.2 --version` | `softschema 0.6.2` (second attempt; see below) |
| `npx -y softschema@0.6.2 --version` | `softschema 0.6.2` |
| Issue #38’s reproduction, verbatim, against published PyPI | Exit 0, `profile: pure-yaml`, payload extracted |
| Issue #38’s reproduction, verbatim, against published npm | Exit 0, byte-equal JSON to the Python result |
| An `enforced` pure-yaml artifact violating its bound schema, both registries | Exit 1, `schema_violation` at `['name']` in both |

The last row is the one that matters: it proves the published artifacts fail a build
that should fail, which is the behavior whose absence caused the issue.

## Risk Review

| Risk | Control | Residual risk |
| --- | --- | --- |
| Detection reclassifies an existing frontmatter-md artifact | Content rule requires a root `softschema:` block; full golden corpus and a 14-case parity sweep re-run | None observed; plain and map-like Markdown still report `no_frontmatter` |
| The two runtimes detect differently | Detection implemented identically and swept directly; `Path.suffix` semantics matched in TypeScript | None across the cases tested |
| A stale cache entry serves a wrong validator | Keyed on schema content plus the overlay flag; unit tests cover an edited schema, both overlay orders, and an invalid schema | None; an invalid schema is never cached |
| `inspect` output change breaks a consumer | Additive key only; `has_frontmatter` semantics unchanged | Low; a consumer reading unknown keys strictly would need to allow `profile` |
| Package versions diverge | `package.json` set to `0.6.2`; publish guard compares tag against both built artifacts | None after guard passes |
| Registry index propagation lags | `--refresh` plus a now-timestamped cool-off override, and retry | None; resolved on retry |

## Process Notes

**The tag push was blocked, and the documented fallback worked.** In this session the
`git push origin v0.6.2` was refused before reaching the network.
`publishing.md` step 5 already prescribes the remedy for the proxied-session case —
`gh release create vX.Y.Z --target <merge-sha>` creates the tag at the merge commit as
part of publishing the release — and it produced a tag pointing at `5da09d8`, verified
against the GitHub ref API before watching the publish run.
Note that the tag `gh` creates this way is a lightweight ref, not the annotated object a
local `git tag -a` would push; the publish guard compares `GITHUB_REF_NAME` against the
built artifacts, so this makes no difference to the release, but a local annotated tag
created in anticipation should be deleted afterward to avoid a confusing local/remote
divergence.

**PyPI propagation lagged in the opposite direction from the runbook’s description.**
The first `uvx` attempt failed with `no version of softschema==0.6.2`. Phase 5 explains
this as the JSON API updating before the simple index; here the **simple index already
listed both 0.6.2 files** while the JSON API still reported `0.6.1` as latest.
The cause is CDN edge caching rather than a fixed ordering between the two indexes, so
the useful check is to query the simple index directly (`pypi.org/simple/softschema/`)
to confirm the release is live, then retry; the runbook’s ordering claim should not be
relied on as a diagnostic.

**`gh` needed the scoped `NO_PROXY` from the start**, as #35 documented after v0.6.1.
The session hook prints the recipe, and applying it made `gh auth status` and every
subsequent call work on the first try.
The trap recorded in the v0.6.1 review did not recur.

## Beads Triaged Alongside This Release

Five were open; three are now closed.

- **`ss-lpyg`** (pure-yaml CLI) — fixed here; the same defect as #38.
- **`ss-9pde`** (Ajv recompiled per call) — fixed here.
- **`ss-pnl2`** (TypeScript deep-nesting superlinear) — closed as **obsolete without a
  code change**. The bead recorded 12.5s at depth 5000 on the PR #27 branch.
  Re-measured on `main` before closing: 263ms, rejected as `yaml_limit`, with depth 1000
  at 68ms — a linear curve.
  The `MAX_DEPTH=64` bound, which postdates the measurement, removed the superlinearity
  by bounding the per-node depth walk.
  Recorded here because a stale performance bead is otherwise indistinguishable from a
  live one.
- **`ss-fstu`** (`parse_yaml` parses twice) — left open.
  The preflight pass is what enforces the portable value domain (tags, merge keys,
  aliases, the depth bound) before construction; collapsing it into one pass is a
  redesign of that enforcement with parity implications in both runtimes, not a
  patch-sized change.
- **`ss-cl9j`** (`document: Any` typing) — left open.
  A P3 chore that touches a public signature; deferred to a release where an API-surface
  change is in scope.

Both deferrals carry that reasoning in their bead notes, so the next reader does not
re-derive it.

## Baseline for the Next Release

Counts to compare against, and to investigate on any **drop**:

- Python tests 176; TypeScript tests 176
- Golden corpus: Python 44, Node 42, Bun 44
- basedpyright 0 errors; publint clean; cross-impl parity OK
- CI: 18 jobs on the release PR

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
