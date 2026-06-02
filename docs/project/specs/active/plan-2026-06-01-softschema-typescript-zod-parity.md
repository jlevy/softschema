# Feature: Softschema TypeScript/Zod Parity (and Phase 0 Cleanup)

**Date:** 2026-06-01 (last updated 2026-06-01)

**Author:** Joshua Levy (with agent assistance)

**Status:** Draft

## Overview

Two linked deliverables:

1. **Phase 0 — Python cleanup.** A senior-engineering review of the current Python
   package surfaced a handful of doc/code drifts and dead surfaces left over from the
   internal-package port. Fix them first so the language-neutral contract that the
   TypeScript port must match is clean and accurate.
2. **Phases 1–4 — TypeScript/Zod port.** Design and build an idiomatic TypeScript
   implementation in `packages/typescript`, using Zod 4 as the source-schema layer the
   way Pydantic is used in Python. The two implementations must agree on the
   language-neutral artifact format, the JSON Schema sidecar, and the observable CLI
   behavior — proven by a **single shared golden-test corpus** run against both CLIs.

The non-negotiable invariant: the Markdown/YAML artifact format and the JSON Schema
sidecar are the portability boundary (per
[softschema-spec.md](../../../softschema-spec.md) and the Cross-Language Boundary
section of the [public-readiness plan](plan-2026-05-24-softschema-public-readiness.md)).
Pydantic and Zod are *implementation* schema layers on either side of that boundary;
neither leaks into the neutral surface.

## Goals

- Land a clean Phase 0: remove or document every undocumented/dead surface in the Python
  package so "parity" has an honest target.
- Ship `@softschema/core` (TypeScript) with feature parity to the documented Python
  public surface: validation, JSON Schema compile, schema-view reader, soft-field
  annotations, generated sections, and the CLI.
- Keep the TypeScript port **idiomatic Zod/TS**, not a transliteration of Python.
- Establish **one** golden-test corpus (tryscript) that exercises both the Python and
  TypeScript CLIs and proves byte-level behavioral parity where it matters.
- Make the JSON Schema sidecar interoperable: a sidecar compiled from a Pydantic model
  and one compiled from the equivalent Zod schema must be structurally equal (or their
  differences must be explicitly enumerated and justified).

## Non-Goals

