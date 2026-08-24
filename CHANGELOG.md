# Changelog

All notable changes to softschema are documented here.
Both the Python (PyPI) and TypeScript (npm) packages release together under the same
version number.

## Unreleased

`status: enforced` now returns real document verdicts for supported `allOf`,
`if`/`then`/`else`, and `dependentSchemas` object shapes that version 0.6.2 refused
before examining the document.
It also corrects unsafe `anyOf`, `oneOf`, and `$ref` transformations that could change
the authored schema’s result.
At each supported object location, it rejects a present property whose value is not
admitted by any successful applicable schema.
If the validator cannot apply that undeclared-property rule without changing the
schema’s other behavior, it returns an explicit unsupported result.

Support for the previously refused shapes is additive relative to version 0.6.2, but
this release is not wholly backward-compatible: corrected alternative/reference
behavior, model-only enforced calls, supplied-resource handling, and structural
diagnostic records can change as described below.

### Breaking changes and migration

Structural errors now identify both a stable category and, for field-level repairs, the
affected property. Consumers that match engine keywords or assume one aggregate record
per object should migrate:

| Before | After |
| --- | --- |
| Match `validator == "additionalProperties"` | Match `code == "undeclared_property"`; composed sites report `unevaluatedProperties` |
| Match `{kind, code, path}` for a field repair | Match `{kind, code, path, property}` |
| Read one generic missing/extra record | Read one record per affected field, with a property-specific message |
| Treat every `enforcement_unsupported` as composed-schema refusal | Inspect its stable `reason`; only shapes outside the support matrix are refused |
| Use an enforced semantic model without a schema | Bind a compiled structural schema; the result is now `enforced_schema_required` |
| Read a null or omitted structural `skipped_reason` from a model-only values call | Read `skipped_reason: "no_schema"`; the semantic model still runs |

The `code` values are `undeclared_property`, `missing_property`, `invalid_value`, and
`unmapped_keyword`. `validator`, `validator_value`, and `value` remain diagnostic
fields, not the field-repair match surface.

Callers that supply external resources must key each one by an absolute URI without a
fragment. A resource root `$id`, when present, must resolve to that key.
This makes Python and TypeScript resolve the same fully supplied offline resource graph
rather than relying on engine-specific retrieval behavior.

### Fixed

