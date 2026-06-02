# Feature: Softschema TypeScript/Zod Parity (and Phase 0 Cleanup)

**Date:** 2026-06-01 (last updated 2026-06-02)

**Author:** Joshua Levy (with agent assistance)

**Status:** Draft

## Overview

Two linked deliverables:

1. **Phase 0 — Python cleanup.** A senior-engineering review of the current Python
   package surfaced doc/code drift and dead surface left over from the internal-package
   port, plus one engine-leakage issue (structural error messages pass through the
   `jsonschema` library verbatim). Fix them first so the language-neutral contract the
   TypeScript port must match is clean, minimal, and accurate.
2. **Phases 1–4 — TypeScript/Zod port.** Build an idiomatic TypeScript implementation in
   `packages/typescript`, using Zod 4 as the source-schema layer the way Pydantic is used
   in Python. The two implementations must agree on the artifact format, a **canonical
   JSON Schema sidecar**, and **observable CLI behavior** — proven by a **single shared
   golden-test corpus** (tryscript) run against both CLIs.

**No backward-compatibility constraint.** There is exactly one downstream consumer (the
trading repo's `packages/softschema`); it will be down-migrated with a new release as
needed. So Phase 0 removes dead/leaky surface outright rather than deprecating it, and we
are free to change the Python sidecar/error shapes to land on a clean canonical form that
both languages can hit exactly.

The non-negotiable invariant: the Markdown/YAML artifact format and the canonical JSON
Schema sidecar are the portability boundary (per
[softschema-spec.md](../../../softschema-spec.md) and the Cross-Language Boundary section
of the [public-readiness plan](plan-2026-05-24-softschema-public-readiness.md)). Pydantic
and Zod are *implementation* schema layers on either side of that boundary; neither leaks
into the neutral surface.

## Goals

- Land a clean Phase 0: remove every undocumented/dead surface and the structural-error
  engine leakage so "parity" has an honest, minimal target.
- Ship `@softschema/core` (TypeScript) with feature parity to the documented Python
  public surface: validation, JSON Schema compile, schema-view reader, soft-field
  annotations, generated sections, and the CLI.
- Keep the TypeScript port **idiomatic Zod/TS**, not a transliteration of Python.
- Define a **canonical JSON Schema profile** that both `compile_model` (Pydantic) and
  `compileSchema` (Zod) normalize to, so the two sidecars are **byte-equal** and share the
  same `schema_sha256`. Enumerate every raw Pydantic-vs-Zod divergence and its canonical
  resolution.
- Define **canonical, engine-neutral structural error records** so `jsonschema` (Python)
  and `ajv` (TS) emit identical structural errors for identical inputs.
- Establish **one** golden-test corpus (tryscript) that exercises both CLIs and proves
  byte-level behavioral parity. Build the corpus against the **Python CLI first** (Phase
  0), then implement the TypeScript CLI to pass the **same** corpus unchanged.
- Use exact, current, in-sync dependency versions (verified June 2026; see Verified
  Versions).

## Non-Goals

- No new runtime *features* beyond what the Python package already ships (no repair loops,
  alias resolution, URN registry, provider adapters, body-form bridges — all remain
  deferred for both languages, per the public-readiness plan's Deferred Work).
- No monorepo tooling overhaul. Python stays uv-driven; TypeScript adds a self-contained
  bun package under `packages/typescript`. They share test corpora and CI, not build
  systems.
- **No attempt to make cross-field semantic invariants portable.** Pydantic validators
  and Zod refinements stay implementation-specific; only the canonical JSON Schema
  structural subset travels. Semantic-only failures are tested per-language, not in the
  shared corpus (see Validation Layering).
- No npm publish of the TypeScript package in this plan (tagging is a follow-up once the
  API is proven against the corpus).

## Background

### What exists today

- `packages/python/src/softschema/` — the reference implementation: `models.py`,
  `registry.py`, `validate.py`, `compile.py`, `schema_view.py`, `soft_field.py`,
  `generate.py`, `cli.py`.
- `packages/typescript/README.md` — a stub committing to "idiomatic port, Zod source
  schemas, JSON Schema sidecars exported from Zod, result shape matching Python
  conceptually."
- 63 pytest unit/integration tests; **no CLI-level golden tests** today.
- One console script: `softschema = "softschema.cli:main"` (pyproject `[project.scripts]`).
- CI (`.github/workflows/ci.yml`) runs lint + pytest + build across Python 3.11–3.14.

### Guidance consumed for this plan

- **Golden testing** (`tbd guidelines golden-testing-guidelines`): model events with
  stable/unstable field classification; capture full output, not surgical slices; use
  **tryscript** for console-output golden tests of CLIs (run `npx tryscript@latest docs`
  for syntax); keep scenarios few, end-to-end, fast (<100ms); pattern **only** truly
  unstable fields (IDs, timestamps), never stable known values; commit session files as
  behavioral specs. The console-output-capture strategy is exactly right for proving two
  CLIs behave identically.
- **TypeScript house rules** (`tbd guidelines typescript-rules`,
  `typescript-yaml-handling-rules`, `typescript-cli-tool-rules`): Zod 4.x; `yaml@2.x`
  (not `js-yaml`), centralized stringify options with sorted keys for deterministic diffs;
  no `any`; lowerCamelCase (not `LLM`-style all-caps); document fields on the type, not at
  usage sites; 14-day supply-chain cool-off on every dependency. **CLI tooling**:
  **Commander 15+** (ESM-only, Node ≥22.12; Commander 14 is security-maintenance only —
  do not start new projects on it); `picocolors` for color (never raw ANSI), honoring
  `NO_COLOR`/`FORCE_COLOR`/`--color`; global options `--json`/`--color`/`--quiet`.
- **Python CLI patterns** (`tbd guidelines python-cli-patterns`,
  `python-modern-guidelines`): uv for everything (already adopted); exit codes
  `0` success / `1` error / `2` validation; data→stdout, errors→stderr (softschema already
  does both); `uv-dynamic-versioning` (tag is the version — already adopted); **atomic
  output files**; tag-triggered OIDC publish, no changesets (already adopted via
  `publish.yml` + PyPI Trusted Publishing).
- **Monorepo patterns** (`tbd guidelines bun-monorepo-patterns`,
  `pnpm-monorepo-patterns`): this is a polyglot monorepo — Python under `packages/python`
  (uv), TypeScript under `packages/typescript`. Single TS package ⇒ tag-triggered OIDC
  npm publish (no changesets), `publint` for publishability, the 14-day cool-off enforced
  in the package manager. **Toolchain decided: the bun stack** (bun + bunup + `bun test` +
  biome) — the leanest house-approved option for a small focused CLI/library; both
  guidelines list `tryscript` and `flowmark`, which this repo already uses. See Toolchain
  Alignment.

### Verified Versions (June 2026)

Both schema libraries default to **JSON Schema draft 2020-12**, so the dialects are in
sync at the boundary.

| Layer | Python | TypeScript | Notes |
| --- | --- | --- | --- |
| Source schema | `pydantic` **2.13.4** (pin `>=2.13`) | `zod` **4.4.3** (pin `^4.4`) | Pydantic `model_json_schema()` defaults to draft 2020-12; Zod `z.toJSONSchema()` defaults to `target: "draft-2020-12"`. |
| Structural validator | `jsonschema` **4.26.0** (pin `>=4.26`), `Draft202012Validator` | `ajv` **^8** via `import Ajv2020 from "ajv/dist/2020"` + `ajv-formats@^3` | Ajv cannot mix dialects in one instance; use the 2020 entry point. |
| YAML | (via `frontmatter-format>=0.3`, PyYAML) | `yaml` **^2.8** | Centralized stringify options, sorted keys. |
| Frontmatter | `frontmatter-format` | `gray-matter` **or** thin custom splitter | Pick whichever round-trips to identical YAML for the corpus. |
| CLI framework | `argparse` (stdlib) | `commander` **^15** | Commander 15 is ESM-only, Node ≥22.12. Commander 14 is security-maintenance only — not for new projects. |
| Color | n/a (JSON output) | `picocolors` **^1.1.1** | Help/diagnostic color only; JSON stays uncolored; honor `NO_COLOR`/`--color`. tryscript runs non-TTY ⇒ auto-disabled. |
| Atomic writes | stdlib tempfile+replace (`compile.py`) | `atomically` **^2.1.1** | Matches Python `_write_atomic`; apply to sidecar + generated-section writes. |
| Tests | `pytest` | **`bun test`** (built-in) + the shared `tryscript` **^0.1.6** corpus | bun test has Jest-compatible matchers and built-in `--coverage`. |
| Build | `uv build` | **`bunup` ^0.16** | ESM (+ optional CJS) + `.d.ts`; `bin` → `dist/cli.js`. |
| Lint/format | `ruff` + `basedpyright` | **`biome` ^2.4** + `tsc --noEmit` for types | One tool for lint + format; `publint` **^0.3.20** for publishability. |
| Runtime / PM | Python 3.11–3.14 (uv) | **`bun` 1.3.x** (runtime + package manager) | `oven-sh/setup-bun@v2`; `actions/checkout@v6`. Node available on runners for `npx` fallbacks. |
| Types | `basedpyright` | **`typescript` ^6.0.3** (`tsc --noEmit`), `bun-types` **^1.3** | TS 6.0 (strict default); do not adopt `tsgo`/TS 7 beta. |

All TypeScript dependencies are subject to the 14-day supply-chain cool-off
(`typescript-rules` supply-chain section), enforced with `npm-check-updates --cooldown 14`
when bumping and bun's install gating. Mirrors the Python side's `UV_EXCLUDE_NEWER`
14-days-ago cutoff already set in CI.

### Toolchain Alignment — decided: bun + biome

**Decision: the bun stack** (`bun-monorepo-patterns`). For a focused single-package CLI
that is also a small npm library, bun is the leanest house-approved choice — one tool for
the package manager, runtime, test runner, and (via `bunup`) the library build — paired
with `biome` as a single lint+format tool. This minimizes config and dependencies versus
the pnpm stack's `pnpm + tsdown + vitest + eslint + prettier`. The pnpm stack remains a
valid alternative; the choice does not change the parity design (canonical sidecar, error
records, and the golden corpus are toolchain-agnostic).

| Concern | Chosen (bun) | Alternative (pnpm) |
| --- | --- | --- |
| Package manager / runtime | **bun 1.3.x** | pnpm ^11 + Node 24 |
| Build | **bunup ^0.16** | tsdown ^0.22 |
| Test runner | **`bun test` + `--coverage`** | vitest ^4.1.5 + @vitest/coverage-v8 |
| Lint + format | **biome ^2.4** | eslint ^10 (flat) + prettier ^3.8 |
| Type check | **`tsc --noEmit`** (TS ^6.0.3) | same |
| CI setup action | **`oven-sh/setup-bun@v2`** | `pnpm/action-setup@v6` |
| Shared by both | `commander@^15`, `zod@^4.4`, `yaml@^2.8`, `ajv@^8` (+`ajv-formats`), `picocolors`, `atomically`, `publint`, `tryscript`, tag-triggered OIDC publish (no changesets), `flowmark` for Markdown | — |

**Conformance note on coverage.** `typescript-code-coverage` is written for Vitest +
`@vitest/coverage-v8`. With bun we use `bun test --coverage` (lcov), but we hold to the
**same thresholds** from that guideline — statements ≥ 80%, branches ≥ 75%, functions ≥
80%, lines ≥ 80% as targets (starting floors 70/65/70/70) — and the same include/exclude
rules (exclude `dist/`, `*.d.ts`, test files, fixtures). Branch coverage matters most
here given the union types in the result/error records.
Confirm before Phase 1 scaffolding (`ss-d0id`); the Verified Versions rows above carry
both columns so neither choice is blocked.

## Senior Engineering Review (informs Phase 0)

The validation core is sound — no correctness bugs. The issues below are doc/code drift,
dead surface, and one engine-leakage problem. With no backward-compat constraint, the
decisions are decisive removals/changes, not deprecations.

### Findings

**F1 — gzip-on-read is still in the code, but the plan says it was removed.** `validate.py`
still carries `.gz` handling (`import gzip`; `_read_frontmatter_doc`, `_read_yaml`,
`_temporary_text_artifact` at `validate.py:5,479-490,542-556`). The public-readiness
plan's *Capability Roadmap* lists "gzip-on-read … removed." Leftover from the internal
port: untested, undocumented, adds a tempfile round-trip, and would force the TS port to
copy a private-history wart. **Cut it.**

**F2 — `validate()` + `ValueResolver` is a parallel public entry with divergent envelope
defaults and a dead mode.** `ValueResolver` supports `values_key` / `frontmatter_root` /
`host_adapter` (`validate.py:82-105`); the contract path only ever produces the first two,
so `host_adapter` + the `HostAdapter` type are dead. The lower-level public `validate()`
defaults to `frontmatter_root` excluding `softschema`, which **diverges from the spec's
single-key envelope inference** that `validate_artifact()` uses. Two public entry points
with different default semantics is a parity hazard. **Decision (no backcompat): remove
`validate()`, `ValueResolver`, `HostAdapter` from the public surface.** Keep
`validate_values()` (the useful "I already have a dict" helper) and `validate_artifact()`
as the two public entries. Internally, `validate_artifact` resolves the envelope directly
(single-key inference / explicit `envelope_key`) without a `ValueResolver` indirection.
The TS port implements only `validateArtifact` + `validateValues`.

**F3 — `Contract.owner` is undocumented and unused.** `models.py:54`. Read nowhere.
**Remove it.**

**F4 — `SchemaStage` / `Contract.stage` is computed but never consumed.** `models.py:27-66`
+ `__all__` export. Nothing reads `.stage`. **Remove it** (cheap to re-add when a consumer
earns it; keeps the parity surface minimal).

**F5 — `engine` is overloaded to carry skip reasons.** `_validate_extracted_values`
(`validate.py:399-401`) sets `engine="skipped_inferred_via_model"` / `"skipped_no_schema"`
on a skipped structural result, while `engine` nominally names the validation engine
(`"json_schema"`). **Add an explicit `skipped_reason: str | None` to `StructuralResult`**
(mirroring `SemanticResult`) and keep `engine` honest. Lock this before the TS port copies
the result shape.

**F6 — `_resolve_schema_path` walks all of `cwd().parents`.** `validate.py:422-433` searches
`doc_path.parent`, then `cwd`, then **every ancestor of cwd**, so a relative schema path
can silently bind to an unrelated `*.schema.yaml` higher up the tree. **Bound it** to
(doc dir, then cwd) and document the rule so the TS port matches exactly. The one finding
with mild correctness/safety weight.

**F7 — Result-shape `ok` duplication.** `ValidationResult.ok` and
`ArtifactValidationResult.ok` repeat `structural.ok and semantic.ok`. Harmless in Python;
the TS port factors it once.

**F8 (new) — structural error messages leak the `jsonschema` engine.**
`_describe_jsonschema_error` (`validate.py:493-500`) surfaces `err.message` (the
`jsonschema` library's wording) and `err.validator`/`err.validator_value`. `ajv` produces
different wording for the same violation, so the two CLIs could never emit identical
structural errors. **Decision: synthesize an engine-neutral canonical message** from the
normalized fields `(path, validator, validator_value, value)` instead of passing through
the engine's text. Define the structural error record as
`{ kind, path, message, validator, validator_value, value }` where `message` is generated
by softschema (same template both languages). This makes structural errors byte-equal
cross-language. (See Canonical Error Records.)

### Non-issues (validated, no action)

- Two-layer structural/semantic separation with independent reporting: matches spec, keep.
- `status` is informational and does not gate validation: matches spec, keep.
- Deterministic JSON output (`sort_keys=True`, `_plain` normalizer, `cli.py:497-516`): this
  is exactly what makes the CLI golden-testable. Preserve and have TS match it (one change:
  emit non-ASCII literally — see CLI Output Contract).
- `compile.py` SHA-256 over canonical JSON + atomic write + `--check` drift: clean; the TS
  compiler reproduces the same canonicalization so sidecar hashes match.

## Design

### Cross-language parity standard (the bar)

The two implementations must be **equivalent**, not merely similar. Concretely:

- **CLI inputs/flags are equivalent.** Same subcommands (`validate`, `compile`, `inspect`,
  `docs`, `generate`, `skill`) and same flags (`--contract`, `--envelope`, `--model`,
  `--schema`, `--status`, `--check`, `--list`, `--json`, `--brief`). The one idiomatic
  difference: `--model`/`compile`'s *source* is a Pydantic `module:Class` on Python and a
  Zod module export on TypeScript — equivalent role, idiomatic per language.
- **CLI outputs are equivalent**, and for the shared neutral corpus, **byte-identical**.
  Only genuinely incidental, non-semantic formatting may differ; we hold the stronger
  byte-identical bar wherever practical (the corpus enforces it).
- **Library APIs are equivalent.** `validate_artifact`/`validateArtifact`,
  `validate_values`/`validateValues`, `compile_model`/`compileSchema`,
  `Contracts`, `SchemaView`, `SoftField`/`softField`, `parse_schema_metadata`/
  `parseSchemaMetadata`, `regenerate`. Names are idiomatic (snake_case ↔ camelCase);
  shapes, semantics, error `kind`s, and warning codes are identical.
- **The canonical JSON Schema sidecar is exact.** A Pydantic model and the equivalent Zod
  schema compile to a **byte-identical** sidecar with the same `schema_sha256`. This is the
  hardest guarantee and is proven by the comprehensive fixture below.
- **Semantic invariants are impl-specific by design** (Pydantic validators ↔ Zod
  refinements) and tested per-language; only the portable structural subset is exact.

### Pydantic ↔ Zod reconciliation matrix

Raw `model_json_schema()` and `z.toJSONSchema()` differ; `canonicalize_json_schema` (run
by both compilers) normalizes every divergence to one canonical form. Each row is a
reconciliation rule; "status" tracks whether it is implemented and fixture-covered.

| Aspect | Pydantic raw | Zod raw | Canonical rule | Status |
| --- | --- | --- | --- | --- |
| Auto `title` | on every property/$def | none | drop all `title` keywords (never names) | done |
| Optional+nullable | `anyOf:[X,{null}]` + `default:null` | `oneOf:[X,{null}]` | `anyOf:[X,{null}]`, strip implicit `default:null` | done |
| Nullable union form | `anyOf` | `oneOf` | rewrite type-or-null `oneOf`→`anyOf` | done |
| `required` order | field-definition order | field order | sort (set semantics) | done |
| Provenance | `generated_from: module:Class` | n/a | omit `generated_from` (language leak) | done |
| Key order | insertion | insertion | sort keys at serialization | done |
| Named-object reuse | always `$defs/<ClassName>` | `reused:"inline"` extracts only `id`-registered | Zod compiles with `reused:"inline"`; register each nested object with `.meta({id:<ClassName>})` so `$defs` keys match | done |
| Bounded int/number | `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum` | `z.number().min()/.gt()` emits same keywords | identical | done |
| Integer safe-bounds | none | `z.int()` adds `minimum:-9007199254740991`/`maximum:9007199254740991` for unbounded sides | strip the JS safe-integer sentinel bounds | done |
| `multipleOf` | `multipleOf` | `z.number().multipleOf()` | identical | done |
| String constraints | `minLength`/`maxLength`/`pattern` | `z.string().min()/.max()/.regex()` | identical | done |
| Enum | `enum:[...]` + `type:string` | `z.enum([...])` → `enum` + `type` | identical (authored order preserved) | done |
| Mapping | `dict[str,int]` → `additionalProperties:{type:integer}` | `z.record(z.string(),z.int())` adds `propertyNames:{type:string}` | strip the redundant `propertyNames:{type:string}` | done |
| Empty-collection default | `default_factory` → no `default` emitted | `.default([])`/`.default({})` emit `default:[]`/`{}` | strip empty-collection defaults (`[]`,`{}`) like `null` | done |
| Non-nullable union | `anyOf:[{integer},{string}]` | `z.union([...])` → `anyOf` (same order) | author union members in same order | done |
| Object closure | `extra="forbid"`→`additionalProperties:false` | `z.strictObject()`→`false` | identical | done |
| Per-property `x-softschema` | `SoftField` `json_schema_extra` | `softField()` `.meta()` | identical block + omit-empty rules | done |
| Hash encoding | `json.dumps` (was `ensure_ascii=True`) | `JSON.stringify` (literal UTF-8) | hash literal UTF-8 both sides (`ensure_ascii=False`) | done |

All rows are reconciled and proven by the comprehensive fixture: the Zod `KitchenSink`
compiles to the **byte-identical canonical schema and equal `schema_sha256`** as the
committed Pydantic `parity.schema.yaml` (TS `test/conformance.test.ts`). Any future
feature that proves irreconcilable would be removed from the **portable subset** and
documented as not-cross-language.

### Comprehensive parity fixture

`examples/parity/` is the conformance fixture (not a teaching example). `model.py`
(Pydantic `KitchenSink`) and `packages/typescript/test/fixtures/parity.ts` (the
equivalent Zod schema) must both compile to the **committed** `parity.schema.yaml`. The
fixture exercises the portable matrix above (scalars+constraints, enums, optional/nullable
±default, defaults, nested objects with reuse, mapping, union, full `x-softschema`).
`test_parity.py` (Python) and a TS conformance test each assert no-drift against the
committed reference; a cross-implementation test asserts the two compiled sidecars are
byte-equal with the same `schema_sha256`.

### Cross-language architecture

```text
                 Markdown/YAML artifact  +  CANONICAL JSON Schema sidecar (YAML)
                 ────────────── portability boundary (spec) ──────────────
   Python side                                              TypeScript side
   ───────────                                              ───────────────
   Pydantic model ─model_json_schema()─┐         ┌─z.toJSONSchema()─ Zod schema
                                       ▼          ▼
                          canonicalize_json_schema()  (SAME rules both sides)
                                       │          │
                                       ▼          ▼
                          BYTE-EQUAL sidecar (same schema_sha256)
   validate_artifact() ── jsonschema ──┤          ├── ajv/2020 ── validateArtifact()
   (canonical structural error records, engine-neutral messages, both sides)
   SchemaView / SoftField / generate                SchemaView / softField / generate
   softschema-py  (alias: softschema)               softschema-ts
                         │                                   │
                         └────────► one tryscript corpus ◄───┘
                              tests/golden/ (neutral `softschema`, run twice)
```

### Canonical JSON Schema profile (the correspondence mapping)

Raw `model_json_schema()` and raw `z.toJSONSchema()` differ in several incidental ways.
Rather than force one library to mimic the other's quirks ad hoc, both compilers run a
shared **`canonicalize_json_schema()`** post-pass to a lean canonical profile. The output
is byte-identical across languages, so `schema_sha256` matches and `compile --check` /
generated-section hashes are cross-language stable.

The committed movie sidecar (`examples/movie_page/movie-page.schema.yaml`) is the
reference Pydantic output. The table maps every observed divergence:

| Aspect | Pydantic raw (2.13) | Zod raw (4.4) | Canonical resolution |
| --- | --- | --- | --- |
| Nested object reuse | Always `$defs/<ClassName>` + `$ref`, even when used once (`cast → $ref CastMember`) | `reused:"inline"` default; inlines single-use objects | **Always extract named objects to `$defs/<Name>` + `$ref`.** Zod: register named objects (`z.object(...).meta({id})` / registry) and compile with `reused:"ref"`; or extract in the post-pass. |
| Optional (not nullable) | omitted from `required` | `.optional()` → omitted from `required` (no union) | **Omit from `required`.** Already agree. |
| Nullable union | `anyOf: [X, {type: "null"}]` | `.nullable()` → `oneOf: [X, {type:"null"}]` | **`anyOf: [X, {type:"null"}]`.** Post-pass rewrites Zod's `oneOf`-with-null to `anyOf`. |
| Optional **and** nullable (`X \| None = None`) | `anyOf:[X,{null}]` + `default: null`, not required | `.nullish()` → omit from `required`, `oneOf` null, no default | **`anyOf:[X,{null}]`, omitted from `required`, no auto `default`.** Post-pass strips Pydantic's auto `default: null`; keeps explicit non-null defaults. |
| Enum + null (`Literal[...] \| None`) | `anyOf:[{enum:[...],type:string},{null}]` | `z.enum([...]).nullable()` → `oneOf` | Same nullable rule → `anyOf`. |
| Field titles | auto `title: Field Name` on every property and `$def` | none unless `.meta({title})` | **Drop auto titles.** Post-pass removes `title` keys that softschema did not author explicitly. |
| `additionalProperties` | `extra="forbid"` → `false`; default → absent | `z.strictObject()`/`z.object()` (output mode) → `false`; `z.looseObject()` → absent | **`z.strictObject()` ↔ `extra="forbid"` → `false`.** Compile in output mode. Document: closed objects are the norm for artifacts. |
| Numeric/array constraints | `minimum`/`maximum`/`exclusiveMinimum`/`minItems`/`minLength` | same keywords | Pass through unchanged. |
| Description | model docstring → object `description`; `Field(description=)` → property `description` | `.describe()` / `.meta({description})` → `description` | Pass through unchanged. |
| `x-softschema` per-property | from `SoftField` `json_schema_extra` | from `softField()` `.meta({"x-softschema":...})` (Zod copies all meta keys through) | Pass through unchanged; identical block shape. |
| Root envelope | `$schema`, `$id`, root `x-softschema` added by `compile_model` wrapper | same, added by `compileSchema` wrapper | Identical wrapper logic both sides. |
| Key ordering | YAML dumped `sort_keys=False` (insertion order) | object key order | **Canonical sorts keys** (or fixes a canonical order) before YAML dump so byte-equality is order-independent. |

`canonicalize_json_schema(raw) -> dict` rules (shared spec, implemented in both
languages):

1. Extract every named object schema into `$defs/<Name>`; replace inline occurrences with
   `$ref`.
2. Rewrite any `oneOf`/`anyOf` that is exactly `[X, {type:"null"}]` to `anyOf:[X,{type:"null"}]`.
3. Remove auto-generated `title` keys (keep titles softschema explicitly authored).
4. Strip `default: null` that is purely the implicit optional default; keep explicit
   non-null defaults.
5. Recursively sort object keys (canonical order) for deterministic YAML.
6. Leave constraints, `description`, `enum`, `required`, `additionalProperties`,
   `x-softschema` untouched.

A CI conformance test compiles the movie schema from **both** Pydantic and Zod, runs
`canonicalize_json_schema`, and asserts the two YAML sidecars are byte-identical and share
the same `schema_sha256`. The committed Pydantic sidecar is regenerated under the
canonical rules during Phase 0 (allowed — no backcompat).

### Validation layering (what is portable vs impl-specific)

The clean rule that makes "the same golden tests run on both CLIs" actually achievable:

- **Portable invariants live in the canonical JSON Schema** and are checked by the
  **structural** layer (`jsonschema` / `ajv`). Types, enums, `min/max`, `minItems`,
  `minLength`, `required`, `additionalProperties:false`, nullability — all of these are in
  the sidecar and validate **identically** cross-language. The movie model's invariants
  are entirely of this kind.
- **Non-portable invariants live in Pydantic validators / Zod refinements** and are checked
  by the **semantic** layer. Cross-field rules (e.g. "audience ≤ critics") cannot be
  expressed in JSON Schema. These are impl-specific by design and are tested **per-language**
  (pytest / `bun test`), never in the shared corpus.

Consequence for the corpus: failing scenarios are chosen to fail **structurally** (the
canonical, identical path). Their CLI output asserts the full `structural.errors` block
(byte-equal) and asserts `semantic.ok == false`, while the semantic `errors` array is
patterned out (impl-specific wording). Passing scenarios have both blocks `ok:true` with
empty errors and are fully byte-equal.

### Canonical error records

- **Structural** (engine-neutral, byte-equal both sides):
  `{ kind, path: [...], message, validator, validator_value, value }`. `message` is
  synthesized by softschema from a shared template keyed on `validator` (e.g.
  `"enum"`, `"minimum"`, `"required"`, `"type"`) — **not** taken from `jsonschema`/`ajv`.
  A small `normalize_structural_error()` exists on each side mapping the engine's native
  error object into this record (jsonschema `ValidationError` → record; ajv error object,
  with `instancePath`/`keyword`/`params`, → record). Pin with the corpus.
- **Semantic** (impl-specific): keep the engine's native error list
  (`pydantic.errors()` / Zod `error.issues`) for diagnostics, but the shared corpus does
  not compare it byte-for-byte (patterned out). Per-language unit tests assert the native
  shapes.
- The softschema-level **error `kind` strings** (`parse_error`, `no_frontmatter`,
  `frontmatter_not_mapping`, `yaml_not_mapping`, `contract_unknown`, `envelope_mismatch`,
  `document_softschema_invalid`, `document_contract_mismatch`, `schema_sidecar_missing`)
  and **warning codes** (`document-contract-mismatch`, `document-status-mismatch`) are
  string-level contracts shared verbatim by both languages and pinned by the corpus.

### CLI naming and the dual-CLI golden mechanism

Per the requested design, each implementation ships an explicitly-named binary, with a
neutral alias defaulting to Python:

- **Python** (`pyproject [project.scripts]`): `softschema-py = "softschema.cli:main"` **and**
  `softschema = "softschema.cli:main"` (alias). Existing `softschema` users keep working.
- **TypeScript** (`package.json bin`): `softschema-ts`. The TS package does **not** claim
  the unscoped `softschema` name to avoid global collisions.

The shared tryscript scenarios invoke the **neutral `softschema`** command. The suite is
run **twice**, swapping which implementation `softschema` resolves to:

- **Run A (Python):** plain PATH — `softschema` → `softschema-py`. Works from Phase 0,
  before any TS exists.
- **Run B (TypeScript):** a tiny shim dir prepended to `PATH` (or tryscript's sandbox
  `PATH`) where `softschema` → the built `softschema-ts`. Same scenarios, same expected
  output.

`softschema-py` and `softschema-ts` remain available by explicit name for manual use and
for the cross-implementation conformance/diff test (which runs both at once and compares).
A `tests/golden/run.sh` (or `package.json`/`Makefile` target) parameterizes the two runs:

```bash
SOFTSCHEMA_IMPL=py npx tryscript@latest tests/golden   # Run A
SOFTSCHEMA_IMPL=ts npx tryscript@latest tests/golden   # Run B (after TS build)
```

### CLI output contract (byte-level)

Both CLIs must emit identical bytes for shared scenarios:

- JSON via `json.dumps(value, indent=2, sort_keys=True)` ↔ a TS `stableStringify(value, 2)`
  that sorts keys recursively and uses 2-space indent.
- **One Phase 0 change:** set Python `_json` to `ensure_ascii=False` so non-ASCII is
  emitted literally, matching `JSON.stringify` (which never escapes). Avoids `\uXXXX`
  divergence.
- The `_plain` normalizer (Path→str, Enum→value, model→dict, dataclass→dict) has a direct
  TS analogue; both produce the same field set and ordering.
- Exit codes: `0` ok, `1` validation failure / drift, `2` usage error. Identical mapping.

### TypeScript package shape

`packages/typescript/`, a self-contained **bun** package, later published as
`@softschema/core` with a `softschema-ts` bin.

```text
packages/typescript/
  package.json            # type: module; bin: {"softschema-ts":"dist/cli.js"}; exports/files publish-ready
  bunfig.toml             # bun config (test, install)
  bunup.config.ts         # library build → dist/ (ESM + .d.ts), CLI bin
  biome.json              # lint + format (extends house config)
  tsconfig.json           # strict; tsc --noEmit for type checking
  src/
    settings.ts           # YAML stringify opts (sorted keys); stableStringify(); canonicalJson()
    models.ts             # Contract, SchemaStatus, SchemaProfile, SchemaMetadata, WarningCode, SchemaWarning, parseSchemaMetadata
    registry.ts           # Contracts (register/resolve/all, dup-id error)
    canonicalize.ts       # canonicalizeJsonSchema(): drop titles, strip null default, oneOf→anyOf
    compile.ts            # compileSchema(zod, out, {contractId, checkOnly}) -> sidecar + sha256 + --check
    errors.ts             # structuralErrorRecord + renderStructuralMessage + normalizeAjvError; templates
    validate.ts           # validateValues, validateArtifact; result types; ajv/2020 structural + safeParse semantic
    schemaView.ts         # SchemaView, FieldInfo (reader over canonical sidecar)
    softField.ts          # softField(); SoftFieldMeta; SoftOwner/SoftTier/RepairKind
    generate.ts           # parseSections, regenerate (enum_table, field_list, vocab)
    cli.ts                # commander program: validate, compile, inspect, generate, docs, skill
  src/*.test.ts           # bun test unit tests (co-located), incl. semantic-only refinements
  test/fixtures/
    moviePage.ts          # the movie model in Zod — cross-language fixture
  README.md               # replaces the stub
```

`package.json` scripts mirror the Python `Makefile` targets so the two packages feel the
same: `build` (`bunup`), `test` (`bun test`), `test:cov` (`bun test --coverage`),
`lint`/`format` (`biome`), `typecheck` (`tsc --noEmit`), `check` (lint + typecheck + test).

### Testing the TypeScript package (guideline conformance)

Three layers, per `general-testing-rules`, `typescript-code-coverage`, and
`golden-testing-guidelines`:

- **Shared golden corpus (primary parity gate).** The same `tests/golden/` scenarios run
  against `softschema-ts` via `SOFTSCHEMA_IMPL=ts`. This is the cross-language behavioral
  contract and the highest-value coverage; it is language-agnostic (tryscript), so no
  per-language duplication.
- **`bun test` unit tests (co-located `*.test.ts`).** Per-module edge cases that the corpus
  should *supplement*, not duplicate: canonicalize transforms, `stableStringify`/`canonicalJson`
  byte-equality against Python fixtures, `SchemaView` `$ref`/`anyOf`-null walking, ajv error
  normalization, and at least one **semantic-only** cross-field `.refine()` (impl-specific
  by design). Coverage via `bun test --coverage` (lcov), holding the
  `typescript-code-coverage` thresholds (statements ≥ 80, **branches ≥ 75**, functions ≥ 80,
  lines ≥ 80; floors 70/65/70/70), excluding `dist/`, `*.d.ts`, `*.test.ts`, and fixtures.
- **Cross-implementation conformance.** Compile the movie schema via both binaries and
  assert byte-equal canonical sidecar + equal `schema_sha256`.

### Idiomatic Zod choices (not transliteration)

- **Source schema = Zod object.** Pydantic `BaseModel` + `extra="forbid"` ↔
  `z.strictObject({...})` (or `z.object().strict()`). Named nested objects are registered
  with an `id` so the canonical `$defs` extraction is natural.
- **Validation = `safeParse`** (never throw on validation failure; throw only on programmer
  error, per error-handling rules).
- **Annotations via `.meta()`.** Zod 4 copies **all** metadata keys into the JSON Schema
  output (confirmed: arbitrary keys pass through), so `softField()` attaches
  `.meta({ "x-softschema": {...} })` and the compiler emits the same per-property block as
  Pydantic's `json_schema_extra`. Same omit-empty-defaults rules.
- **JSON Schema export** via `z.toJSONSchema(schema, { target: "draft-2020-12", io: "input",
  reused: "ref", unrepresentable: "throw" })`, then `canonicalize_json_schema()`, then the
  `$schema`/`$id`/`x-softschema` wrapper + SHA-256 over the same canonical JSON the Python
  side uses (`stableStringify` matching `json.dumps(sort_keys=True, separators=(",",":"))`).
  `io:"input"` matches Pydantic's default validation-mode schema for `.default()` fields.
- **YAML I/O** via `yaml@2` with centralized `settings.ts` options (sorted keys, no forced
  quoting).
- **Result types** are documented readonly interfaces (doc on the type, per house rules),
  factoring `ok = structural.ok && semantic.ok` once (addresses F7).

### Parity mapping (Python ↔ TypeScript)

| Concept | Python (after Phase 0) | TypeScript | Parity contract |
| --- | --- | --- | --- |
| Source schema | Pydantic `BaseModel`, `extra="forbid"` | `z.strictObject()` | Canonical sidecar |
| Contract record | `Contract` | `Contract` interface | Same fields: `id`, `model`/`schema`, `envelope_key`, `status`, `profile`, `schema_path` |
| Registry | `Contracts` | `Contracts` | `register`/`resolve`/`all`; dup-id error |
| Status / Profile | `SchemaStatus` / `SchemaProfile` StrEnum | string unions | `soft`/`permissive`/`enforced`; `frontmatter-md`/`pure-yaml` |
| Metadata parse | `parse_schema_metadata` | `parseSchemaMetadata` | Same accepted shapes + errors |
| Compile | `compile_model` + `canonicalize` | `compileSchema` + `canonicalize` | **Byte-equal sidecar, equal `schema_sha256`** |
| Canonicalize | `canonicalize_json_schema` | `canonicalize_json_schema` | Identical rules 1–6 |
| Artifact validate | `validate_artifact` | `validateArtifact` | Same result JSON, same error `kind`s |
| Values validate | `validate_values` | `validateValues` | Same result shape |
| Structural | `jsonschema` Draft2020 + `normalize_structural_error` | `ajv/2020` + `normalizeStructuralError` | **Byte-equal structural error records** |
| Semantic | `model_validate` | `safeParse` | Same pass/fail; native errors impl-specific (not corpus-compared) |
| Schema reader | `SchemaView`/`FieldInfo` | `SchemaView`/`FieldInfo` | Same `iter_fields`/`enum_values`/`softmeta`/group-owner-tier filters |
| Field annotations | `SoftField()` | `softField()` | Same emitted `x-softschema` block |
| Generated sections | `regenerate()` 3 kinds | `regenerate()` 3 kinds | **Byte-equal** rendered markers |
| Warning codes / error kinds | `WarningCode` / kind strings | same string unions | Pinned by corpus |
| CLI binary | `softschema-py` (+ `softschema` alias) | `softschema-ts` | Neutral `softschema` in corpus; **byte-equal stdout** |

### Shared golden-test corpus (the parity engine)

Following the golden-testing guideline's console-output-capture strategy with tryscript.
**Golden-first:** the corpus is authored and committed against `softschema-py` in Phase 0,
becoming the executable spec the TS CLI must satisfy unchanged.

- **One corpus, two runs.** `tests/golden/` holds tryscript `.md` scenarios that invoke the
  neutral `softschema`. Run A resolves it to `softschema-py`; Run B (post-TS-build) to
  `softschema-ts`. Both satisfy the same expected-output blocks.
- **Why one block validates both:** the CLI emits deterministic, key-sorted JSON; structural
  errors are engine-neutral; the sidecar is canonical. So identical inputs ⇒ identical bytes.
- **Stable vs unstable:** the only unstable values are absolute paths and `schema_sha256`.
  Pattern **only** those via tryscript frontmatter patterns (`SHA256: '[0-9a-f]{64}'`,
  `TMPPATH: '...'`). Show everything else literally — contract IDs, statuses, error kinds,
  enum tables, etc. (per the guideline's anti-patterns). Semantic `errors` arrays in
  failing scenarios are patterned (impl-specific).
- **Neutral inputs only in the shared set.** The CLI's language-neutral surface is
  `validate --schema`, `inspect`, `docs`, `skill`, `generate`. The semantic layer
  (`--model`: Pydantic vs Zod) and `compile` (source is a Pydantic class vs a Zod module)
  are language-specific *invocations* and live in `scenarios-py/` / `scenarios-ts/`
  (identical expected output, different command). `run.sh` runs `scenarios/` +
  `scenarios-$IMPL/`. Output strings are neutralized (e.g. `skipped_reason:
  no_semantic_model`, not `no_pydantic_model`).
- **Shared `scenarios/` (run on both):**
  1. `validate.md` — schema-only validate of the movie example (structural ok, semantic
     skipped `no_semantic_model`); plus a structural failure with full canonical,
     engine-neutral, sorted `structural.errors` (exit 1).
  2. `inspect-and-docs.md` — `inspect`; `docs --list`; `skill --brief`.
  3. `envelope-errors.md` — ambiguous multi-key envelope (needs `--envelope`); missing
     validation implementation (exit 2, stderr).
  4. (Phase 2) `generate.md` — render `enum_table`/`field_list`/`vocab`; `--check` drift.
- **Per-impl `scenarios-{py,ts}/`:** `compile.md` — `compile --check` no-drift (literal
  `schema_sha256`) and drift; Python source is `module:Class`, TS source is a Zod module;
  identical output otherwise.
- **Cross-implementation conformance test** (separate from tryscript, runs both binaries at
  once): compile the movie schema via `softschema-py` and `softschema-ts`, assert
  byte-equal canonical sidecars and equal `schema_sha256`.

~6 hermetic scenarios + 1 conformance test cover the whole CLI surface for both languages,
with two patterns handling all nondeterminism. No mocks needed (no network/clock/RNG).

### CI integration

- Phase 0: add a `golden` job running `SOFTSCHEMA_IMPL=py npx tryscript@latest tests/golden`
  on the existing Python matrix. Locks behavior before the port.
- Phases 1–2: add a job that sets up the TS toolchain (`oven-sh/setup-bun@v2`,
  `actions/checkout@v6`), runs `bun install`, `biome ci`, `tsc --noEmit`, `bun test
  --coverage`, builds with `bunup`, then runs `SOFTSCHEMA_IMPL=ts bash tests/golden/run.sh`
  + the conformance test. Green on both = parity.
- Keep `pytest` and add `bun test` for per-language edge cases (including semantic-only
  refinements), which golden tests supplement rather than replace.

### Docs embedding equivalence

Both CLIs must **embed** the same documentation set the same way — the Python wheel
already force-includes the guide/spec/design/examples/skill as bundled resources
(`softschema docs <topic>` reads them via `importlib.resources`). The TypeScript package
must do the equivalent: bundle the doc/skill text into `@softschema/core` (at `bunup`
build) so `docs <topic>`, `docs <topic> --json`, and `skill --install`/`--brief` work
when the package is installed standalone from npm — not only inside this monorepo where
the repo files happen to be on disk. Resolution order mirrors Python: bundled resource
first, repo file as a dev fallback. Equivalence is **tested**, not assumed: `docs --list
--json` is already in the golden corpus; `docs <topic>` content is added there too
(byte-identical py↔ts), plus a standalone smoke test that runs `softschema-ts` with only
the bundled resources. The doc **topic set** is identical across CLIs (every doc is a
registered topic in both), including `typescript-design` and the parity-process doc.

### Parity development process (keep the two in sync)

A short, enforced loop documented in `docs/development.md` (and referenced from
`AGENTS.md`/`SKILL.md`) so the two implementations never drift:

1. **Golden first** — for any behavior change, write or update the shared `tests/golden/`
   scenario (or per-impl scenario) before touching code.
2. **Implement in Python**, run `pytest` + `SOFTSCHEMA_IMPL=py` golden.
3. **Port to TypeScript**, run `bun test` + `SOFTSCHEMA_IMPL=ts` golden.
4. **Both green + conformance** — the cross-impl conformance test (KitchenSink sha) and
   both golden runs pass in CI.

The parity invariants and where each is enforced: the **canonical schema** (equal
`schema_sha256`, conformance test), **engine-neutral structural errors** (shared message
templates, golden), **byte-identical neutral CLI output** (golden corpus), and **equal
flag/command surface** (per-impl + neutral scenarios). Skill/agent install follows
`cli-agent-skill-patterns`: a thin dual-runner `SKILL.md` (uvx + npx), copied to
`.agents/` and `.claude/` mirrors, with a **drift test** (commit-and-dogfood) so the
committed mirrors can never go stale.

## Implementation Plan

### Phase 0: Python cleanup + canonical profile + Python-side golden corpus

One PR. Cleans the parity target and locks observable behavior.

- [ ] **F1 — remove gzip:** delete `import gzip`, the `.gz` branches in
  `_read_frontmatter_doc`/`_read_yaml`, and `_temporary_text_artifact` (`validate.py`).
- [ ] **F2 — collapse to two public entries:** remove `validate`, `ValueResolver`,
  `HostAdapter` from `validate.py` and `__init__.__all__`; inline single-key/`envelope_key`
  resolution into `validate_artifact` (replace `_resolver_for_binding`/`resolver.resolve`).
  Keep `validate_values` + `validate_artifact`. Rewrite the three resolver tests in
  `test_core.py` to the contract path.
- [ ] **F3 — remove `Contract.owner`** (`models.py`).
- [ ] **F4 — remove `SchemaStage` + `Contract.stage`** (`models.py`, `__init__.__all__`).
- [ ] **F5 — add `StructuralResult.skipped_reason`**; stop overloading `engine`
  (`validate.py`); update result-shape docs and tests.
- [ ] **F6 — bound `_resolve_schema_path`** to (doc dir, cwd); document the rule.
- [ ] **F8 — engine-neutral structural errors:** add `errors.py` (or extend `validate.py`)
  with `normalize_structural_error()` + a `message` template keyed on `validator`; replace
  `_describe_jsonschema_error` pass-through. Lock the record shape
  `{kind, path, message, validator, validator_value, value}`.
- [ ] **Canonical profile:** add `softschema/canonicalize.py` implementing rules 1–6; call it
  from `compile_model` before YAML dump + SHA-256. Regenerate the movie sidecar under the
  canonical rules; update `compile --check` and `schema_view`/`generate` tests to the new
  bytes. Verify `SchemaView` still reads it (it already handles `$ref`/`anyOf`-null).
- [ ] **CLI output:** set `_json` to `ensure_ascii=False`; add `softschema-py` console script
  and keep `softschema` as alias (`pyproject [project.scripts]`).
- [ ] **F9 — atomic generated-section writes (guideline alignment):** `generate.regenerate`
  currently does `path.write_text` (`generate.py:131`); make it atomic (temp-file +
  `os.replace`, as `compile._write_atomic` already does) so a crash can't truncate a doc.
  Matches `python-modern-guidelines` "Atomic Output Files" and the TS `atomically` plan.
- [ ] **Python-CLI alignment check (no code expected):** confirm against
  `python-cli-patterns` that exit codes are `0`/`1`/`2`, data goes to stdout and errors to
  stderr, and the version comes from `importlib.metadata` (`uv-dynamic-versioning`). These
  already hold; record the audit in the design doc so the TS CLI mirrors them.
- [ ] **Golden corpus (Python):** create `tests/golden/` with scenarios 1–6 (tryscript),
  `tests/golden/README.md` (workflow), and the run parameterization
  (`SOFTSCHEMA_IMPL=py|ts`). Author/commit expected output against `softschema-py`. Wire the
  `golden` CI job.
- [ ] Re-run `devtools/lint.py --check`, `pytest`, `uv build`; update
  `softschema-python-design.md` (two entry points, canonical sidecar, error records) and the
  public-readiness roadmap wording (gzip really gone).

### Phase 1: TypeScript skeleton + canonical compile + validate core

Smallest vertical slice that passes scenarios 1, 2, 4 under `SOFTSCHEMA_IMPL=ts`.

- [ ] **Scaffold** `packages/typescript` on the bun stack: `package.json`
  (`type: module`, `bin: {"softschema-ts":"dist/cli.js"}`, publish-ready `exports`/`files`,
  scripts build/test/test:cov/lint/format/typecheck/check), `bunfig.toml`, `bunup.config.ts`,
  `biome.json`, strict `tsconfig.json`. Pin under the 14-day cool-off: `zod@^4.4`,
  `yaml@^2.8`, `commander@^15`, `ajv@^8`, `ajv-formats@^3`, `picocolors@^1.1.1`,
  `atomically@^2.1.1`; dev: `bunup@^0.16`, `biome@^2.4`, `typescript@^6.0.3`,
  `bun-types@^1.3`, `publint@^0.3.20`. Replace the stub README.
- [ ] **`settings.ts`:** YAML stringify options (sorted keys, no forced quoting);
  `stableStringify(value, indent)` matching Python `json.dumps(sort_keys=True)`;
  `canonicalJson(value)` matching `separators=(",",":")` for SHA-256.
- [ ] **`models.ts` + `registry.ts`:** `Contract`, `SchemaStatus`/`SchemaProfile` unions,
  `SchemaMetadata`, `parseSchemaMetadata` (string|mapping, same errors), `WarningCode`,
  `SchemaWarning`, `Contracts` (dup-id error parity).
- [ ] **`canonicalize.ts`:** port rules 1–6; unit-test against fixtures derived from raw Zod
  output.
- [ ] **`compile.ts`:** `compileSchema(zodSchema, outPath, {contractId, checkOnly})` —
  `z.toJSONSchema({target:"draft-2020-12", io:"input", reused:"ref"})` → `canonicalize` →
  wrapper (`$schema`/`$id`/`x-softschema`) → SHA-256 → atomic write / `--check` drift.
- [ ] **`errors.ts` + `validate.ts`:** structural via `Ajv2020` + `ajv-formats` +
  `normalizeStructuralError`; semantic via `safeParse`; `validateValues` + `validateArtifact`
  with the documented result shape and exact `kind` strings.
- [ ] **`cli.ts` (commander):** `validate`, `compile`, `inspect` emitting JSON byte-identical
  to Python; exit-code mapping 0/1/2; `bin: softschema-ts`.
- [ ] **Conformance test:** compile movie schema via both binaries; assert byte-equal sidecar
  + equal `schema_sha256`. Run scenarios 1, 2, 4 with `SOFTSCHEMA_IMPL=ts`; add the TS golden
  CI job.
- [ ] **Phase 1 conformance gate (`ss-o72d`):** `biome ci`, `tsc --noEmit` (strict, clean),
  `bun test --coverage` meets thresholds, no `any`, docstrings on public types — run before
  starting Phase 2.

### Phase 2: TypeScript schema-view, soft-field, generated sections

Full feature parity; passes scenarios 3, 5, 6.

- [ ] **`schemaView.ts` + `FieldInfo`:** port `iterFields` (with `$ref`/`$defs` walking and
  the `anyOf`-null shapes the canonical profile produces), `enumValues`, `softmeta`,
  `fieldsByGroup`/`ByOwner`/`ByTier`. Pin against the committed canonical movie sidecar.
- [ ] **`softField.ts`:** `softField()` via Zod `.meta({"x-softschema":...})`; same
  omit-empty-defaults rules; same emitted block. Build the movie Zod model
  (`test/fixtures/moviePage.ts`) as the cross-language fixture.
- [ ] **`generate.ts`:** `parseSections`/`regenerate` with the three renderers producing
  **byte-equal** marker bodies; same marker grammar and error messages.
- [ ] **`cli.ts`:** add `generate`, `docs`, `skill` subcommands (docs/skill read shared repo
  resources or a bundled copy; match Python topic names and `--list --json`/`--brief`).
- [ ] Pass scenarios 3, 5, 6 under `SOFTSCHEMA_IMPL=ts`.

### Phase 3: Parity hardening + docs

- [ ] Cross-implementation conformance test in CI (Pydantic vs Zod canonical sidecar) green
  on every push.
- [ ] `bun test` unit tests for TS-specific edge cases: Zod-vs-Pydantic raw quirks the
  canonicalizer must absorb, YAML round-tripping, and **semantic-only refinements** (a
  cross-field Zod `.refine()` mirroring a Pydantic validator) proving the impl-specific layer
  works per-language.
- [ ] `packages/typescript/README.md` + `docs/softschema-typescript-design.md` mirroring the
  Python design doc; a "Two reference implementations / canonical sidecar / golden corpus"
  note in the guide/spec.
- [ ] Update `AGENTS.md` / `SKILL.md` to mention the TS implementation and `softschema-ts`.
- [ ] **TypeScript guideline conformance review (`ss-4o98`):** run
  `tbd shortcut review-code-typescript` on the branch diff and confirm the mechanical gates
  against every TS guideline — `typescript-rules` (no `any`, lowerCamelCase, docstrings on
  public types, field docs on type defs), `typescript-yaml-handling-rules` (`yaml@2`,
  centralized sorted-key stringify), `typescript-cli-tool-rules` (Commander 15, picocolors,
  `--color`/`NO_COLOR`/`FORCE_COLOR` precedence), `typescript-code-coverage` (coverage
  thresholds, branch focus on union types), and `bun-monorepo-patterns` (`biome ci`, `bunup`
  build, `publint`, publish-ready `package.json`, 14-day cool-off). Fix findings before merge.

## Testing Strategy

- **Golden corpus (primary, cross-language):** tryscript scenarios in `tests/golden/`, run
  against both CLIs via the neutral `softschema` + `SOFTSCHEMA_IMPL` switch. Few scenarios,
  full output capture, only `schema_sha256` + paths patterned, fully hermetic, <100ms each.
- **Cross-implementation conformance:** compile the movie schema via both binaries; compare
  canonical sidecars byte-for-byte and `schema_sha256`.
- **Unit tests (secondary, per-language):** pytest (extended for Phase 0) + `bun test`
  with `--coverage` (incl. semantic-only refinements that are impl-specific by design).
- **Commands:**
  ```bash
  # Python
  uv run python devtools/lint.py --check && uv run pytest && uv build
  # Golden, Python side (works today)
  SOFTSCHEMA_IMPL=py bash tests/golden/run.sh
  # TypeScript (from Phase 1)
  cd packages/typescript && bun install && biome ci . && tsc --noEmit && bun test --coverage && bunup
  SOFTSCHEMA_IMPL=ts bash tests/golden/run.sh
  ```

## Rollout Plan

1. Land Phase 0 (cleanup + canonical profile + Python golden corpus) as one PR —
   independently valuable even if the TS port slips.
2. Land Phases 1–2 behind the corpus; the TS package is "done" when green on the same
   scenarios as Python and the conformance test passes.
3. Phase 3 docs + hardening.
4. Down-migrate the trading-repo consumer to the new release (API renames from Phase 0:
   `validate()`/`ValueResolver` gone; `StructuralResult.skipped_reason`; new error records;
   regenerated sidecars). Defer npm publish of `@softschema/core` to a follow-up.

## Open Questions

- ~~**TS toolchain — pnpm vs bun.**~~ **Decided: bun + biome** (see Toolchain Alignment).
  Leanest house-approved stack for a focused small CLI/library; does not affect the parity
  design. pnpm remains a documented fallback.
- **TS package name:** `@softschema/core` (assumed) vs unscoped `softschema` on npm. The
  binary is `softschema-ts` regardless; the unscoped global name stays Python's.
- **TS publishing:** tag-triggered OIDC npm publish with `publint` preflight (mirrors the
  Python `publish.yml` + PyPI Trusted Publishing), **no changesets** for a single package.
  Deferred to a follow-up; flagged here so the package.json `exports`/`files`/`bin` are set
  up publish-ready from the start.
- **Frontmatter library:** `gray-matter` vs a thin custom splitter — pick whichever
  round-trips to identical YAML to Python's `frontmatter-format` for the corpus.
- **`default: null` canonicalization (rule 4):** confirm the final rule against real outputs
  — strip only the implicit optional null default, preserve explicit/non-null defaults. The
  conformance test pins the exact bytes.
- **`io` mode:** `"input"` chosen to match Pydantic validation-mode for `.default()` fields;
  revisit if a model uses transforms/coercions where input vs output diverge.

## References

- [Softschema Spec](../../../softschema-spec.md) — the portability boundary the port
  preserves.
- [Softschema Python Design](../../../softschema-python-design.md) — the surface being
  ported; updated in Phase 0.
- [Public Readiness Plan](plan-2026-05-24-softschema-public-readiness.md) — Cross-Language
  Boundary / Future TypeScript/Zod sections; this plan executes that intent.
- [Runtime Design v8](../../research/research-2026-05-24-softschema-runtime-design-v8.md) —
  durable design reference.
- `tbd guidelines golden-testing-guidelines` — tryscript, stable/unstable fields,
  transparent-box testing, anti-patterns. `npx tryscript@latest docs` for syntax.
- `tbd guidelines typescript-rules` / `typescript-yaml-handling-rules` /
  `typescript-cli-tool-rules` / `typescript-code-coverage` — Zod 4, `yaml@2`,
  **Commander 15**, picocolors, coverage thresholds, supply-chain.
- `tbd guidelines python-cli-patterns` / `python-modern-guidelines` — exit codes,
  stdout/stderr split, uv-dynamic-versioning, atomic output files, tag-triggered OIDC
  publish.
- `tbd guidelines bun-monorepo-patterns` / `pnpm-monorepo-patterns` — version table
  (bun 1.3, bunup, biome, `bun test`, publint, tryscript; or Node 24/pnpm/tsdown/vitest),
  supply-chain
  cool-off, single-package OIDC publishing.
- Zod JSON Schema: <https://zod.dev/json-schema> — `z.toJSONSchema` options
  (`target`/`io`/`reused`/`cycles`/`unrepresentable`/`override`), `.meta()` passthrough,
  `oneOf`-for-nullable, `additionalProperties` for strict/loose objects. Zod **4.4.3**.
- Pydantic JSON Schema: <https://docs.pydantic.dev/latest/concepts/json_schema/> — draft
  2020-12 default, `$defs`/`$ref`, `anyOf`-null optionals, auto titles. Pydantic **2.13.4**.
- Ajv 2020-12: <https://ajv.js.org/json-schema.html> — `ajv/dist/2020` entry point,
  `ajv-formats`.
- [Future TypeScript Notes](../../../../packages/typescript/README.md) — current stub.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