- No new runtime *features* beyond what the Python package already ships (no repair
  loops, alias resolution, URN registry, provider adapters, body-form bridges — all
  remain deferred for both languages, per the public-readiness plan's Deferred Work).
- No monorepo tooling overhaul. Python stays uv-driven; TypeScript adds a self-contained
  pnpm package under `packages/typescript`. They share test corpora and CI, not build
  systems.
- No attempt to make Zod refinements portable across languages. Cross-field invariants
  stay implementation-specific (Pydantic validators / Zod refinements); only the JSON
  Schema structural subset travels.
- No publish/release of the TypeScript package to npm in this plan (tagging is a
  follow-up once the API is proven against the golden corpus).

## Background

### What exists today

- `packages/python/src/softschema/` — the reference implementation: `models.py`,
  `registry.py`, `validate.py`, `compile.py`, `schema_view.py`, `soft_field.py`,
  `generate.py`, `cli.py`.
- `packages/typescript/README.md` — a stub that commits to "idiomatic port, Zod source
  schemas, JSON Schema sidecars exported from Zod, result shape matching Python
  conceptually."
- 63 pytest unit/integration tests; **no CLI-level golden tests** today.
- CI (`.github/workflows/ci.yml`) runs lint + pytest + build across Python 3.11–3.14.

### Guidance consumed for this plan

- **Golden testing** (`tbd guidelines golden-testing-guidelines`): model events with
  stable/unstable field classification; capture full output, not surgical slices; use
  **tryscript** for console-output golden tests of CLIs; keep scenarios few, end-to-end,
  fast (<100ms); commit session files as behavioral specs.
- **TypeScript house rules** (`tbd guidelines typescript-rules`,
  `typescript-yaml-handling-rules`, `typescript-cli-tool-rules`): Zod 4.x; `yaml@2.x`
  (not `js-yaml`), centralized stringify options with sorted keys for deterministic
  diffs; `commander` for CLIs; `vitest` for tests; no `any`; lowerCamelCase (not
  `LLM`-style all-caps); 14-day supply-chain cool-off on every dependency.

## Senior Engineering Review (informs Phase 0)

Overall the Python package is in good shape: small, layered cleanly (models → registry →
validate; compile/schema_view/soft_field/generate as orthogonal feature modules), well
documented, with a deterministic JSON-emitting CLI that is *already* ideal for golden
testing. The review found no correctness bugs in the validation core. The issues below
are **doc/code drift and dead surface** — exactly the things that make a port chase
ghosts.

### Findings

**F1 — gzip-on-read is still in the code, but the plan says it was removed.**
`validate.py` still carries `.gz` handling (`import gzip`, `_read_frontmatter_doc`,
`_read_yaml`, `_temporary_text_artifact` at `validate.py:5,479-490,542-556`). The
public-readiness plan's *Capability Roadmap* explicitly lists "gzip-on-read … removed
because they served private-history shapes, not the public concept." This is leftover
from the internal port. It is untested, undocumented, adds a tempfile round-trip, and
would force the TypeScript port to either copy a private-history wart or diverge.
**Cut it.**

**F2 — `ValueResolver` has a dead third mode and re-introduces "value-path contracts."**
`ValueResolver` supports `values_key` / `frontmatter_root` / `host_adapter`
(`validate.py:82-105`). The contract path (`validate_artifact` → `_resolver_for_binding`)
only ever produces `values_key`/`frontmatter_root`. `host_adapter` (and the
`HostAdapter` type) is reachable only through the lower-level public `validate()` function
and its one test. Meanwhile the plan claims "value-path contracts … removed." The
lower-level `validate()` + `ValueResolver` API is genuinely *parallel* to
`validate_artifact()` with **different default envelope semantics** (`validate()` defaults
to `frontmatter_root` excluding `softschema`; the spec's rule is single-key envelope
inference). Two entry points with divergent defaults is a maintenance trap and a parity
hazard. **Decide:** either (a) demote `validate()`/`ValueResolver`/`HostAdapter` to
internal helpers (drop from `__all__`) and make `validate_artifact` the one public entry,
or (b) document `validate()` as a supported "values from elsewhere" API and align its
envelope default with the spec. Recommendation: **(a)** — keep `validate_values()` (the
genuinely useful "I already have a dict" helper) public, make `validate()` +
`ValueResolver` internal. The TypeScript port then implements only `validateArtifact` +
`validateValues`.

**F3 — `Contract.owner` is an undocumented, unused field.** `models.py:54`
(`owner: str | None = None`) is not in the design doc's Contract Semantics list and is
read nowhere. **Remove it** (or document it if a host actually needs it — none does
today).

**F4 — `SchemaStage` / `Contract.stage` is computed but never consumed.**
`models.py:27-66` plus an `__all__` export. Nothing in validation, CLI, or tests reads
`.stage`. It's a plausible "continuum position" concept but currently pure dead weight,
and porting it to TS would be speculative work. **Decide:** keep as a documented,
intentionally-public concept (then add a one-line consumer or at least a doc paragraph + a
test that pins its truth table), or remove it. Recommendation: **remove for now**; it's
cheap to re-add when a consumer earns it, and it keeps the parity surface minimal.

**F5 — `engine` field is overloaded to carry skip reasons.** In
`_validate_extracted_values` (`validate.py:399-401`) a skipped structural result sets
`engine="skipped_inferred_via_model"` / `"skipped_no_schema"`. The `engine` field
nominally names the validation engine (`"json_schema"`). Overloading it as a status string
is a minor smell and an easy thing for the TS port to get subtly wrong. Prefer an explicit
`skipped_reason: str | None` on `StructuralResult` mirroring `SemanticResult`, and keep
`engine` honest. Small, optional, but worth doing before locking the result shape the TS
side must match.

**F6 — `_resolve_schema_path` walks all of `cwd().parents`.** `validate.py:422-433`
searches `doc_path.parent`, then `cwd`, then **every ancestor of cwd** for a relative
schema path. That's a surprisingly broad filesystem search that can silently bind to an
unrelated `*.schema.yaml` higher up the tree. Tighten to a documented, bounded search (doc
dir, then cwd, stop) so the resolution rule is portable and the TS port can match it
exactly. This is the one finding with mild correctness/safety weight.

**F7 — Result-shape duplication.** `ValidationResult.ok` and `ArtifactValidationResult.ok`
repeat the same `structural.ok and semantic.ok`. Harmless in Python; note it so the TS
port factors it once.

### Non-issues (validated, no action)

- Two-layer structural/semantic separation, independent reporting: matches spec, keep.
- `status` is informational and does not gate validation: matches spec, keep.
- Deterministic JSON output (`sort_keys=True`, `_plain` normalizer in `cli.py:497-516`):
  this is *exactly* what makes the CLI golden-testable. Preserve byte-for-byte and make
  the TS CLI match it.
- `compile.py` SHA-256 over canonical JSON, atomic write, `--check` drift mode: clean; the
  TS compiler must reproduce the same canonicalization to keep sidecar hashes equal.

## Design

### Cross-language architecture

```text
                 Markdown/YAML artifact  +  JSON Schema sidecar (YAML)
                 ────────────── portability boundary (spec) ──────────────
   Python side                                              TypeScript side
   ───────────                                              ───────────────
   Pydantic model  ──compile──► sidecar ◄──compile──  Zod schema
   validate_artifact()                                 validateArtifact()
   SchemaView / SoftField / generate                   SchemaView / softField / generate
   softschema CLI (argparse)                           softschema CLI (commander)
                         │                                       │
                         └──────────► shared golden corpus ◄─────┘
                              tests/golden/  (tryscript .md scenarios)
```

The sidecar is the interop contract: a Zod-compiled sidecar and a Pydantic-compiled
sidecar for the equivalent model must be structurally identical. Where Zod's JSON Schema
export legitimately differs from Pydantic's (e.g. `$defs` naming, `additionalProperties`
emission), the plan enumerates the differences and the `SchemaView` reader on both sides
absorbs them — exactly as the Python `SchemaView` already absorbs Pydantic's
`anyOf: [{$ref}, {type: null}]` optional shape.

