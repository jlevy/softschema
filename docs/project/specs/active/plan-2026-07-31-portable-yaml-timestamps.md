---
title: Portable YAML Timestamp Strings
description: Normalize implicit YAML timestamps to strings across both runtimes
author: Codex, with maintainer direction from Joshua Levy
---
# Feature: Portable YAML Timestamp Strings

**Date:** 2026-07-31 (last updated 2026-07-31)

**Author:** Codex, with maintainer direction from Joshua Levy

**Status:** Implemented

**Tracking:** GitHub issue [#22](https://github.com/jlevy/softschema/issues/22),
delivery epic `ss-xuw3`; original implementation bead `ss-lri7`

## Overview

Decode implicit YAML date- and timestamp-shaped scalars as strings in both softschema
implementations. Python must prevent ruamel.yaml from constructing `date` or `datetime`
objects without changing ruamel.yaml behavior elsewhere in the process.
TypeScript must stop rejecting values that its YAML parser already decodes as strings.

This change establishes a clean portable boundary: parsed artifact values contain only
JSON-compatible values.
Date validity belongs to a semantic model or an explicit JSON Schema assertion, not the
YAML decoder or a `format` annotation by itself.

## Goals

- Make valid, invalid, quoted, and unquoted date-shaped YAML scalars decode to the same
  string values in Python and TypeScript.
- Preserve the scalar text without date construction, timezone normalization, or
  fractional-second rounding.
- Keep explicit tags and the other portable-input restrictions unchanged.
- Avoid process-wide mutation of ruamel.yaml constructor state.
- Keep corresponding Pydantic and Zod temporal fields aligned in canonical compiled
  schemas without activating implementation-dependent JSON Schema format checking.
- Give users and agents an accurate upgrade path that does not require rewriting
  existing artifacts.
- Assign each documentation fact to one authoritative document and keep higher-level
  surfaces concise.

## Non-Goals

- Activating the optional JSON Schema Format-Assertion vocabulary or treating `format`
  as an assertion in softschema’s structural validators.
- Defining one portable semantic date type across Pydantic and Zod.
- Returning host-native `date`, `datetime`, or JavaScript `Date` values from artifact
  parsing.
- Adding a timestamp warning, compatibility mode, status-dependent behavior, migration
  command, or artifact version field.
- Reformatting existing quoted date strings.

The format policy is a resolved part of this design, not follow-up work.
`format` remains annotation-only; an authored `pattern` or another ordinary JSON Schema
keyword remains an assertion.

## Background

The current portable-input rule rejects any plain scalar beginning with `YYYY-MM-DD`
followed by the end of the scalar, `T`, a space, or a tab.
The rule prevents a real parity failure: ruamel.yaml constructs Python `date` and
`datetime` objects, while the TypeScript `yaml` package returns strings.

Rejection is not required to preserve parity.
A scoped Python constructor can retain the scalar text as a string, matching the
TypeScript result and the JSON-compatible portable domain.

The design was reproduced against ruamel.yaml 0.19.1 and `yaml` 2.9.0:

- a constructor registered through a `YAML` instance changes fresh ruamel.yaml instances
  in the same process;
- a `SafeConstructor` subclass receives its own copied constructor registry and does not
  change the base class;
- returning the timestamp node value preserves an offset and nine fractional digits;
- constructing a Python datetime and calling `.isoformat()` changes spelling and can
  round fractional seconds;
- setting ruamel.yaml’s declared YAML version to 1.1 or 1.2 does not disable timestamp
  construction.

The phrase **scalar text** in this plan means the value after ordinary YAML scalar
decoding. It does not promise preservation of source bytes, comments, quoting, or line
endings.

JSON Schema Draft 2020-12 defines `format` as an annotation in its default meta-schema
and makes the Format-Assertion vocabulary optional.
The current Python validator constructs `Draft202012Validator` without a
`FormatChecker`, and the TypeScript validator constructs Ajv with
`validateFormats: false`. Those settings are retained deliberately.

Pydantic emits `type: string` plus a format annotation for native `date`, `datetime`,
`time`, and `timedelta` fields.
Zod’s `z.iso.date()`, `z.iso.datetime()`, `z.iso.time()`, and `z.iso.duration()` schemas
emit the corresponding format plus an intrinsic regular expression.
That extra generated expression is a compiler-adapter difference, not an authored
portable contract constraint, and must not make the canonical sidecar
language-dependent.

## Design

### Portable Value Rule

An implicit plain scalar that a host YAML parser recognizes as a timestamp must enter
the portable value domain as its string content.
Quoted and unquoted spellings with the same scalar content therefore produce the same
value. An invalid calendar date such as `2001-13-99` is still a portable string; a
semantic model or explicit structural assertion decides whether it is a valid date.

An explicit tag such as `!!timestamp` remains an explicit YAML tag and is rejected by
the existing `yaml_custom_tag` rule.

### Python Implementation

Define a private module-level subclass of `ruamel.yaml.constructor.SafeConstructor`.
Register a constructor for `tag:yaml.org,2002:timestamp` on that subclass that returns
the scalar node value.
Assign the subclass to each `YAML(typ="safe")` instance before parsing or loading.

Remove the timestamp-shape regular expression and the event-level timestamp rejection.
Keep the constructed-value guard against Python `date` and `datetime` objects as a
defense for non-parser construction paths, but change its message so it does not claim
that timestamp strings are unsupported.

Do not register the constructor through `yaml.constructor`; that mutates the inherited
class registry and affects unrelated ruamel.yaml users in the host process.
Do not normalize a constructed object with `.isoformat()` because construction can
already have lost lexical precision.

### TypeScript Implementation

Remove the plain-scalar timestamp-shape rejection from `parsePortableYaml`. The
configured `yaml` parser already returns the scalar content as a string, so no
replacement parser hook is required.

Reject host-native JavaScript objects inside the internal portable-value checker used
for programmatic metadata.
Arrays, plain objects, and null-prototype objects remain in the portable domain; values
such as `Date`, `Map`, `Set`, `RegExp`, `Error`, `URL`, and class instances do not.
This mirrors Python’s host-native value guard without changing `validateValues`, whose
input is already-extracted host data rather than parsed YAML.

### Structural Format Policy

The canonical softschema profile uses JSON Schema Draft 2020-12’s default
Format-Annotation vocabulary.
`format: date`, `format: date-time`, `format: time`, and `format: duration` describe a
string’s intended meaning but do not make structural validation fail.
Unknown formats have the same annotation-only behavior.
This policy is unconditional: document status, CLI flags, and host runtime do not change
it.

An author who needs schema-only lexical enforcement must use an ordinary portable JSON
Schema assertion such as `pattern`. That assertion is checked by both runtimes under the
existing regular-expression subset.
Calendar-aware validation belongs in the semantic model because the two structural
engines’ optional format libraries do not implement identical date-time edge cases.

The layers therefore behave as follows:

| Input | Portable Decode | Format-Only Schema | Date Semantic Model |
| --- | --- | --- | --- |
| `2026-07-11` | string | valid | valid |
| `2001-13-99` | string | valid | invalid |
| explicit-tag `!!timestamp 2026-07-11` | rejected | not reached | not reached |

The TypeScript compiler removes only the intrinsic JSON Schema `pattern` emitted for
`z.ZodISODate`, `z.ZodISODateTime`, `z.ZodISOTime`, and `z.ZodISODuration` nodes.
Use Zod’s `toJSONSchema` override callback, public schema classes, and public classic
`def.pattern` to identify those nodes before canonicalization.
Do not remove `pattern` based only on the presence of a date format: an explicitly
authored `z.string().regex(...)` constraint must remain structural.

The Python and TypeScript parity fixtures include structurally corresponding date,
datetime, time, and duration fields.
After adapter normalization, both models compile to `type: string` plus `format`, with
no generated pattern, and retain the same `schema_sha256`.

### Semantic Date Models

Pydantic `date`, `datetime`, `time`, and `timedelta` fields may validate the portable
strings and expose native values to host code that explicitly constructs a model.

TypeScript hosts may use `z.iso.date()`, `z.iso.datetime()`, `z.iso.time()`, or
`z.iso.duration()` to validate temporal strings semantically.
These Pydantic and Zod choices are not accept-set equivalents: their accepted spellings
and coercions differ, and Zod datetime options can further narrow or expand the accepted
strings. Projects that require identical cross-runtime semantics must align and test
validators in both models.
The TypeScript compiler normalizes the intrinsic JSON Schema patterns out of the
canonical sidecar, leaving the corresponding format annotation Pydantic emits.
`z.date()` and `z.coerce.date()` produce JavaScript `Date` values and cannot be compiled
by Zod to the package’s canonical JSON Schema; they are not portable contract types.

The canonical sidecar and `schema_sha256` identify structural constraints only.
Model-specific coercions and Zod ISO options that are not emitted as JSON Schema remain
outside that identity, so a semantic accept-set change does not necessarily cause
structural schema drift.

`ArtifactValidationResult.values` remains the decoded portable mapping in both runtimes.
Semantic validation reports success or failure but does not replace those values with a
model instance.

### API and Error Behavior

No public API, CLI flag, result field, or exit class changes.
Timestamp-shaped YAML no longer produces `yaml_unsupported_scalar`. That error code
remains available for unsupported constructed values and lone surrogates.

This is an intentional input-domain expansion for the next minor release.
Every previously valid artifact keeps the same decoded value; previously rejected bare
timestamp-shaped scalars become strings.
Canonical schemas compiled from Zod ISO temporal fields may drift once because their
language-specific generated patterns are removed.

## Documentation Plan

Documentation follows the repository’s common documentation guidelines: orient a
low-context reader, state present behavior, put exact facts in their owning document,
avoid duplicated explanations, use concrete examples, and retain the standard footer.

| Document | Update | Ownership Boundary |
| --- | --- | --- |
| `docs/softschema-spec.md` | Replace timestamp rejection with the normative string-decoding rule. State that implicit date-shaped scalars must not become host-native date objects, invalid date-shaped text remains a string, explicit tags remain rejected, and calendar validity is outside portable decoding. Define `format` as annotation-only and distinguish it from explicit assertions such as `pattern`. Correct the compatibility section so it does not claim that the Python implementation delegates frontmatter parsing to `frontmatter-format`; softschema implements the documented subset and uses its own portable parser. | Exact language-neutral artifact and validator requirements only; no migration or runtime implementation detail. |
| `docs/softschema-guide.md` | Add a concise temporal-string subsection to the artifact-migration playbook. Explain that existing quoted values need no edit, previously rejected bare values work after upgrading, raw result values remain strings, `format` alone does not reject invalid dates, and model validation is required for calendar semantics. State that Pydantic and Zod temporal models are not accept-set equivalents and that hosts requiring identical semantics must align their validators. | User and agent adoption, authoring, and migration guidance. Link to the spec for the exact rule. |
| `docs/softschema-python-design.md` | Add a short portable YAML parsing subsection under Validation. Document the scoped `SafeConstructor` subclass, why process-global registration is forbidden, why native dates remain outside parsed values, and why structural validation does not install a `FormatChecker`. Correct the dependency-boundary text: softschema owns frontmatter extraction and portable YAML parsing; `frontmatter-format` supplies the configured YAML writer used for compiled schemas. | Python implementation mechanism, parser ownership, and process-isolation invariant. Do not repeat the full portable-value list. |
| `docs/softschema-typescript-design.md` | Add `portable` to the module table and a short portable YAML parsing subsection. Document that the `yaml` parser already yields strings, the redundant lexical rejection is absent, Ajv keeps `validateFormats: false`, portable date models use Zod ISO strings rather than `z.date()`, and the compiler adapter removes only the four public Zod ISO schemas’ intrinsic patterns. Explain the plain-object host boundary and that semantic options remain outside the structural digest. | TypeScript implementation and Zod-specific choices. Link to the spec for language-neutral semantics. |
| `skills/softschema/SKILL.md` | Add one operating-brief bullet: date- and datetime-shaped YAML values are portable strings, `format` is annotation-only, and agents should rely on a semantic model or explicit structural assertion for date validity. | Actionable agent guidance only. Do not copy migration or constructor details. |
| `.agents/skills/softschema/SKILL.md` and `.claude/skills/softschema/SKILL.md` | Regenerate both managed mirrors from the source skill and verify byte-for-byte drift tests. | Generated discovery surfaces; never edit independently. |
| `CHANGELOG.md` | Restore the missing v0.3.0 entry from the completed release plan and tag before adding the next minor release entry. The new entry describes the accepted input, unchanged quoted values, portable string result, rewrite-free artifact upgrade, annotation-only format policy, and possible one-time Zod compiled-schema drift. | Versioned behavior and compatibility history. Do not restate implementation internals. |
| This plan | Record evidence, design, test ownership, documentation ownership, and rollout. | Internal implementation plan. It is not bundled as user documentation. |
| `plan-2026-07-11-minimal-softschema-hardening.md` | Add one concise pointer near the overview stating that its timestamp-rejection decision records v0.3 behavior and is superseded for the next minor release by this plan. Preserve its original disposition tables as historical evidence. | Prior release plan and decision history. Do not rewrite it to describe the new design. |

The following documents need no content change:

- `README.md`: it remains a short subset of the guide and should not acquire a low-level
  portable-scalar rule.
- `AGENTS.md`: it already routes agents to the guide, spec, and example.
- `docs/development.md`: it already requires shared-vector-first parity development and
  the full two-runtime validation loop.
- `docs/installation.md` and `docs/publishing.md`: installation and release mechanics do
  not change.
- `packages/python/README.md` and `packages/typescript/README.md`: package entry points
  should link to bundled docs rather than duplicate the rule.
- `examples/movie_page/`: adding an unrelated date field would expand the public example
  and compiled schema without improving ownership or coverage.
- Historical reviews and research documents: retain the behavior they reviewed.
- `tests/vectors/README.md` and `tests/golden/README.md`: their test-ownership guidance
  already covers the new shared vector.

### Documentation Wording Requirements

- Say **decoded scalar text** or **string content**, not “verbatim source bytes.”
- Describe the configured parsers and observed behavior; do not claim that every YAML
  1.2 or JavaScript parser behaves identically.
- Distinguish portable parsing from structural and semantic date validation.
- State directly that `format` is annotation-only in softschema.
  A schema must use `pattern` or another assertion for structural rejection.
- Recommend Zod ISO string schemas for portable temporal models; do not imply that they
  accept exactly the same strings as Pydantic, or that `z.date()` accepts the raw string
  or compiles to JSON Schema.
- Keep compatibility history in the guide’s migration section, the changelog, and the
  two linked plan documents.
  Write the spec and language design docs in present tense.
- Preserve Title Case for H1 and H2 headings and the standard documentation footer.

## Implementation Plan

### Phase 1: Implement and Document the Portable Rule

- [x] Change the shared portable-value vectors first and confirm both runtimes fail for
  the intended reason.
- [x] Add expected values for bare dates, offset datetimes, space-separated datetimes,
  fractional seconds, invalid date-shaped strings, quoted equivalents, and a date-shaped
  mapping key.
- [x] Implement the scoped Python timestamp constructor and remove lexical rejection.
- [x] Remove the TypeScript lexical rejection and align internal host-native `Date`
  handling.
- [x] Add one Python regression for constructor isolation and focused semantic date
  tests in both runtimes.
- [x] Update the spec, guide, language design docs, source skill, changelog, and prior
  plan pointer according to the documentation table.
- [x] Regenerate the managed skill mirrors rather than editing them directly.
- [x] Run documentation lint, mirror drift, bundled-resource tests, both unit suites,
  both golden suites, cross-runtime conformance, builds, and package smoke tests.

### Phase 2: Make the Format Policy and Compiler Parity Explicit

- [x] Add shared structural vectors proving that an invalid calendar string passes a
  format-only schema and fails when an explicit portable `pattern` rejects it.
- [x] Add Pydantic `date`, `datetime`, `time`, and `timedelta` fields plus structurally
  corresponding Zod ISO fields to the compiler parity fixture; confirm the TypeScript
  side initially differs because of its intrinsic patterns.
- [x] Add a TypeScript `toJSONSchema` override that removes the intrinsic pattern only
  from the four public Zod ISO temporal schema classes.
- [x] Add a TypeScript regression proving an authored `z.string().regex(...)` pattern is
  preserved, including when metadata also declares a date format.
- [x] Update every documentation surface in the table with the final annotation-only
  policy and Zod compiler normalization.
- [x] Regenerate managed skill mirrors and the reviewed `skill --brief` golden.
- [x] Re-run the full local validation and package-smoke matrix from Phase 1.

### Phase 3: Harden the Review Boundary

- [x] Reject every non-plain JavaScript object from programmatic portable metadata and
  retain arrays, plain objects, and null-prototype objects.
- [x] Restore generic `format` annotation coverage alongside the temporal vector.
- [x] Prove that Zod ISO datetime semantic options do not alter the structural sidecar
  or digest.
- [x] Remove assertion precedence from both shared-vector harnesses so `expected` and
  `code` can be checked independently.
- [x] Document the structural-digest boundary and the non-equivalent Pydantic and Zod
  semantic accept sets in the spec, guide, language design docs, changelog, and plan.
- [x] Explain Python constructor-registry isolation and use Zod’s public classic-schema
  definition surface in the compiler adapter.
- [x] Re-run documentation lint, both unit suites, three CLI golden suites,
  cross-runtime conformance, builds, package lint, and clean-install smoke tests.

## Testing Strategy

The shared YAML vector is the primary owner of portable timestamp decoding.
Adapter tests cover only runtime-specific integration:

- Python constructor isolation from unrelated ruamel.yaml instances
- Python Pydantic temporal semantic acceptance and rejection
- TypeScript Zod ISO temporal semantic acceptance and rejection
- TypeScript non-plain host-object rejection in portable metadata
- Shared format-only versus explicit-pattern structural behavior
- Cross-language compiled-schema and digest parity for date, datetime, time, and
  duration fields
- Structural-digest stability across Zod ISO datetime semantic options
- Preservation of explicitly authored Zod regex constraints

The implementation does not add a timestamp-specific CLI golden because the shared
vector exercises artifact parsing through both validation adapters.
The reviewed `skill --brief` golden changes because the operating brief is public CLI
presentation.

Documentation validation includes:

- the repository documentation lint and standard-footer check
- codespell and formatting checks
- source-skill and managed-mirror drift tests
- bundled docs and skill resolution tests for both packages
- a claim audit against the spec, guide, language design docs, and changelog
- link review from the obvious entry points named in the documentation table

The full runtime matrix follows `docs/development.md` and includes Python, Node, and Bun
where already required by the repository.

## Rollout Plan

Release the Python and TypeScript packages together under the next shared minor version,
expected to be v0.4.0.

No artifact rewrite is required:

- Quoted date strings remain valid and keep the same values.
- Bare date-shaped values that the prior release rejected become valid after the
  validator upgrade.
- Agents may leave existing quotes in place and author new date-shaped strings either
  quoted or unquoted.
- Projects with installed skill mirrors should rerun the explicit skill installation
  command after upgrading.
- Projects should validate their artifact corpus with the upgraded runtime before any
  optional style-only reformatting.
- Projects that compile Zod ISO temporal schemas should regenerate committed sidecars
  once; only Zod’s intrinsic date, datetime, time, and duration patterns are removed, so
  the resulting sidecars match the Pydantic format-only form.

There is no successful v0.3 timestamp parse whose return type must be migrated: bare
values were rejected, while quoted values already returned strings.
Host code that needs native values should explicitly construct its Pydantic model from
the portable mapping.
TypeScript hosts should likewise parse or transform validated ISO strings outside the
portable artifact result.

## Decision Summary

- Implicit date- and timestamp-shaped YAML scalars decode as strings.
- Explicit YAML tags remain rejected.
- `format` remains annotation-only in every status and runtime.
- Semantic models own calendar-aware validation.
- Explicit portable JSON Schema assertions such as `pattern` remain structural.
- The TypeScript compiler removes only Zod’s intrinsic ISO date, datetime, time, and
  duration patterns so structurally corresponding Pydantic and Zod fields produce the
  same canonical sidecar.
- The sidecar digest proves structural identity, not equal Pydantic and Zod semantic
  accept sets; projects that require both align and test their model validators.
- No migration command or artifact rewrite is needed.
- Zod projects regenerate compiled sidecars after upgrading.

There are no open design questions.

## References

- [GitHub issue #22](https://github.com/jlevy/softschema/issues/22)
- [softschema Spec](../../../softschema-spec.md)
- [softschema Guide](../../../softschema-guide.md)
- [Python Package Design](../../../softschema-python-design.md)
- [TypeScript Package Design](../../../softschema-typescript-design.md)
- [Development](../../../development.md)
- [Minimal Softschema Hardening Plan](plan-2026-07-11-minimal-softschema-hardening.md)
- [JSON Schema Draft 2020-12 Format Vocabularies](https://json-schema.org/draft/2020-12/json-schema-validation#name-vocabularies-for-semantic-c)
- [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)
- tbd `common-doc-guidelines`
- tbd `general-testing-rules`
- tbd `golden-testing-guidelines`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