- **Supported composed object schemas now validate under `enforced`**
  ([#41](https://github.com/jlevy/softschema/issues/41)). `allOf`, `anyOf`, `oneOf`,
  `if`/`then`/`else`, `dependentSchemas`, and supported `$ref` branches remain unchanged
  internally; their parent receives annotation-aware `unevaluatedProperties: false`.
  This preserves alternative branch selection and successful-branch annotations.
  Direct lexical objects continue to use `additionalProperties: false`. Reusable
  definitions and resources remain open while each supported structured reference site
  receives its own undeclared-property rule.
  The offline graph supports local pointers, escaped tokens, anchors, nested
  definitions, embedded `$id` resources, supplied resources, and literal or
  pattern-based declarations.
  Structured `items` and disjoint `prefixItems`/`items` receive the rule independently,
  while `contains` remains an unchanged matcher.
  Sibling child evaluators and context-sensitive composition references are refused when
  inserting undeclared-property rejection could change intersection, branch-selection,
  or conditional-success semantics.
- **Enforced status no longer succeeds without structural enforcement.** Artifact
  validation and the Python/TypeScript values APIs reject model-only enforced calls with
  `enforced_schema_required`. Both values APIs accept `status` and offline `resources`.
- **Field-level structural diagnostics identify the repair target.** Missing and
  undeclared-property errors name the field and preserve one record per affected field.
  `unevaluatedProperties` uses the same category and property-specific message as
  `additionalProperties`. Array indexes in `path` are numeric in both runtimes, and
  Python derives missing required fields from validator data rather than English error
  text.
- **In-memory schema graph identity is deterministic.** Reusing one mapping object at
  several schema locations now returns `schema_invalid/shared_subschema` with deep-copy
  guidance instead of allowing traversal order to select which object locations reject
  undeclared properties.
  TypeScript repeats this graph check before returning a validator-cache hit, where
  serialized content alone cannot distinguish shared identities.

### Added

- **Stable `code` and `property` error fields.** `code` groups engine keywords by repair
  category; `property` identifies the field for missing and undeclared-property records.
- **An explicit `status: enforced` support matrix.** Dynamic references, unsafe nested
  instance composition, conditionals whose matcher annotations escape the unconditional
  declaration scope, directly applied structured embedded resources, and references to
  directly applied non-reusable targets return `enforcement_unsupported` with stable
  `reason`, `schema_path`, and `message` fields.
  Malformed graphs remain `schema_invalid`.
- **Semantic parity vectors.** Shared raw-versus-enforced vectors cover alternatives,
  references, resources, patterns, conditionals, unsupported boundaries, and field-error
  multiplicity in Python and TypeScript.
- **Documented native-engine deviations.** The `engine_deviations` vectors pin the few
  accepted `jsonschema`/Ajv record-set differences exactly.
  Validation verdicts for the supported matrix remain equal.

### Compatibility

Compiled schemas and `schema_sha256` are unchanged because the checked overlay remains
validation-time only.
Explicit `additionalProperties` or `unevaluatedProperties` at an instance site still
wins, and mappings with no reachable declaration remain open.

Documents previously refused solely because they used supported composition now report
their real valid or invalid outcome.
A schema outside the supported matrix fails before document validation with an
actionable reason rather than receiving a partial overlay.
See the spec’s [support matrix](docs/softschema-spec.md#support-matrix) for the exact
boundary and author workarounds.

## v0.6.2—2026-08-22

Fixes a validation gap that could pass a build while checking nothing: the CLI bound
every artifact to the `frontmatter-md` profile, so a conforming `pure-yaml` artifact —
including the spec’s own example — could not be validated at all.

### Fixed

- **`validate` and `inspect` resolve the artifact profile instead of assuming
  `frontmatter-md`** ([#38](https://github.com/jlevy/softschema/issues/38)). Both CLIs
  read every artifact with the frontmatter reader and built a `Contract` with no
  `profile`, so the pure-yaml branch of `validate_artifact` was unreachable from the
  command line and any pure-YAML file failed with `no_frontmatter`. The library was
  correct throughout; only the binding was wrong.

  The gap was silent rather than loud, which is what made it worth a patch: a project
  could adopt pure-YAML datasets, mark them `status: enforced`, wire
  `softschema validate` into CI, and get a passing build that validated nothing — the
  exact failure `status` exists to prevent.
  An `enforced` pure-yaml artifact that violates its bound schema now fails with exit 1.

  Profile resolution is `--profile` flag > a `*.yaml`/`*.yml` file name > a fenceless
  document whose root mapping carries a `softschema:` block > `frontmatter-md`. The name
  is checked before the fence because a YAML document may open with the `---`
  document-start marker that the frontmatter reader would otherwise scan as a fence.
  Requiring the metadata block for the content case keeps prose that happens to parse as
  YAML on `frontmatter-md`, so a Markdown document without frontmatter reports
  `no_frontmatter` exactly as before.

- **Envelope inference no longer applies to pure-yaml artifacts.** The spec exempts the
  profile from single-key inference and multi-key ambiguity rejection, because a
  pure-yaml artifact’s whole root minus the metadata block is the payload.
  Reaching that branch through the CLI would otherwise have rejected a two-key pure-yaml
  document as ambiguous.

### Features

- **`--profile {frontmatter-md,pure-yaml}` on `validate` and `inspect`** in both
  implementations: the explicit escape hatch for an artifact whose name and content do
  not settle its shape.

- **`inspect` reports the resolved `profile`**, and reads a pure-yaml artifact’s root
  metadata block rather than reporting `metadata: null` for it.
  `has_frontmatter` stays literal — a pure-yaml artifact has none — and `profile` is
  what explains the populated metadata beside it.
  This adds one key to the `inspect` JSON output.

- **`clearValidatorCache` is exported from the TypeScript package**, matching Python’s
  `clear_validator_cache`.

### Performance

- **TypeScript compiled schemas are memoized**, closing the last gap with the Python
  cache shipped in v0.5.0. `validateStructural` constructed a fresh Ajv instance and
  recompiled the schema on every call, so a suite validating many artifacts against one
  schema paid full compilation each time; on a repeated validation of the movie example
  the per-call cost drops from roughly 17ms to 0.03ms.

  Both runtimes now key the cache on the schema’s own content plus the `enforced`
  overlay, so a rewritten schema can never be served a stale entry and two paths holding
  identical schemas share one.
  Validation with `resources` supplied builds fresh in both, rather than risk a wrong
  key.

## v0.6.1—2026-08-14

Documentation only. Both packages are unchanged in behavior, so no code, CLI surface, or
schema output differs from v0.6.0; the release exists to ship the new guidance with the
docs bundled in the wheel and the npm tarball.

Adds a worked example of using soft schemas to record a **research loop** — any process
that repeatedly proposes an idea, measures it, and decides, such as performance work,
prompt tuning against an eval, or a library comparison.
Each iteration is one artifact whose frontmatter carries the values the loop’s own
tooling consumes (hypothesis ID, fingerprints, measured medians with confidence
intervals, a verdict from a fixed set) while the body keeps the reasoning only the
author can write.

### Documentation

- **New guide playbook, “Record a Research Loop”** (`docs/softschema-guide.md`): the
  artifact shape as a complete annotated example, plus the four habits that keep the
  record and its roll-up report in sync — compile the contract from a model and
  `--check` it in CI, record measurements mechanically and ask the operator only for
  judgment, regenerate the ledger from validated artifacts, and let the record be the
  loop’s memory across sessions.
- **New README section, “Example: Recording a Research Loop”**: a short subset of the
  playbook that links to it, keeping the README a summary rather than a second copy.
  It covers why negative results survive as queryable artifacts, why a regenerated
  report cannot drift from the record, and why an agent resuming the loop months later
  can read back what was tried without re-running anything.

## v0.6.0—2026-08-04

Validation accepts an already-parsed document root on both profiles, not just
`frontmatter-md`. A consumer whose artifacts are pure YAML previously had no way to
reuse its own parse: the parameter existed but that profile ignored it and re-read the
file. On a downstream workload publishing 1,274 files, validation drops from 171.1s to
69.2s because each artifact is now parsed once rather than twice.

The parameter is renamed to reflect what it carries on either profile, and both
implementations now publish the readers that produce it.

### Upgrade

1. Rename the argument at every callsite.
   Python `validate_artifact(..., frontmatter=root)` becomes `document=root`; TypeScript
   `validateArtifact(..., { preParsed })` becomes `{ document }`, whose type
   `RawFrontmatter` is renamed `ParsedDocument`. No alias is kept, so a missed callsite
   is a `TypeError` in Python and a compile error in TypeScript rather than a silently
   ignored option.

2. Produce the root with softschema’s own readers, now exported: `read_frontmatter_doc`
   and `read_yaml_doc` in Python, `readFrontmatterDoc` and `readYamlDoc` in TypeScript.
   A supplied root is trusted as already decoded and bypasses the portable YAML rules
   (merge keys, explicit tags, aliases, the 64-collection depth bound) that reading from
   disk enforces. A root decoded by a host YAML library directly may validate in one
   implementation and be rejected by the other reading the same file, which is the
   divergence those rules exist to prevent.

3. Drop any `profile: frontmatter-md` declared on a pure-yaml artifact purely to reach
   the single-read path.
   That workaround traded a correctness hazard for a performance one and is no longer
   needed.

### Breaking

- **The pre-parse parameter is renamed** in both implementations, with no alias: Python
  `validate_artifact(..., frontmatter=)` is now `document=`, and TypeScript
  `validateArtifact(..., { preParsed })` is now `{ document }`. The parameter carries
  the parsed document root for either profile, so a caller holding one no longer has to
  know which profile it is on to avoid a second parse.
- **TypeScript type and reader renames**: the exported `RawFrontmatter` is now
  `ParsedDocument`, and `readFrontmatter` is now `readFrontmatterDoc`, matching the
  Python names.
- Minor rather than patch: these rename public API in both packages, which is what
  `publishing.md` reserves a minor bump for.
  A missed callsite fails loudly (a `TypeError` in Python, a compile error in
  TypeScript) rather than silently ignoring the option, so the break is visible at
  upgrade time rather than at runtime.

### Features

- **Pure-yaml validation honors a pre-parsed root** in both implementations.
  The parameter previously existed but reached only the frontmatter profile; a pure-yaml
  contract ignored it and always re-read the file, so the optimization was unreachable
  for exactly the consumers whose artifacts are pure YAML. TypeScript had the same
  defect and is fixed in the same release.
- **The decoders are exported**: `read_frontmatter_doc` and `read_yaml_doc` in Python,
  `readFrontmatterDoc` and `readYamlDoc` in TypeScript.
  Neither package previously published a way to decode an artifact, so a caller
  producing a `document` root had no supported parser and would reach for a host YAML
  library, silently losing the portable rules.
  `read_yaml_doc` replaces the private `_read_yaml`.
- **The trust boundary is documented** in the spec, both design docs, and the
  `validate_artifact` docstrings: a supplied root is trusted as already decoded and is
  not re-checked against the portable YAML rules.

## v0.5.0—2026-08-04

v0.5.0 removes the parser’s input, scalar, and node size ceilings, so softschema no
longer refuses a large artifact after its caller has already written it.
The nesting depth rule stays, reclassified as a portability rule rather than a resource
guard. Compiled schemas are also now cached per schema file, which cuts a large
validation run’s wall clock substantially.

### Upgrade

1. Upgrade every softschema implementation the project uses to `0.5.0`, then refresh its
   lockfiles. Projects that use both implementations must update them together.
   TypeScript lockfiles should resolve `fast-uri>=3.1.5` through Ajv; versions before
   3.1.5 have high-severity URI host-confusion advisories.

2. Remove any handling of the `artifact_too_large` error kind.
   It no longer exists, and no validation result can return it.
   Code that branched on it is now dead; code that treated it as “the artifact was
   rejected” needs no replacement, because such artifacts now validate normally.

3. Re-check any workflow that depended on softschema rejecting large artifacts.
   Inputs over 1 MiB, scalars over 256 KiB, and documents over 100,000 nodes were
   previously rejected with `outcome: input_error` and are now parsed and validated like
   any other artifact. If a pipeline used softschema as its size guard, that guard must
   move to the code that writes or accepts the artifact, where it can reject before the
   work is done rather than after.

4. Leave nesting depth alone.
   The 64-collection depth rule is unchanged and still reports `yaml_limit`. It is now
   documented as a portability rule, in the same category as `MAX_SAFE_INTEGER`: without
   it the two runtimes disagree by an order of magnitude about how deep a document may
   be, because CPython and V8 have very different stack budgets.

5. No artifact rewrite is required, and no compiled schema needs regenerating.
   Every artifact valid under v0.4.0 remains valid under v0.5.0.

### Breaking

- **`artifact_too_large` is removed** from the error taxonomy in both implementations,
  along with the internal `input_too_large` mapping and the shared `too_large`
  conformance vector. An artifact that v0.4.0 rejected with
  `outcome: input_error, kind: artifact_too_large` now returns a normal `valid` or
  `invalid` result. This widens the accepted artifact set; it never narrows it, so no
  previously valid artifact is affected.

### Features

- **Parser resource ceilings removed**: `MAX_INPUT_BYTES` (1 MiB), `MAX_SCALAR_BYTES`
  (256 KiB), and `MAX_NODES` (100,000) are gone from both implementations.
  They only answered whether a hostile document could exhaust the parser, and softschema
  reads artifacts its own callers just wrote.
  A cap that can only fire after the artifact is written destroys completed work rather
  than rejecting bad input, and none of the three was overridable by a parameter,
  profile, or environment setting.
- **Compiled validators are cached** (Python): `validate_structural` no longer reparses
  and recompiles the JSON Schema validator on every call.
  The cache is keyed on the schema text itself, so a regenerated schema can never be
  served from a stale entry and two paths holding identical bytes share one entry.
  Validation that passes `resources` is left uncached, and compile failures are not
  cached. Measured on a downstream suite: 361s to 262s, a 28% reduction.
- **`clear_validator_cache()`** (Python) is exported for long-lived processes that
  regenerate compiled schemas in place, such as a watch mode or a language server.
  Ordinary callers never need it, because a rewritten schema misses the cache on its
  own. The TypeScript implementation has no corresponding export because it does not yet
  cache compilation.

### Fixes and hardening

- **Python maps `RecursionError` to `yaml_limit`**, mirroring the TypeScript
  `RangeError` path. The depth preflight makes this unreachable for ordinary callers, but
  a caller already deep in its own stack can exhaust the budget at a legal depth, and
  that must stay a structured result rather than an exception escaping
  `validate_artifact`.
- **Depth rule documented as a portability rule**: `MAX_DEPTH` (64) is unchanged in
  value and behavior, but the spec and both implementations now explain that it bounds
  what survives a round trip through a host parser, alongside `MAX_SAFE_INTEGER`, which
  bounds what survives a round trip through a JS number.

### Dependencies

- **Patched TypeScript URI resolver**: The checked-in TypeScript dependency graph now
  constrains Ajv’s `fast-uri` dependency to reviewed version 3.1.5, removing a further
  high-severity host-confusion advisory that also covers the previously pinned 3.1.4.
  The exact pin carries the same one-package release-age exception as the 3.1.4 pin it
  replaces, because the patched release is the only way to clear the advisory and no 3.x
  version outside the affected range exists.
  Refresh and verify application lockfiles against the same safe floor; no softschema
  API or artifact change is involved.

## v0.4.0—2026-07-31

v0.4.0 makes YAML date- and timestamp-shaped scalars portable strings in both
implementations. It also aligns canonical schemas compiled from corresponding Pydantic
and Zod temporal fields.

### Upgrade

1. Upgrade every softschema implementation the project uses to `0.4.0`, then refresh its
   lockfiles. Projects that use both implementations must update them together.
   Python lockfiles should resolve `frontmatter-format>=0.4.0`; that first-party release
   is an intentional exception to the normal dependency cool-off.
   TypeScript lockfiles should resolve `fast-uri>=3.1.4` through Ajv; versions before
   3.1.4 have high-severity URI host-confusion advisories.

2. Validate the project’s full artifact corpus.
   No artifact rewrite is required: quoted and unquoted date-shaped YAML values remain
   strings, and bare dates that v0.3.0 rejected are now accepted.

3. Regenerate committed compiled schemas from Zod models that use ISO date, datetime,
   time, or duration helpers.
   Their digest may change once because compiler-intrinsic patterns are removed.
   Review and commit that generated diff.

4. If a workflow relied on a Zod-generated temporal pattern for structural rejection,
   add an explicit portable JSON Schema `pattern`. The default JSON Schema `format`
   vocabulary remains annotation-only in softschema.

5. Test the bound Pydantic and Zod semantic validators with the application’s accepted
   and rejected temporal values.
   Canonical schema parity does not promise identical semantic accept sets across the
   two model libraries.

6. Treat validation-result values as strings.
   Host code that needs `date`, `datetime`, or JavaScript `Date` objects must construct
   them explicitly after validation.

7. If the bundled project skill is installed, refresh its managed mirrors:

   ```bash
   softschema skill --install --scope project --agent portable --agent claude
   ```

The
[Dates and Timestamps Are Strings](docs/softschema-guide.md#dates-and-timestamps-are-strings)
guide section gives the complete authoring and migration rationale.

### Features

- **Portable YAML timestamp strings**: Bare dates and timestamps now decode to their
  string content in both implementations instead of being rejected.
  Existing quoted values remain unchanged, and no artifact rewrite is required when
  upgrading. Validation results retain strings; date validity remains the responsibility
  of a semantic model or explicit structural assertion.
- **Canonical temporal-schema parity**: Corresponding Pydantic temporal fields and Zod
  ISO date, datetime, time, and duration strings now compile to the same format-only
  schema and digest. JSON Schema `format` remains annotation-only; explicitly authored
  patterns remain structural assertions.
  Model-specific coercions and Zod ISO options remain semantic constraints outside the
  structural digest.

### Dependencies

- **`frontmatter-format` v0.4.0**: The Python package adopts the deterministic,
  alias-free writer used for compiled-schema YAML. Its general-purpose readers retain
  YAML-native timestamp behavior; softschema does not use them for artifacts and
  continues to own the stricter portable-string parsing boundary.
  The dependency upgrade therefore requires no artifact rewrite and does not cause the
  timestamp behavior change described above.
- **Patched TypeScript URI resolver**: The checked-in TypeScript dependency graph
  constrains Ajv’s `fast-uri` dependency to reviewed version 3.1.4, removing two
  high-severity host-confusion advisories.
  The exact pin is a maintainer-approved exception to the normal dependency cool-off.
  Refresh and verify application lockfiles against the same safe floor; no softschema
  API or artifact change is involved.

### Guidelines and Content

- **Agent timestamp guidance**: The bundled skill now tells agents that date-shaped YAML
  values are portable strings and that calendar validation belongs in the bound contract
  or model.

### Documentation

- **Date migration guidance**: The guide, spec, and language design references now
  distinguish portable string decoding from Pydantic, Zod, and JSON Schema date
  validation, including the annotation-only format policy.

**Full commit history**:
[v0.3.0 … v0.4.0](https://github.com/jlevy/softschema/compare/v0.3.0...v0.4.0)

## v0.3.0—2026-07-12

### Features

- **Paired portable-value boundary**: Python and TypeScript now share bounded UTF-8 and
  YAML input rules, safe-number limits, canonical schema digests, and structurally
  comparable validation results.
- **Contract and schema identity**: Compilers require a logical contract ID, keep an
  optional JSON Schema resource ID separate, and produce matching canonical compiled
  schemas and `schema_sha256` values.
- **Explicit skill installation**: `softschema skill --install` now requires a scope and
  agent target, supports dry-run previews, and protects unmanaged files.

### Fixes

- **Portable validation parity**: Aligned frontmatter delimiters, YAML structure limits,
  schema and pattern failures, strict-extra handling, error records, and compiler drift
  checks across both runtimes.
- **Bounded document resources**: Document-declared schemas and installed package
  resources now resolve within their intended trust boundaries.

### Guidelines and Content

- **Installed agent resources**: The source skill and generated portable Agent Skills
  and Claude mirrors now use one managed, drift-checked installation flow.

### Documentation

- **Hardening documentation**: Updated the guide, spec, language design references, and
  development workflow to describe the paired runtime and release boundary accurately.

**Full commit history**:
[v0.2.2 … v0.3.0](https://github.com/jlevy/softschema/compare/v0.2.2...v0.3.0)

## v0.2.2—2026-06-15

### Features

- **`softschema prime` command**: Prints the full agent context (the skill operating
  rules plus the bundled docs index), so an agent can restore context without the source
  checkout. Byte-identical across the Python and TypeScript CLIs.

### Fixes

- **CLI error boundary no longer masks internal bugs**: The user-error boundary now
  excludes bug-indicator exception types (Python `TypeError`/`KeyError`; JavaScript
  `TypeError`/`RangeError`/`ReferenceError`), so a programmer bug surfaces as a
  traceback instead of a clean exit 2. In the TypeScript CLI every per-command handler
  routes through one shared boundary (`reportUserError`), so a bug thrown deep inside a
  command — not just one that reaches the top-level guard — crashes rather than being
  reported as exit 2. Adds an explicit `UsageError` class and documents the 0/1/2
  exit-code contract.
- **Supply-chain cool-off config**: The `[tool.uv]` cutoff used a date-only string that
  uv could not parse; it now uses RFC3339 timestamps with a pinned global cutoff, so the
  exception applies to local resolution and the lockfile stays stable.
- **Canonical number rendering (`ss-wbnm`)**: A whole-valued number now renders in
  canonical form — no trailing fraction and no exponent below 1e21 (`2.0` becomes `2`,
  `1.0e16` becomes `10000000000000000`) — in error records, synthesized messages, and
  the echoed `values` block.
  JavaScript emits this form natively; the Python side converts its whole-valued floats
  to match, so validation output is byte-identical for every number an implementation
  represents exactly (the IEEE-754 safe-integer range).
  A non-round integer-valued magnitude at or beyond 2^53 stays runtime-specific and is
  out of scope.

### Refactoring

- **Shared mapping guard**: Consolidated four near-duplicate object guards into one
  `isMapping` helper (TypeScript).
- **Preserve original `docs` error**: The `docs` command reports the underlying failure
  rather than a generic message, matching the Python CLI.
- **Removed redundant error handling**: Dropped a redundant inner `try/except` in the
  Python `compile` command.

### Documentation

- **PyPI-focused Python README**: `packages/python/README.md` is now a short PyPI entry
  point instead of a second full README.
- **Added `CHANGELOG.md`** following the release-notes guidelines.

**Full commit history**:
[v0.2.1 … v0.2.2](https://github.com/jlevy/softschema/compare/v0.2.1...v0.2.2)

## v0.2.1—2026-06-15

### Fixes

- **ESM library entrypoint and CLI main check**: Fixed the ESM entrypoint and CLI main
  guard so the library loads correctly in ESM consumers (#16)

### Documentation

- **Documentation-guidelines pass**: Standardized repo docs to follow
  common-doc-guidelines
- **Review cleanups**: Minor cleanups from code review

**Full commit history**:
[v0.2.0 … v0.2.1](https://github.com/jlevy/softschema/compare/v0.2.0...v0.2.1)

## v0.2.0—2026-06-11

### Features

- **Contract-ID grammar enforcement**: Contract IDs now follow an enforced shape
  (`[namespace:]Name[/version]`)
- **`softschema.schema` binding**: Artifacts can declare their compiled schema path in
  the `softschema:` block for self-describing validation
- **Self-describing artifacts**: Artifacts with a `softschema:` block validate with no
  CLI flags

### Refactoring

- **Error-kind renames**: Validation error kinds renamed for clarity and consistency

**Full commit history**:
[v0.1.4 … v0.2.0](https://github.com/jlevy/softschema/compare/v0.1.4...v0.2.0)

## v0.1.4

Maintenance and packaging fixes.

## v0.1.3

Maintenance and packaging fixes.

## v0.1.2

Maintenance and packaging fixes.

## v0.1.1

Maintenance and packaging fixes.

## v0.1.0

Initial release.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