### TypeScript package shape

`packages/typescript/` as a self-contained pnpm package, published later as
`@softschema/core` (name decision deferred per public-readiness Open Questions; this plan
assumes `@softschema/core` with a `softschema` bin).

```text
packages/typescript/
  package.json            # type: module; bin: softschema; deps: zod, yaml, commander
  tsconfig.json
  src/
    models.ts             # Contract, SchemaStatus, SchemaProfile, SchemaMetadata, WarningCode, SchemaWarning
    registry.ts           # Contracts
    validate.ts           # validateArtifact, validateValues, result types
    compile.ts            # compileSchema (Zod -> JSON Schema YAML sidecar), SHA-256, --check
    schemaView.ts         # SchemaView, FieldInfo (reader over the sidecar)
    softField.ts          # softField() helper, SoftFieldMeta, SoftOwner/SoftTier/RepairKind
    generate.ts           # parseSections, regenerate (enum_table, field_list, vocab)
    cli.ts                # commander program mirroring the Python subcommands
    settings.ts           # centralized YAML stringify + JSON canonicalization options
  test/                   # vitest unit tests (idiomatic per-module coverage)
  README.md               # replaces the stub
```

### Idiomatic Zod choices (not transliteration)

- **Source schema = Zod object.** Where Python writes a Pydantic `BaseModel`, TS writes
  `z.object({...})`. `extra="forbid"` ↔ `.strict()`.
