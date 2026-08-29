---
title: Validate with Repair
description: Let the producing agent run the repair-and-conform pass its judge runs, as `softschema validate --repair`
author: Claude Code, with maintainer direction from Joshua Levy
---
# Feature: Validate with Repair

**Date:** 2026-08-29 (last updated 2026-08-29)

**Author:** Claude Code, with maintainer direction from Joshua Levy

**Status:** Implemented (phases 1-3); phase 4 and the metaproc coordination deferred

**Tracking:** `ss-pac1` (epic), with file-level children `ss-uwp6`/`ss-l3dc` (portable
helpers), `ss-arqr`/`ss-ioej`/`ss-ibay` (repair), `ss-1obx`/`ss-xisi`/`ss-roh1`
(conform), `ss-oguz`/`ss-unny`/`ss-xri1`/`ss-g5tr` (wiring), `ss-y3h8` (golden journey),
`ss-umu2` (docs), and the deferred `ss-e56b` (near-miss hint) and `ss-vt54` (metaproc),
from GitHub issue [#50](https://github.com/jlevy/softschema/issues/50)

## Overview

A model authoring a contract-bearing artifact writes YAML by hand, with no serializer in
the path and no schema in front of it.
Its characteristic failures are near-misses: an unquoted colon that makes the document
unparsable, or a name like `1850` that arrives as an integer against a `type: string`
field.
Both are one-turn repairs for the model that produced them, and both are currently
discovered after that model’s session has exited.

At least one downstream consumer, [metaproc](https://github.com/jlevy/metaproc), already
repairs and conforms an artifact before validating it.
An agent running `softschema validate` today therefore sees failures its judge would
have silently fixed, and its verdict disagrees with the gate’s.

This adds one escalating pass behind one flag, in both implementations:

```bash
softschema validate             # read-only check, as today
softschema validate --repair    # repair, conform, validate; writes the file
```

Because `--repair` writes, the artifact the orchestrator’s boundary later reads is
already repaired, so the operation is idempotent rather than duplicated.

## Goals

- One operation both a producing agent and an orchestrator boundary invoke, so the two
  agree by construction rather than by convention.
- Repair an unparsable document, which is a total loss today.
- Conform a scalar to the type its contract declares, in the one direction that can be
  corrected without guessing intent.
- Full Python/TypeScript parity: identical flag surface, identical verdicts, identical
  repair records.
- No new dependencies in either package.

## Non-Goals

- **Inferring a synonym rename.** A `reason` key where the contract wants `rationale` is
  a *missing field*, not a type error.
  Renaming it guesses intent.
  It is reported, never rewritten.
- **A second opinion about the schema.** The only defects acted on are the ones the
  existing validation layers already name.
  Nothing here decides independently what a document should look like.
- **A `repair` subcommand.** Repair without a verdict serves no caller; see
  [Rejected Alternatives](#rejected-alternatives).
- **Repairing files softschema does not validate.** Compiled schemas, generated
  sections, and installed skills keep their current owners.
- **Restyling.** A one-scalar fix must not reflow the document.

## Background

### What the issue proposed, and what the code shows

Issue #50 proposes migrating two modules out of metaproc (`engine/yaml_repair.py`, ~203
lines; `engine/schema_conform.py`, ~374 lines) on the grounds that neither is about
orchestration and both are about what a soft-schema artifact is allowed to look like.
That dependency-direction argument is correct — `schema_conform` already imports
`softschema.Contracts` — and both modules should move.

Review against the current tree changes five things about *how*.

#### 1. The stated prerequisite is already shipped

The issue treats the `required` message naming every required property as a load-bearing
prerequisite. That was fixed in v0.7.0, in both implementations, and the CHANGELOG lists
it as a breaking change.
`_structural_error_properties` (Python) and `ajvErrorProperty` (TypeScript) emit **one
record per absent property**, each carrying `property`:

```json
{"code": "missing_property", "property": "rationale",
 "message": "required property 'rationale' is missing", "path": []}
```

Acceptance criteria 1 and 5 from the issue already pass.
The patch the issue suggests would be a regression: it rebuilds an aggregate record with
a filtered list, discarding the per-property `property` field that
[the spec](../../../softschema-spec.md#matching-on-structural-error-records) now
documents as the field-level repair match surface.
This section is dropped from the plan.

#### 2. Conform has to read both validation layers, not one

The issue keys conform on Pydantic’s `string_type` error.
That covers only half the callers, and not the half the feature exists to serve.

`Contract.model` is `None` unless the caller passes `--model module:Class`, which
imports arbitrary local code and is documented as trusted-only.
The flagship agent flow — a self-describing artifact binding a compiled schema through
`softschema.schema` — has no Pydantic model at all.
A conform pass keyed on `string_type` **cannot fire for
`softschema validate --repair <artifact>`**, the exact command the issue proposes.

The mirror of that is just as sharp.
metaproc registers every built-in contract with a model and **no `schema_path`**
(`plugins/registry.py`), and softschema answers a missing schema with
`StructuralResult(ok=True, skipped_reason="no_schema")`. So a conform keyed only on the
structural layer would be a silent no-op for the very consumer this migration is for — a
regression from the code being moved.

softschema already runs
[two independent layers](../../../softschema-spec.md#validation-expectations) and
reports them separately.
The same defect simply has two spellings, and conform reads whichever ran:

| Source | Record | Available when |
| --- | --- | --- |
| Structural (JSON Schema) | `{code: "invalid_value", validator: "type", validator_value: "string", path: [...]}` | a compiled schema is bound |
| Semantic (Pydantic) | `{"type": "string_type", "loc": [...]}` | a model is bound |
| Semantic (Zod) | `invalid_type` issue with `expected: "string"` | a model is bound |

The structural source preserves the issue’s narrowness argument exactly — one keyword,
one direction, no inference — needs no model, and is emitted identically by Ajv, which
is what makes shared-corpus parity possible.
The semantic source keeps model-only callers working and is per-language by design,
which the parity policy already allows for Pydantic-versus-Zod behavior.

When neither is bound, validation is metadata-only, so conform has nothing to key on and
only repair runs. That is the correct outcome, and the result should say so rather than
report a silent success.

One TypeScript detail this exposes: `validateSemantic` currently maps a Zod issue to
`{code, path, message}` and **discards `expected`**, which is the field that identifies
a string-type issue.
The mapping has to carry it for the semantic source to work at all.

#### 3. Parity is a hard repo invariant, and the proposal is Python-only

[`docs/development.md`](../../../development.md) makes “equal flag/command surface” a
parity invariant enforced by the golden corpus, run twice through `SOFTSCHEMA_IMPL`. A
Python-only `--repair` fails that corpus.

Parity is achievable with no new dependencies.
TypeScript already parses through `parseDocument` from `yaml` — the round-trip,
comment-preserving API that is the direct analogue of ruamel’s `typ="rt"` — and already
depends on `atomically` for atomic writes.
Python already depends on `ruamel.yaml` and on `strif`, whose `atomic_write_text` is
what `compile` and `generate` write through today.

#### 4. Neither module can move verbatim

`yaml_repair`:

- Its line matcher is `^(\s+\w[\w_]*): `, which **requires leading whitespace**. In
  metaproc every payload sits under an envelope, so keys are always indented.
  softschema must also repair unindented keys: the frontmatter root, and the entire
  `pure-yaml` profile, whose payload root sits at column 0. Verified against the
  compiled pattern: the same key/value line matches when it is indented and fails to
  match at column 0, so a top-level `title: Note: actually Q1` is left unrepaired.
- It handles only the `---` fence.
  The `pure-yaml` profile has no fence.
- Its self-check is ruamel `YAML(typ="safe")`, not softschema’s `parse_yaml`. The
  portable reader adds rules ruamel does not: aliases and anchors rejected, merge keys,
  explicit tags, non-string mapping keys, depth 64, the IEEE-754 safe-integer range,
  negative zero, lone surrogates.
  A repair that satisfies ruamel but not `parse_yaml` would log “repaired” and then fail
  validation — precisely the failure its own docstring says it exists to prevent, moved
  up one layer.

`schema_conform`:

- Its `_COERCIBLE` set includes `datetime.date`, `time`, and `datetime`. softschema’s
  portable reader maps `tag:yaml.org,2002:timestamp` to a **string** on read (verified:
  `released: 2024-01-01` arrives as `"2024-01-01"`), and `_check_value` rejects
  host-native dates outright.
  A round-trip load, however, *does* produce `datetime.date`. The two parses disagree,
  which is a live hazard for a pass that writes back: conform must never re-emit a value
  the portable reader would then reject.
- Its alias-preservation machinery (`allow_aliases=True`, the pinned null representer,
  the `represented_objects` bookkeeping) exists to protect anchors.
  softschema rejects anchors and aliases at read time, so an artifact containing them
  never validates. That machinery can go — but the null-spelling behavior it also pinned
  must be preserved another way, or a null the pass did not touch changes shape.

#### 5. “Substitute softschema’s own” names two things softschema does not have

The issue’s migration table dismisses `atomic_output_file`, `fmf_split_frontmatter`, and
`new_yaml` in one row.
Only the first is a straight substitution (`strif.atomic_write_text` in Python,
`atomically` in TypeScript, both already used by `compile` and `generate`). The other
two are new work in both languages:

- **An offset-preserving frontmatter splitter.** metaproc splices the body back by byte
  offset, which is what keeps the body untouched.
  softschema’s readers do not expose offsets: both `read_frontmatter_doc` and
  `readFrontmatterDoc` split on lines and rejoin with `"\n"`, so a CRLF document is
  silently reflowed and a missing trailing newline is invented.
  Python can adopt `frontmatter_format.fmf_split_frontmatter`, already a dependency,
  which returns `(metadata_str, body_offset, meta_start)`. **TypeScript has no
  equivalent** and needs one written, reproducing the existing fence rules exactly —
  including the `trimEnd()` on the fence line and the `\r?\n` split, so repair and
  validation never disagree about where the frontmatter is.
- **A round-trip YAML writer.** softschema has no configured round-trip emitter in
  either language. Python’s `compile.py` uses `frontmatter_format.new_yaml` to write
  compiled schemas, but that is a fresh-document writer, not a formatting-preserving
  one. Both languages need an emitter configured for this pass: preserved quotes, no
  re-wrapping, the artifact’s own indentation, and the pinned null spelling noted above.

### Two further findings

**`--repair` makes softschema a writer of artifacts for the first time.** Today it
writes only files it owns: compiled schemas, generated sections, installed skills.
`validate` is read-only, and many library callers depend on that.
The closest precedent is `generate`, which pairs its write with `--check` and writes
atomically. `--repair` should follow that shape.

**The repair vocabulary is already shipped and must be reconciled.** `soft_field.py`
exports `RepairKind = Literal["none", "safe_coerce", "suggest_alias"]` — documented as
“how a *future repair pass* may treat near-miss values” — plus
`aliases: dict[str, list[str]]`, “controlled-vocabulary repair table”.
Both are propagated verbatim into compiled schemas.
This is that future repair pass.
See [Open Questions](#open-questions).

### Failure-class coverage

Measured against the four classes the issue names:

| Class | Today | After this plan |
| --- | --- | --- |
| Frontmatter syntax (unquoted `: `) | total loss; nothing downstream reads it | repaired |
| Scalar type drift (`1850` vs `type: string`) | `invalid_value` failure | conformed |
| Synonym substitution (`reason` for `rationale`) | `missing_property`, correct field named | reported, plus an optional near-miss hint |
| Envelope indentation (keys outdented past the envelope) | two `missing_property` records; the stray keys are **invisible** | reported, plus the same hint |

The last row is worth stating plainly, because neither migrating module addresses it:
`yaml_repair` sees a document that parses fine, and `schema_conform` sees no type error.
Verified against the current tree — the outdented keys produce no diagnostic of their
own. The near-miss hint is the right treatment, and for this case it must look at the
**frontmatter root**, not only at the envelope instance, because the stray keys are
siblings of the envelope rather than members of it.

## Design

### Approach

One escalating pass, exposed as one flag:

1. **Read.** Parse the document under the portable rules.
2. **Repair** (schema-free).
   If the parse failed, quote unsafe plain scalars and re-parse with `parse_yaml`. If it
   still fails, stop and report the original error.
3. **Conform** (schema-aware).
   Validate, and for each string-type disagreement either layer reports (see the table
   [above](#2-conform-has-to-read-both-validation-layers-not-one)), replace the scalar
   at that path with its own source text.
4. **Write**, atomically, once, only if something changed.
5. **Validate** the result and report both the verdict and what was changed.

Each step is guarded by the next: a repair that does not produce a parseable document is
discarded, and a conform that does not produce a portable value is discarded.

Two details the pass depends on:

**One write, not two.** metaproc writes in both its passes because they are separate
call sites. Here they are one operation, so repair hands its output to conform in memory
and the file is touched once.
That is what makes idempotence and the minimal-diff invariant testable rather than
emergent, and it means a conform failure cannot leave a half-applied file behind.

**Conform iterates to a fixed point, bounded.** A defect can hide another: fixing a
parent can reveal a child the validator never reached, which is why metaproc bounds
itself at `_MAX_ROUNDS = 3`. The pressure is lower here on the structural path, because
`iter_errors` and Ajv report the whole set at once — but not absent, since a corrected
type can newly satisfy an `if`/`then`, `anyOf`, or `$ref` branch that did not previously
apply, and the model path behaves exactly as metaproc’s does.
Keep the bound, and terminate on the first round that changes nothing rather than on the
round count, so the common case costs one pass.

### Components

| Module | Owns |
| --- | --- |
| `softschema/repair.py` / `src/repair.ts` | syntactic repair; no schema dependency |
| `softschema/conform.py` / `src/conform.ts` | type conform, keyed on both layers’ records |
| `softschema/_portable.py` / `src/portable.ts` | offset-preserving frontmatter split; round-trip writer |
| `validate.py` / `validate.ts` | the escalating pass; unchanged read-only entry points |
| `cli.py` / `cli.ts` | `--repair`, `--check-repair`; result reporting |

Repair and conform stay separate modules because they answer different questions and
have different dependencies: repair runs on documents that do not yet parse and needs no
schema; conform assumes a parseable document and needs the compiled schema.

### API Changes

Additive. `validate_artifact` keeps its read-only guarantee — a function named
`validate_` must not write the file its caller passed.

```python
def repair_artifact(path: Path) -> RepairResult:
    """Repair YAML that does not parse. Schema-free; runs before validation."""

def conform_artifact(
    path: Path,
    *,
    schema_path: Path | None = None,
    model: type[BaseModel] | None = None,
    envelope_key: str | None = None,
) -> ConformResult:
    """Coerce scalars to the string type the contract declares.

    Reads whichever validation layer is bound: the structural `type` record from
    `schema_path`, the semantic `string_type` record from `model`, or both. With
    neither, there is nothing to conform against and the result says so.
    """

def repair_and_validate_artifact(
    doc_path: Path, *, contract: Contract, write: bool = True
) -> ArtifactValidationResult:
    """Repair, conform, then validate. With write=False, report without touching the file."""
```

`ArtifactValidationResult` gains a `repairs: list[RepairRecord]` field, default empty,
so an existing consumer sees no change.
Each record reuses the documented match surface (`kind`, `code`, `path`) rather than
prose, so a caller matches a repair the same way it matches an error.

TypeScript mirrors all four, with the same names in camelCase.

### CLI surface

```
softschema validate <path>                  # unchanged; read-only
softschema validate <path> --repair         # repair, conform, write, validate
softschema validate <path> --check-repair   # report what --repair would change; no write
```

`--check-repair` mirrors `generate --check` and exists so a CI gate can ask “would this
have been repaired?”
without mutating a reviewed artifact.
Cheap now, awkward to retrofit.

Exit codes: `0` when the document validates (repaired or not), `1` when it does not, `2`
for usage and input errors, as today.
The JSON result distinguishes “was already valid” from “was repaired into validity”
through a non-empty `repairs`, because a gate cannot infer that from the exit code
alone. `--check-repair` exits `1` if anything would change.

### Invariants

These are the properties to test, not aspirations:

1. **Idempotence.** `--repair` twice produces the same bytes as once.
2. **Portable round-trip.** Any value conform writes is a value `parse_yaml` reads back
   unchanged. This is what keeps the date hazard closed.
3. **Minimal diff.** A document with one bad scalar differs by that scalar alone: no
   reflow, no re-indent, no requoting elsewhere, no line-ending change.
   Note that `read_frontmatter_doc` splits on `splitlines()` and rejoins with `"\n"`, so
   the write path must not go through the read path.
4. **No widening.** A document that validates without `--repair` is byte-identical after
   `--repair`.
5. **Parity.** Python and TypeScript produce the same bytes and the same records for
   every corpus document.

## Implementation Plan

### Phase 1: Syntactic repair, both implementations

Self-contained, no schema dependency, and the largest single win: an unparsable document
is a total loss today.

- [ ] Add the offset-preserving frontmatter split and the round-trip writer in both
  languages, since every later step writes through them.
  Python adopts `frontmatter_format.fmf_split_frontmatter`; TypeScript needs one written
  against the existing fence rules.
- [ ] Port `yaml_repair` to `softschema/repair.py`, dropping metaproc imports.
- [ ] Replace the self-check with `parse_yaml`, so repair is judged by the reader that
  will judge the artifact.
- [ ] Relax the line matcher to unindented keys, and cover the `pure-yaml` profile (no
  fence, payload at column 0).
- [ ] Exclude the portable violations that are not typos — aliases, anchors, merge keys,
  explicit tags — up front, with their existing error codes.
- [ ] Port to `src/repair.ts` on `parseDocument`.
- [ ] Shared vectors for the repair corpus, including the unindented and pure-yaml cases
  that metaproc’s version cannot reach.

### Phase 2: Type conform, both implementations

- [ ] `softschema/conform.py`, keyed on `{code: "invalid_value", validator: "type"}`
  records whose `validator_value` admits `string`, resolving the scalar through the
  record’s `path`.
- [ ] Add the semantic source alongside it, so model-only callers (metaproc’s registered
  contracts among them) keep the behavior being migrated.
- [ ] Carry `expected` through the TypeScript Zod issue mapping, which currently drops
  it, so the semantic source can identify a string-type issue at all.
- [ ] Iterate to a fixed point under a bound; terminate on the first no-change round.
- [ ] Derive the coercible set from softschema’s portable value domain, not metaproc’s:
  settle the `datetime` members against the round-trip/portable parse disagreement.
- [ ] Drop the alias machinery; keep the null-spelling pin under its own test.
- [ ] Preserve the source text of the scalar (`1.10` stays `1.10`, `007` stays `007`),
  so the fix is lossless.
- [ ] Port to `src/conform.ts`.
- [ ] Shared vectors for the structural source, including every notation the round trip
  does not preserve; per-language tests for the semantic source, as the parity policy
  already requires for Pydantic-versus-Zod behavior.

### Phase 3: Wire the pass and the flags

- [ ] `repair_and_validate_artifact` in both implementations.
- [ ] `--repair` and `--check-repair` on `validate`, in both CLIs.
- [ ] `repairs` on the result; atomic writes through `strif` and `atomically`.
- [ ] Golden scenario in `tests/golden/scenarios/`, run through all three
  `SOFTSCHEMA_IMPL` variants.
- [ ] Spec, guide, design docs, SKILL.md, and CHANGELOG.

### Phase 4 (separate change): near-miss key hint

Touches the message contract, so it lands on its own.

- [ ] When a required property is absent and the instance carries an undeclared
  near-miss key, name it.
- [ ] Extend the search to the frontmatter root, so the envelope-indentation class gets
  a diagnostic.
- [ ] Byte-identical strings in both implementations, with golden coverage in each.

## Testing Strategy

A pass that **writes the file it was asked to check** needs its testing settled up
front, not discovered case by case.
Two things make it unusual for this repo: the observable output includes a side effect
on disk, and the safety argument rests on what the pass *declines* to do.
Both shape what is tested and where.

### What owns what

Following the ownership rules in [`docs/development.md`](../../../development.md) — one
primary owner per case, never the same case at every layer:

| Layer | Owns | Does not own |
| --- | --- | --- |
| Shared vectors (`tests/vectors/hardening.yaml`) | which documents repair, which conform, which are deliberately left alone | anything about the CLI, or the filesystem |
| Golden journeys (`tests/golden/scenarios/`) | the CLI surface, exit codes, the `repairs` array, and the side effect on disk | library rules already pinned by a vector |
| Adapter unit tests | the filesystem boundary and the semantic source | restating the vector corpus |
| `cross-impl-diff.sh` | that both implementations write the same bytes | new cases of its own |

The shared corpus is the primary owner for repair and for the **structural** conform
source, because Ajv and `jsonschema` emit the same engine-neutral record and the rule is
therefore genuinely portable.
The **semantic** source is per-language on purpose: `docs/development.md` already scopes
Pydantic-versus-Zod behavior out of the shared corpus, so Pydantic `string_type` and Zod
`invalid_type` get adapter tests instead of vectors.

### The golden journey is the parity oracle

`tests/golden/scenarios/validate-repair.md` runs against Python, Node, and Bun through
`SOFTSCHEMA_IMPL`, so it is the one place the whole feature is checked as a caller sees
it. Three consequences for how it is written:

**Fixtures must be copied, not mutated in place.** `--repair` rewrites its input, so a
scenario that points at a checked-in fixture passes once and then fails on a dirty tree.
Each case copies its fixture to a scratch path first.
This is the one place these tests differ structurally from every existing scenario, and
getting it wrong makes the whole file non-reproducible.

**The file is part of the output.** A transcript that shows only the JSON verdict has
not tested the feature — the write is the deliverable.
Each mutating case `cat`s the file afterward, so the repaired bytes are in the
transcript and a reviewer reads the actual diff rather than trusting an `ok: true`.

**Elisions are for genuinely variable text only.** `[..]` covers scratch paths and
digests. It must not paper over a field that should be pinned, which for this feature
means the `repairs` array is never elided — it is the field a caller reads to tell “was
already valid” from “was repaired into validity”, and an elided one would hide a pass
that silently stopped firing.

### The invariants are test cases, not prose

Each of the five [invariants](#invariants) gets a case that fails if it breaks:

| Invariant | Where | Shape |
| --- | --- | --- |
| Idempotence | golden | `--repair` twice; the second run reports no change |
| Portable round-trip | vectors | every conformed value re-read through `parse_yaml` |
| Minimal diff | golden | `cat` after repair; one scalar differs, nothing else |
| No widening | golden | a valid document is byte-identical after `--repair` |
| Parity | `cross-impl-diff.sh` | same bytes, same records, both runtimes |

Minimal diff and no widening are the two most likely to rot silently, because a
formatting regression still validates.
Putting both in the transcript rather than in an assertion is deliberate: a reviewer
sees a whole-file diff the moment an emitter starts restyling.

### Negative cases carry the safety argument

The reason to trust this pass is the set of defects it refuses to touch.
That set is only real if it is tested, so each refusal is a named case rather than an
absence:

- a missing required field is **not** invented
- a near-miss synonym key (`reason` for `rationale`) is **not** renamed
- an explicit null is **not** stringified
- a union that already admits the value is **not** rewritten
- a genuinely wrong value is **not** coerced into looking right
- an alias, merge key, or explicit tag is **not** “repaired” — it is a semantic choice,
  not a typo, and quoting cannot fix it

A change that widens the fixable set has to delete one of these to land, which is the
point.

### Two regression guards worth naming

**The model-only conform path.** Assert directly, in both adapter suites, that a
contract with a model and no `schema_path` still conforms.
This is the metaproc case, and the failure mode is a silent no-op that every other test
passes through happily.

**Line endings and the trailing newline.** Both existing readers normalize CRLF and can
invent a trailing newline; the write path deliberately does not go through them.
A CRLF fixture and a fixture with no final newline both belong in the adapter suites,
because a golden transcript will not show the difference.

### Ported coverage

metaproc’s suites (`test_yaml_repair.py`, ~354 lines; `test_schema_conform.py`, ~407
lines) are a substantial head start, and its `TestRecordedNotationLimits` already pins
the two notations a round trip does not preserve (a bool comes back canonically spelled,
an integer’s leading `+` is dropped).
Port the cases; do not port the structure, since ownership here splits differently.

### Acceptance criteria

The four that survive from the issue:

1. `--repair` on a document with an unquoted colon repairs it, writes it, and validates.
2. `--repair` on `1850` against `type: string` conforms it and validates clean.
3. A missing required field is not auto-fixed, and neither is a near-miss synonym key.
4. Every case above holds identically in Python and TypeScript.

(The issue’s criteria 1 and 5, on the `required` message, already pass; regression
coverage exists.)

Plus three this review adds:

5. A model-only contract still conforms.
6. `--repair` on an already-valid document leaves it byte-identical.
7. `--check-repair` never writes, and exits 1 exactly when `--repair` would change
   something.

## Rollout Plan

Minor release: new CLI flags, new public functions, one additive result field.
No existing verdict changes, and `validate` without `--repair` is untouched.

Coordinated with metaproc, which pins `softschema>=0.7.0,<0.8`:

1. Release softschema with the migrated code.
2. In one metaproc change: bump the pin, delete `engine/yaml_repair.py` and the
   per-artifact half of `engine/schema_conform.py`, retire the
   `metaproc softschema repair` subcommand, and repoint `repair_declared_outputs` and
   `conform_declared_outputs` at the softschema functions.

The orchestration wrapper stays in metaproc: `resolve_templates`,
`resolve_output_fpath`, `IOSpec`, and `plugins.discovery` are about declared outputs,
not about what an artifact may look like.

Both releases land together.
A metaproc pinned to a softschema without the migrated code, with its own copies already
deleted, silently loses repair at its boundary.

## Rejected Alternatives

**A `repair` subcommand.** Steps 2 and 3 are already validation and step 1 must precede
it, so these are not separable operations with independent value.
Telling a caller a document was repaired without telling it whether the document is now
acceptable serves nobody.
(metaproc has such a subcommand today; it is retired rather than moved.)

**`--forgiving`.** `SchemaStatus` already has `enforced`, `permissive`, and `soft`, and
artifacts declare `status: permissive` in their own frontmatter.
A fourth tolerance-sounding word invites confusion about which leniency is in force.
`--repair` names the action, not a disposition.

**A retry policy keyed to what failed.** A policy declared for the failure kind observed
at the time does not fire for the next kind, and the same loss returns wearing a
different label.
A declaration naming `semantic` does nothing for a `structural` failure,
and a default retryable set covering *absent* or *unreadable* artifacts covers none of
the ways a *present* artifact can be wrong.
Letting the producer see and fix its own failures does not depend on classifying them
correctly after the fact.

**Keying conform on one validation layer.** Either layer alone leaves half the callers
unserved: Pydantic `string_type` cannot fire for the CLI flow this feature exists to
serve, and the structural record cannot fire for model-only contracts like metaproc’s.
See [Background](#2-conform-has-to-read-both-validation-layers-not-one).

## Open Questions

Questions 1-3 were settled during implementation and are recorded here with what was
decided; question 4 is still open, and belongs to the deferred phase 4.

1. **Is string coercion unconditional, or gated on `repair: safe_coerce`?** *Decided:
   unconditional.* The issue argues it is intent-free and therefore always safe.
   The shipped `RepairKind` vocabulary defaults to `none`, which reads as opt-in.
   *Recommendation:* unconditional for the `type: string` case — a provably lossless fix
   should not need per-field opt-in — and repurpose `suggest_alias` plus the `aliases`
   table to power **non-mutating** suggestions in the error records.
   That keeps the shipped vocabulary meaningful without making the safe fix opt-in.
   Needs a maintainer decision before Phase 2, since it is a documented public
   annotation.

2. **Does `--repair` write a file that still fails validation?** *Decided: yes.* A
   document can be repaired into parseability and still be invalid.
   *Recommendation:* yes — write it.
   The repair is independently correct, and leaving an unparsable file on disk to
   preserve a failing verdict helps nobody.
   Needs confirming, since it means a failing gate can still mutate a file.

3. **What does `--repair` do for a `pure-yaml` artifact?** *Decided: same treatment, and
   it is covered by both the shared vectors and the golden journey.* Repairing the whole
   document, rather than a fenced region, is a larger blast radius.
   *Recommendation:* same treatment, same invariants.
   Excluding it would leave one of two supported profiles without the feature.

4. **Does the near-miss hint (Phase 4) belong in `message`, or in a new record field?**
   `message` wording may improve within a minor release, but the parity contract makes
   every wording change a two-implementation change with golden updates in both.
   A separate field is cheaper to evolve and easier to match on.

## References

- [Issue #50](https://github.com/jlevy/softschema/issues/50): the original proposal.
- [softschema Spec](../../../softschema-spec.md): validation expectations and the
  structural-error match surface.
- [Development guide](../../../development.md): the parity loop and its invariants.
- [Python design](../../../softschema-python-design.md): the `SoftField` `repair` and
  `aliases` annotations.
- [metaproc](https://github.com/jlevy/metaproc): `src/metaproc/engine/yaml_repair.py`
  and `src/metaproc/engine/schema_conform.py`, the code being migrated.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