- **Validation = `safeParse`.** `validateValues(values, { schema, jsonSchema })` returns a
  result object; never throw on validation failure (throw only on programmer error, per
  error-handling rules). Map Zod's `error.issues` into the same structural error record
  shape the Python side emits (`{ path, message, validator, value }`), normalizing so
  golden diffs line up.
- **Soft-field annotations via a Zod-native carrier.** Python piggybacks on Pydantic's
  `json_schema_extra`. Zod 4 supports `.meta()` / registries; the TS `softField()` helper
  attaches the `x-softschema` block through `.meta({ "x-softschema": {...} })` (or
  `z.registry`), and the compiler lifts it into per-property JSON Schema `x-softschema`.
  Same emitted sidecar shape; idiomatic Zod mechanism.
- **JSON Schema export.** Use Zod 4's built-in `z.toJSONSchema()` (target draft 2020-12).
  Wrap with the same `_augment_schema` logic: add `$schema`, `$id`, `x-softschema` root
  block (`contract`, `generated_from`, `softschema_format_version`, `schema_sha256`). The
  SHA-256 must be computed over the **same canonical JSON** the Python side uses
  (`JSON.stringify` with recursively sorted keys + `","`/`":"` separators to match
  Python's `json.dumps(sort_keys=True, separators=(",",":"))`).
- **YAML I/O** via `yaml@2.x` with centralized `settings.ts` options (sorted keys, no
  forced quoting) — matches `typescript-yaml-handling-rules`. Frontmatter read/write:
  evaluate `gray-matter` vs a thin custom splitter; prefer whatever produces YAML that
  round-trips identically to Python's `frontmatter-format` output for the corpus.
- **Result types** are discriminated unions / readonly interfaces, documented on the type
  (per `typescript-rules`), factoring the shared `ok = structural.ok && semantic.ok` once
  (addresses F7).

### Parity mapping (Python ↔ TypeScript)

| Concept | Python (current) | TypeScript (target) | Parity contract |
| --- | --- | --- | --- |
| Source schema | Pydantic `BaseModel`, `extra="forbid"` | `z.object().strict()` | Same JSON Schema sidecar |
| Contract record | `Contract` (pydantic model) | `Contract` (interface/Zod) | Same fields: `id`, `schema`, `envelopeKey`, `status`, `profile`, `schemaPath` |
| Registry | `Contracts` | `Contracts` | `register`/`resolve`/`all`; dup-id error |
| Status enum | `SchemaStatus` (StrEnum) | `SchemaStatus` (Zod enum / union) | `soft`/`permissive`/`enforced` |
| Profile enum | `SchemaProfile` | `SchemaProfile` | `frontmatter-md`/`pure-yaml` |
| Metadata parse | `parse_schema_metadata` | `parseSchemaMetadata` | Same accepted shapes + errors |
| Artifact validate | `validate_artifact()` | `validateArtifact()` | Same result JSON, same error `kind`s |
| Values validate | `validate_values()` | `validateValues()` | Same result shape |
| Structural | jsonschema Draft2020 | `ajv` (2020 dialect) | Same error records (normalized) |
| Semantic | `model.model_validate` | `schema.safeParse` | Same pass/fail; impl-specific messages |
| Compile | `compile_model()` | `compileSchema()` | **Byte-equal sidecar** (or enumerated diffs) |
| Schema reader | `SchemaView`/`FieldInfo` | `SchemaView`/`FieldInfo` | Same `iter_fields`/`enum_values`/`softmeta`/group-owner-tier filters |
| Field annotations | `SoftField()` | `softField()` | Same emitted `x-softschema` per-property block |
| Generated sections | `regenerate()` 3 kinds | `regenerate()` 3 kinds | **Byte-equal** rendered markers |
| Warning codes | `WarningCode` (`document-*`) | same string union | Same codes, same emission rules |
| Error kinds | `parse_error`, `envelope_mismatch`, … | same snake_case strings | Same strings — pinned by golden corpus |
| CLI | argparse, JSON stdout | commander, JSON stdout | **Byte-equal** stdout for shared scenarios |

The error-`kind` strings and warning codes are **string-level contracts**, not just
concepts. The golden corpus pins them so a rename on one side fails CI on both.

### Shared golden-test corpus (the parity engine)

This is the heart of the plan and the answer to "creative ways to keep testing simple but
high-coverage and parity-safe." Following the golden-testing guideline's **console output
capture** strategy with **tryscript**:

- **One corpus, two CLIs.** `tests/golden/` at the repo root holds tryscript `.md`
  scenario files. Each scenario runs the *same* sequence of CLI commands against a fixture
  artifact and captures full stdout/stderr/exit-code. A small driver runs every scenario
  twice — once with `SOFTSCHEMA=python` (→ `uv run softschema …`) and once with
  `SOFTSCHEMA=ts` (→ `node packages/typescript/dist/cli.js …` or `pnpm softschema`). Both
  must satisfy the *same* expected output block.
- **Why this works:** the CLI already emits deterministic, key-sorted JSON
  (`cli.py:_json`). If the TS CLI emits the same normalized JSON, a single expected-output
  block validates both implementations. Parity is then a *test pass*, not a manual audit.
- **Stable vs unstable fields:** the only unstable values in CLI output are absolute paths
  and the schema SHA-256. Per the guideline's anti-pattern rules, pattern **only** the
  truly-unstable fields via tryscript frontmatter patterns (`SHA256: '[0-9a-f]{64}'`,
  `PATH: '...'`), and show everything else literally. Do **not** pattern stable values like
  contract IDs, statuses, error kinds, or enum tables.
- **Scenario set (few, end-to-end, <100ms each):**
  1. `validate-happy` — movie example validates clean (structural + semantic ok).
  2. `validate-semantic-fail` — bad enum / out-of-range → exit 1, semantic errors shown.
  3. `validate-envelope-errors` — missing envelope, ambiguous multi-key, no metadata.
  4. `compile-and-check` — compile a model/schema, then `--check` clean, then mutate →
     drift exit 1. (SHA-256 patterned.)
  5. `generate-sections` — render `enum_table`/`field_list`/`vocab`; `--check` drift.
  6. `inspect-and-docs` — `inspect`, `docs --list --json`, `skill --brief` smoke.
- **Cross-language sidecar equality test:** one targeted assertion (per the guideline's
  "layer domain-focused assertions") that compiles the movie schema from *both* Pydantic
  and Zod and asserts the two sidecars are byte-equal after canonicalization — or diffs
  against a committed `expected-diffs.md` enumerating each justified difference.
- **Update workflow:** `tryscript` runs in check mode in CI and `--update` (or equivalent)
  locally; golden files are committed as behavioral specs and reviewed in PRs.

This gives **high coverage with very few artifacts**: ~6 scenario files cover the whole
CLI surface for *both* languages, and a single SHA-256 pattern + path pattern handle all
nondeterminism. No mocks are needed — softschema has no network/clock/RNG dependencies, so
the corpus is fully hermetic by construction.

### CI integration

- Add a `golden` job that, on the Python side, runs `npx tryscript@latest tests/golden`
  with `SOFTSCHEMA=python` (works today, immediately, even before the TS package exists —
  Phase 0/1 land the Python-side corpus first).
- Once the TS package builds, add a matrix dimension (or a second job) that builds the TS
  package and runs the **same** corpus with `SOFTSCHEMA=ts`. Green on both = parity.
- Keep the existing `pytest` and `vitest` unit jobs for per-module edge cases the
  guideline says golden tests should be *supplemented* by, not replaced with.

## Implementation Plan

### Phase 0: Python cleanup (clean the parity target)

Land before any TS work so the contract the port matches is honest. Each item is small and
independently testable; group into one PR.

- [ ] **F1:** Remove gzip-on-read (`import gzip`, `.gz` branches in
  `_read_frontmatter_doc`/`_read_yaml`, `_temporary_text_artifact`). Update the plan's
  Capability Roadmap claim to be true.
- [ ] **F2:** Make `validate()` + `ValueResolver` + `HostAdapter` internal (drop from
  `__all__`); keep `validate_values()` and `validate_artifact()` public. Move/adjust the
  three `test_core.py` resolver tests accordingly. Document the single public entry in
  `softschema-python-design.md`.
- [ ] **F3:** Remove `Contract.owner`.
- [ ] **F4:** Remove `SchemaStage` and `Contract.stage` (and the `__all__` export), or —
  if kept — add a doc paragraph + truth-table test. Default: remove.
- [ ] **F5:** Add `skipped_reason` to `StructuralResult`; stop overloading `engine`. Update
  affected tests and the documented result shape.
- [ ] **F6:** Bound `_resolve_schema_path` to (doc dir, cwd) and document the rule.
- [ ] **F7:** Note the `ok` duplication (no code change required in Python; informs TS).
- [ ] Introduce `tests/golden/` with the **Python-side** tryscript corpus (scenarios 1–6
  above) and wire a `golden` CI job running `SOFTSCHEMA=python`. This locks the observable
  behavior *before* the port begins — the corpus becomes the spec the TS side targets.
- [ ] Re-run `devtools/lint.py --check`, `pytest`, `uv build`; update
  `softschema-python-design.md` and the public-readiness plan's roadmap wording.

### Phase 1: TypeScript package skeleton + compile/validate core

The smallest end-to-end vertical slice that can pass golden scenarios 1, 2, and 4.

- [ ] Scaffold `packages/typescript` (pnpm, `type: module`, tsconfig strict). Pin deps with
  the 14-day cool-off: `zod@^4`, `yaml@^2`, `commander`, ajv (for structural), and
  `vitest`/`tsx` dev deps. Replace the stub README.
- [ ] `settings.ts`: centralized YAML stringify options (sorted keys) and a
  `canonicalJson()` matching Python's `json.dumps(sort_keys=True, separators=(",",":"))`.
- [ ] `models.ts` + `registry.ts`: `Contract`, enums, `parseSchemaMetadata`, `Contracts`
  with dup-id error parity.
- [ ] `compile.ts`: `compileSchema(zodSchema, outPath, { contractId, checkOnly })` using
  `z.toJSONSchema()` + the `x-softschema` augmentation + SHA-256 + atomic write +
  `--check` drift. Validate byte-equality against the committed Pydantic sidecar (the
  cross-language equality assertion); record any justified diffs.
- [ ] `validate.ts`: `validateValues` and `validateArtifact` with the documented result
  shape and the exact error-`kind` strings; structural via ajv (2020 dialect), semantic via
  `safeParse`, error-record normalization.
- [ ] `cli.ts` (commander): `validate`, `compile`, `inspect` subcommands emitting JSON
  byte-identical to Python's `_json` normalizer.
- [ ] Run golden scenarios 1, 2, 4 with `SOFTSCHEMA=ts`; add the TS-side `golden` CI job.

### Phase 2: TypeScript schema-view, soft-field, generated sections

Reaches full feature parity; passes the remaining golden scenarios (3, 5, 6).

- [ ] `schemaView.ts` + `FieldInfo`: port `iter_fields` (with `$ref`/`$defs` walking and
  the optional-`anyOf` shapes Zod emits), `enumValues`, `softmeta`, `fieldsByGroup`/
  `ByOwner`/`ByTier`. Pin against the committed movie sidecar.
- [ ] `softField.ts`: `softField()` carrier via Zod `.meta()`/registry → per-property
  `x-softschema`. Same emitted block; same omit-empty-defaults rules.
- [ ] `generate.ts`: `parseSections`/`regenerate` with the three renderers producing
  **byte-equal** marker bodies. Add the movie README marker to the corpus for both langs.
- [ ] `cli.ts`: add `generate`, `docs`, `skill` subcommands (docs/skill may read shared
  repo resources or a bundled copy — match Python's topic names).
- [ ] Pass golden scenarios 3, 5, 6 on both languages.

### Phase 3: Parity hardening + docs

- [ ] Stand up the cross-language sidecar-equality assertion in CI (Pydantic vs Zod) and
  commit `expected-diffs.md` if any differences are justified.
- [ ] Add `vitest` unit tests for TS-specific edge cases (Zod-vs-Pydantic JSON Schema
  quirks, YAML round-tripping) — supplementing, not duplicating, the golden corpus.
- [ ] Write `packages/typescript/README.md` and a `softschema-typescript-design.md`
  mirroring the Python design doc, plus a "Parity" section in the guide/spec noting that
  two reference implementations now exist and the corpus enforces their agreement.
- [ ] Update `AGENTS.md`/`SKILL.md` to mention the TS implementation.

## Testing Strategy

- **Golden corpus (primary, cross-language):** tryscript scenarios in `tests/golden/`, run
  against both CLIs via a `SOFTSCHEMA={python,ts}` switch. Few scenarios, full output
  capture, only SHA-256 + paths patterned, fully hermetic, <100ms each. This is the parity
  guarantee.
- **Cross-language sidecar equality:** one assertion compiling the movie schema from both
  Pydantic and Zod, comparing canonicalized sidecars.
- **Unit tests (secondary, per-language):** existing pytest suite (extended for Phase 0
  changes) + new vitest suite for TS edge cases.
- **Commands:**
  ```bash
  # Python
  uv run python devtools/lint.py --check && uv run pytest && uv build
  # Golden (Python side, works from Phase 0)
  SOFTSCHEMA=python npx tryscript@latest tests/golden
  # TypeScript (from Phase 1)
  pnpm -C packages/typescript build && pnpm -C packages/typescript test
  SOFTSCHEMA=ts npx tryscript@latest tests/golden
  ```

## Rollout Plan

1. Land Phase 0 (cleanup + Python-side golden corpus) as one PR; this is independently
   valuable even if the TS port slips.
2. Land Phases 1–2 behind the golden corpus; the TS package is "done" when it's green on
   the same scenarios as Python.
3. Phase 3 docs + parity hardening.
4. Defer npm publishing of `@softschema/core` to a follow-up once the API is proven.

## Open Questions

- **TS package name:** `@softschema/core` vs unscoped `softschema` (npm) — inherited from
  the public-readiness plan's deferred decisions. Assume `@softschema/core` until decided.
- **Structural engine on the TS side:** `ajv` (closest to jsonschema's behavior and error
  shape) vs re-deriving structural checks from Zod. Recommendation: `ajv` for honest
  two-engine parity with Python; revisit if error-record normalization proves heavy.
- **Frontmatter library:** `gray-matter` vs a thin custom splitter — pick whichever
  round-trips to the same YAML the Python `frontmatter-format` produces for the corpus.
- **Should `validate()`/`ValueResolver` be removed (F2 option a) or documented (option
  b)?** Recommendation: remove from public surface; this is the one Phase 0 decision that
  changes the public Python API, so confirm before landing.

## References

- [Softschema Spec](../../../softschema-spec.md) — the portability boundary the port must
  preserve.
- [Softschema Python Design](../../../softschema-python-design.md) — the surface being
  ported; update for Phase 0.
- [Public Readiness Plan](plan-2026-05-24-softschema-public-readiness.md) — Cross-Language
  Boundary and Future TypeScript/Zod Package sections; this plan executes that intent.
- [Runtime Design v8](../../research/research-2026-05-24-softschema-runtime-design-v8.md) —
  durable design reference.
- `tbd guidelines golden-testing-guidelines` — tryscript, stable/unstable fields,
  transparent-box testing.
- `tbd guidelines typescript-rules` / `typescript-yaml-handling-rules` /
  `typescript-cli-tool-rules` — Zod 4, `yaml@2`, commander, vitest, supply-chain rules.
- [Future TypeScript Notes](../../../../packages/typescript/README.md) — current stub.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
