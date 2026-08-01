# Review: Softschema Full Engineering Review

**Date:** 2026-06-10

**Status:** Review complete

**Reviewer:** Claude Code

## Summary

This is a full senior engineering review of the repository: the soft-schema theory and
how it is explained, the spec, the Python and TypeScript libraries and CLIs, the agent
skill and its self-installation flow, the parity machinery, and the tests.
Everything was reviewed against the repo’s own guidelines (`general-coding-rules`,
`error-handling-rules`, `python-rules`, `python-modern-guidelines`,
`python-cli-patterns`, `typescript-rules`, `typescript-cli-tool-rules`,
`typescript-yaml-handling-rules`, `golden-testing-guidelines`,
`cli-agent-skill-patterns`, `general-testing-rules`, and `common-doc-guidelines`).

The overall state is strong.
Both test suites pass (78 Python, 78 TypeScript), lint and typecheck are clean, the
golden corpus passes against both implementations, the canonical `schema_sha256`
guarantee genuinely holds for the kitchen-sink conformance fixture, supply-chain hygiene
(cool-off windows, pinned tool versions, OIDC trusted publishing) is well above average,
and nearly every finding from the prior review
(`review-2026-05-26-softschema-docs-design.md`) was addressed.

The most important problems found, in order:

1. **Spec violations both implementations share.** Unknown keys in the `softschema:`
   block are silently accepted (the spec mandates rejection); the library’s envelope
   handling does not implement the spec’s single-key inference or ambiguity rejection
   (only the CLI layer does); the pure-yaml profile ignores the envelope rules entirely;
   “malformed `contract`” is a validation error the spec never defines.
2. **Unhandled error paths in both CLIs.** Missing files, malformed frontmatter, and bad
   `--model` specs produce raw tracebacks (Python) or rely on unsafe error casts
   (TypeScript). The library API itself raises on a missing file instead of returning a
   structured result.
3. **The agent bootstrap chain is broken on npm.** The TypeScript CLI lacks the
   “IMPORTANT for agents” `--help` epilog that the Python CLI has, so
   `npx softschema --help` never routes an agent to `skill --brief`.
4. **Parity is enforced only for the inputs the corpus contains.** Known Python/JS
   number-formatting divergences (`1e-07` vs `1e-7`, `inf` vs `Infinity`, different
   exponential-notation thresholds) sit just outside the tested value ranges, and the
   TypeScript golden run executes under Bun while the published package’s primary
   runtime is Node.
5. **Docs have not caught up with the TypeScript port.** The guide and the Python design
   doc still describe TypeScript as a future or deferred path, and the public-readiness
   plan describes a pre-TypeScript world while marked Complete.

Each section below gives findings with severity and file references, followed by
prioritized recommendations.

## What Is Working

- The core theory has a real center of gravity: authoritative YAML at the boundary,
  reader-facing prose, contract IDs that name payloads rather than classes, and
  per-field gradual promotion.
  The “Common Mistakes” and playbook sections of the guide are genuinely useful.
- The dual-implementation discipline is unusually good: a shared golden corpus run
  against both CLIs, a committed cross-language conformance fixture with an asserted
  `schema_sha256`, engine-neutral structural error templates, and a documented
  golden-first development loop in `docs/development.md`.
- The canonicalization layer (`canonicalize.py` / `canonicalize.ts`) is tightly
  synchronized, schema-aware (it never strips `title` when it is a property name), and
  well-commented about why each transform exists.
- The skill follows the progressive-disclosure pattern the `cli-agent-skill-patterns`
  guideline recommends: an 83-line routing SKILL.md, `skill --brief` for a compact
  brief, `docs <topic>` for full material, and a Python-side mirror drift test.
- Supply-chain posture: 14-day cool-off via `UV_EXCLUDE_NEWER`, per-package documented
  exceptions (`strif`, `flowmark-rs`), pinned action and tool versions, OIDC trusted
  publishing for npm, and lockfile-enforced installs in CI.
- The prior docs review was almost fully executed: the conflicting standalone design doc
  was removed, the guide was restructured into playbooks, the spec was tightened, and
  `docs/project/` now separates internal planning from public docs.

## Broad Design Issues

### 1. `status` Is the Theory’s Central Knob but Has No Runtime Effect

The soft → permissive → enforced spectrum is the heart of the soft-schema story, yet the
spec says `status` “does not change validation behavior by itself”
(`docs/softschema-spec.md:134`), and the implementations treat it as a pass-through
label. Enforcement actually lives in the source model (`extra="forbid"` in Pydantic,
`strictObject` in Zod), so flipping `status` requires a second, separate change that the
artifact’s own metadata cannot verify.
The guide’s playbooks read as if the flip does something ("flip `status: enforced` and
set the source model to `extra=\"forbid\"`", guide step 5), which invites users to flip
the label and believe they changed behavior.

Two coherent resolutions exist; the current middle position is the worst of both:

- **Give it teeth.** Let the validator honor `status`: under `enforced`, inject
  `additionalProperties: false` at the structural layer (or fail on unknown-extra-field
  results); under `soft`, downgrade structural errors to warnings.
  This makes the artifact self-describing, which is the stated goal of the metadata.
- **Declare it advisory, loudly.** Keep current behavior, but say in the spec and the
  guide, at first mention, that `status` is intent metadata that validators echo but
  never act on, and reframe the playbook steps so the model change is the action and the
  status field is the record of it.

Either way, the spec, guide, and implementations should agree on which one it is.

**Decision (2026-06-10): give it optional teeth.** Enabling strictness must enforce it;
not wanting enforcement means not enabling stricter settings.
Concretely: when the effective status is `enforced`, structural validation treats every
object schema that declares `properties` but omits `additionalProperties` as
`additionalProperties: false`. An explicit `additionalProperties` value in the schema
(true, false, or a subschema) always wins, so a schema can opt specific objects out.
Object schemas without `properties` (free-form mappings) are unaffected.
`soft` and `permissive` keep exactly today’s behavior: no loosening, no downgrade of
errors to warnings. The overlay is validation-time only and never changes compiled
sidecars; the rejected extras surface as ordinary `additionalProperties` schema
violations through the existing engine-neutral error normalization, so cross-language
output stays byte-identical.
The effective status resolves as it does today: the caller’s contract or `--status` flag
first, then the document’s declared `softschema.status`. Spec, guide, and the design
docs must be updated to state this behavior.

### 2. The Spec’s Envelope Rules Live Only in the CLI, Not the Library

The spec requires single-key envelope inference and explicit-designation-or-rejection
for multi-key documents (`docs/softschema-spec.md:101-110`). The Python CLI implements
this (`_envelope_from_args`, `packages/python/src/softschema/cli.py:242-253`), but the
library does not: `validate_artifact` with a contract that has no `envelope_key` merges
**all** non-`softschema` top-level keys into one payload (`_extract_envelope_values`,
`packages/python/src/softschema/validate.py:279-288`). The TypeScript library mirrors
this.

Consequences:

- A library caller registering a contract without `envelope_key` gets behavior the spec
  explicitly rules out (multi-key documents validate as a merged mapping instead of
  being rejected as ambiguous).
- The envelope-inference logic is duplicated per language in the CLI layer, the exact
  place the parity strategy tries to keep thin.
- The CLI reads and parses the document twice (once in `_infer_validation_binding`, once
  inside `validate_artifact`).

Recommendation: move binding inference (contract from metadata, status resolution,
single-key envelope inference with ambiguity rejection) into the library in both
languages, and have the CLIs call it.
One implementation per language instead of two, and library users get spec-conforming
behavior.

### 3. The Pure-YAML Profile Does Not Follow the Spec’s Envelope Rules

The spec says a pure-yaml artifact “follows the same metadata and envelope rules” with
frontmatter rules applying to the document root (`docs/softschema-spec.md:30-31`). The
implementations validate the entire YAML root as the payload with no metadata extraction
and no envelope handling at all (`_validate_pure_yaml_artifact`,
`packages/python/src/softschema/validate.py:260-276`; same shape in `validate.ts`). A
pure-yaml file carrying a `softschema:` block would have that block validated as payload
data. Either the spec should describe what the implementations do (root is the payload,
no metadata block) or the implementations should honor the stated rule.

### 4. “Exact Behavioral Parity” Is Stronger as a Claim Than as an Enforced Invariant

The parity engineering is real and impressive, but the README’s claims outrun what CI
enforces:

- “Byte-identical” sidecars are content-identical with an equal `schema_sha256` over
  canonical JSON; the YAML file bytes differ between implementations (block-sequence
  indent style, `10.0` vs `10` for integer-valued floats).
  `compile --check` deliberately compares parsed content, not bytes
  (`packages/python/src/softschema/compile.py:58-61`). The claim should be phrased as
  what it is, which is still a strong guarantee.
- CLI output parity holds for the golden corpus’s value ranges, but known Python/JS
  divergences sit just outside them (see Cross-Language Disparities below).
  Error paths (tracebacks, usage errors) diverge completely.
- `--help` output is not byte-comparable (argparse vs commander) and is not in the
  corpus, which is how the missing TypeScript epilog shipped unnoticed.
- The TypeScript golden run executes `bun dist/cli.js` (`tests/golden/run.sh:28`), while
  the published package’s primary invocation is `npx softschema` under Node.
  Node never runs the corpus in CI.

**Direction (2026-06-10): exact parity is the requirement, not an aspiration.** The Node
gap above is a serious shortcoming, since Node is the runtime npm users actually get.
Three principles govern the fix:

- The golden corpus must run under Node as well as Bun in CI (for example
  `SOFTSCHEMA_IMPL=ts` running `node dist/cli.js` as the primary TypeScript target, with
  a Bun variant alongside), so the published runtime is what parity is proven on.
- Golden scenarios must be **the same files** run by both CLIs whenever possible; the
  per-implementation `scenarios-py/` and `scenarios-ts/` directories stay reserved for
  the few invocations that genuinely differ by language (such as `compile` model specs)
  while producing identical output.
- Most functionality should be exposed through the CLI, precisely so the shared corpus
  can exercise it; behavior that only exists as library API is behavior the shared
  corpus cannot hold to parity.

The remaining items (claim calibration, `--help` coverage) are documentation and corpus
additions on top of that.

### 5. Error Handling Has No Boundary in Either CLI

Both CLIs catch a narrow, hand-picked exception set per command and let everything else
escape. The result is raw tracebacks for ordinary user mistakes (Python) and `undefined`
in messages for non-Error throws (TypeScript).
Reproduced examples are in Specific Issues below.
Per `error-handling-rules` and `python-cli-patterns`/`typescript-cli-tool-rules`, each
CLI should have one top-level error boundary that maps expected failure families (file
missing, parse error, bad model spec) to a clean one-line stderr message and exit 2, and
reserves tracebacks for genuine bugs.

### 6. The Adoption Funnel Has a Gap at the Soft Stage

The theory says to start with `status: soft`: a contract ID and metadata but no model or
sidecar yet. At that stage the tool offers nothing: `validate` requires `--model` or
`--schema` (`cli.py:200-201`), and `inspect` does no checking (and crashes on malformed
metadata).
A user following the playbooks gets no value from the CLI until step 4 of 6. A
metadata-only validation mode (validate the `softschema:` block shape, contract ID form,
envelope-key presence and uniqueness, and nothing else) would make `softschema validate`
useful from day one and directly serve the gradual-adoption story.
It would also give the spec’s metadata rules (unknown keys, malformed contract) an
enforcement point even when no schema exists.

### 7. The `--model` Flag Imports Arbitrary Code by Design

`_load_model` prepends the working directory to `sys.path` and imports whatever module
the spec names (`cli.py:404-419`); the TypeScript CLI dynamically imports a file path.
This is appropriate for a developer tool, but it deserves one sentence of documentation
("`--model` executes the named module; only point it at code you trust"), since
`validate` reads otherwise-untrusted artifacts and users may not expect the flag to
execute code.

## Ideas for Improvements and Simplifications

Ordered roughly by leverage:

1. **Move binding inference into the libraries** (design issue 2). Removes duplicated
   CLI logic in both languages, fixes the library/spec divergence, and eliminates the
   double file read.
2. **Add a single error boundary per CLI** (design issue 5). One change point fixes the
   entire family of traceback bugs and makes future commands safe by default.
3. **Decide what `status` means** (design issue 1) and make spec, guide, and
   implementations say the same thing.
4. **Metadata-only validate mode** (design issue 6). Small surface, large payoff for the
   adoption story, and it gives the spec’s metadata rules a home.
5. **Share the doc-topic registry.** `DOC_TOPICS` is hand-duplicated in `cli.py:33-100`
   and `cli.ts:47-130`. A small bundled JSON/YAML resource read by both CLIs would
   remove a silent drift channel (golden tests check `docs --list` output, which helps,
   but the per-topic paths and the bundle manifests can still drift, and already have;
   see Packaging below).
6. **Generate the resource manifests from one list.** The Python wheel `force-include`,
   the TypeScript `copy-resources.ts` list, and `DOC_TOPICS` are three hand-maintained
   copies of the same file set, and they already disagree (`typescript-design` missing
   from the wheel, `movie-page.schema.yaml` missing from the npm resources).
   One manifest, three consumers, plus a test that every `DOC_TOPICS` path resolves from
   the built artifact.
7. **Cache or hoist the Ajv instance.** `validateStructural` builds a new Ajv and
   recompiles the schema on every call (`validate.ts:129-131`). The primary library use
   case is validating many artifacts against one contract in a loop.
8. **Trim the bundled doc set.** `publishing` and `agents` topics ship maintainer-facing
   and repo-internal content to end users; `AGENTS.md` even carries the tbd integration
   block ("This repository uses tbd...", `AGENTS.md:70-83`), which is meaningless and
   confusing inside an installed package.
   Either drop these topics from the bundles or strip repo-internal blocks at bundle
   time.

## Use-Case Walkthroughs

**A Python developer adopts softschema in an existing repo.** The README quickstart
works as documented (verified:
`uv run softschema validate ... --model ... --schema ... --envelope movie` succeeds, and
the docs/skill commands print correctly).
The first rough edge appears on mistakes: a typo’d path or model spec produces a raw
traceback instead of a usage error.

**A coding agent bootstraps via npm.** `npx softschema --help` prints commander help
with no agent epilog, so the discovery chain (help → brief → docs) never starts
(`cli.ts`, missing `addHelpText`; the Python CLI has it at `cli.py:107-111`). The
SKILL.md also recommends `npx softschema@latest`, an unpinned network runner the
`cli-agent-skill-patterns` guideline warns against (the installation doc’s cool-off
rationale is reasonable, but the skill text itself should carry the justification or a
pin).

**A user installs from PyPI and reads the bundled docs.**
`softschema docs typescript-design` crashes with a `FileNotFoundError` traceback: the
topic is registered in `DOC_TOPICS` but the file is absent from the wheel’s
`force-include` (`pyproject.toml:71-87`). `softschema docs agents` serves tbd
instructions that do not apply to the user’s repo.

**A host application validates artifacts in a loop.** `validate_artifact` on a path that
does not exist raises instead of returning a structured failure (`validate.py:184`,
OSError not caught), so pipeline callers must wrap it themselves.
On the TypeScript side every call pays Ajv construction and schema compilation.
A contract without `envelope_key` silently validates merged multi-key frontmatter the
spec says must be rejected (design issue 2).

**A team starts soft and tightens gradually.** At `status: soft` with no model, the CLI
can do nothing for them (design issue 6). When they do add enforcement, flipping
`status` alone changes nothing (design issue 1), and an artifact whose `softschema:`
block misspells a key (say `status` with a dropped letter) validates without complaint,
despite the spec (see Bugs).

**A research agent builds a corpus of loosely structured records.** An agent collects
documents on many items of one kind (companies, products, papers), each starting as
mostly prose with a few frontmatter fields.
Over time the agent promotes more values into YAML, record by record, until every
document carries a highly structured payload under one contract.
The endgame is a strict schema whose fields can be synchronized into a typed database or
drive UI features such as sort and filter, where those features only work if the strict
fields are **known to be enforced** across the whole corpus.
This use case is why the `status` decision above matters: `enforced` must actually
guarantee that every validated record has exactly the declared shape, so a downstream
database sync or UI can trust the corpus without re-checking it.
It also stresses migration (hundreds of records at mixed maturity levels validated under
one contract), batch validation ergonomics (the library loop and CLI over many files),
and the soft-stage gap (early records have contracts but no schema yet).

**A polyglot team relies on parity.** For ordinary artifacts, parity holds and is
well-tested. An artifact with a value like `1e-7` or `Infinity` in frontmatter, or a
schema bound that JS prints in expanded notation, produces different bytes from the two
CLIs (see Cross-Language Disparities).
Nothing in CI runs the corpus under Node, the runtime npm users actually get.

## Documentation Review

### Spec (`docs/softschema-spec.md`)

The spec is concise and mostly normative, a clear improvement after the prior review.
Remaining gaps:

- **HIGH. “Malformed `contract`” is undefined** (lines 86-87, 170). The recommended ID
  form is explicitly advisory, so it cannot be the definition.
  Implementations accept any string.
  Define the minimum (for example “a non-empty string; the recommended form is...”) or
  say only non-strings are malformed.
- **HIGH. Unknown-key rule is not implemented** (line 86 vs both `models.py` and
  `models.ts`); see Bugs.
  Decide: enforce it (likely right; the spec is unambiguous) or relax the spec for
  forward compatibility.
- **MEDIUM. Pure-yaml envelope rules** (design issue 3): spec text and implementation
  disagree.
- **LOW. Add a one-paragraph conformance-language note** ("'must' is a requirement on
  implementations or artifacts") so statements like “never authoritative” have a clear
  addressee.

### Guide (`docs/softschema-guide.md`)

The playbook structure is good and matches the prior review’s proposed shape.
The main problem is staleness from the TypeScript port:

- **HIGH.** “What Softschema Is” (lines 34-39) defines the tool as “a Python package”
  and offers TypeScript as something “another project could implement.”
  The “Relationship To The Python Package” section (lines 626-666) and Further Reading
  (lines 668-677) ignore the TypeScript package entirely.
- **MEDIUM.** The CLI list (line 642-643) omits `softschema generate`.
- **LOW.** Line 369: “an `SoftField` annotation” should be “a `SoftField` annotation.”
- **LOW.** `status` framing (design issue 1): step 5 of the promotion playbook should
  make the model change primary and the status flip the record of it.

### README

- **MEDIUM.** “Unreasonably effective” (line 11) is exactly the extravagant-language
  pattern `common-doc-guidelines` prohibits; the surrounding paragraph already makes the
  calibrated version of the claim.
- **MEDIUM.** “Byte-identical” sidecar claims (lines 127, 328) should be qualified as
  content-identical with equal `schema_sha256` (the YAML bytes differ; see parity
  findings).
- **MEDIUM.** The README is a 395-line document that the design doc says should be “a
  short subset of the guide” (`softschema-python-design.md:46-48`). The full movie
  artifact appears in README, guide, and (abbreviated) spec; three hand-synced copies.
  Shorten the README’s artifact to a fragment plus a link, or accept and document the
  duplication cost.

### Design Docs

- **HIGH.** `docs/softschema-python-design.md` contradicts shipped reality: “the future
  TypeScript port” (lines 26, 152), “Keep TypeScript/Zod as a future path, represented
  only by a README stub” under **Accepted** (line 374), “TypeScript/Zod implementation”
  under **Deferred** (line 383). The module table (line 23) also lists “stage” models;
  `SchemaStage` no longer exists.
- **MEDIUM.** The doc states unknown metadata keys are an error
  (`document_softschema_invalid`, line 202: “unknown keys, bad shape”); the
  implementation does not enforce that (see Bugs).
  One of them must change.
- **LOW.** Line 352: “the contract, envelope, contract, and validation semantics”
  (duplicate word).
- `docs/softschema-typescript-design.md` is accurate and appropriately scoped.

### Workflow and Project Docs

- **HIGH.** `docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md` is
  marked Complete but describes a pre-TypeScript world (TypeScript as “placeholder
  only,” a “Future TypeScript/Zod Package” section, deferred decisions that have since
  been decided). Mark it superseded with a pointer to the parity plan, or move it out of
  `active/`.
- **MEDIUM.** `docs/publishing.md:64-75` still describes npm as unclaimed at 0.1.2; the
  bootstrap has happened (npm is at 0.1.3). Rewrite as present state.
- **LOW.** `docs/publishing-npm.md` (210 lines) is linked from no other document.
- **LOW.** `AGENTS.md` carries the doc-guidelines footer twice (lines 66-68 and 85-87).
- **LOW.** The GitHub Actions example in `docs/development.md:136-138` pins
  `actions/checkout@v4` and `astral-sh/setup-uv@v3` while the repo’s own CI uses v6 and
  v8; copyable snippets should track what the repo itself uses.

## Skill and Self-Installation Review

Measured against `cli-agent-skill-patterns.md`. The structure is right: portable
frontmatter (name plus a two-part trigger-rich description), an 83-line routing body,
progressive disclosure through the CLI, committed-and-dogfooded mirrors with a Python
drift test. Findings:

- **HIGH. TypeScript CLI has no `--help` epilog** (`cli.ts`; Python’s is at
  `cli.py:107-111`). The npm bootstrap chain is broken, and since `--help` output is not
  in the golden corpus, parity machinery cannot catch it.
  Add the same text via commander’s `addHelpText` hook on the program.
- **MEDIUM. No format or version stamp on the DO NOT EDIT marker** (`cli.py:341-345`,
  `cli.ts:152-153`). The guideline’s forward-compatibility model (format codes on
  generated artifacts) is absent: an older CLI cannot detect a newer-format mirror, and
  a human cannot tell which version wrote one.
- **MEDIUM. The `<version>` substitution is dead code in both CLIs** (`cli.py:357`,
  `cli.ts:167`): SKILL.md contains no `<version>` placeholder, so the rendered skill and
  the installed mirrors carry no version anywhere, and the tests asserting
  `"<version>" not in output` (`test_cli.py:207,231`) pass vacuously.
  Either stamp the version into the marker (preferred, pairs with the previous finding)
  or delete the substitution and the vacuous assertions.
- **MEDIUM. No TypeScript mirror drift test** and `skill --install` is untested in
  TypeScript (`test_skill_mirror_drift.py` has no counterpart; `cli-inprocess.test.ts`
  covers `skill` and `skill --brief` only).
- **MEDIUM. Non-atomic install writes**: `_install_skill` uses `target.write_text`
  (`cli.py:383`) where `python-modern-guidelines` requires atomic writes; `compile` and
  `generate` already use `atomic_write_text`.
- **LOW. `--install` is cwd-relative with no repo-root awareness** (`cli.py:395`):
  running from a subdirectory silently plants `.agents/` and `.claude/` in the wrong
  place. Walk up to the git root, or warn when no `.git` is found.
- **LOW. No `allowed-tools` in the skill frontmatter**;
  `allowed-tools: ["Bash(softschema:*)"]` would remove permission prompts for the common
  case.
- **LOW. `@latest` runners in SKILL.md** conflict with the guideline’s pinning rule;
  carry the cool-off justification or a pin in the skill text itself.

## Specific Issues and Bugs

### Python

- **HIGH. Raw tracebacks for ordinary errors** (all reproduced):
  - `softschema validate <missing-file> --schema x` → `FileNotFoundError` traceback
    (`fmf_read` in `_infer_validation_binding`, `cli.py:220`, uncaught).
  - `softschema validate <malformed-frontmatter> ...` → ruamel `ScannerError` traceback
    from the same call site (the clean `parse_error` handling inside `validate_artifact`
    is never reached).
  - `softschema validate doc.md --model nonexistent:Foo` → `ModuleNotFoundError`
    traceback (`_load_model`, `cli.py:413`; the except clause at `cli.py:204` lists only
    `TypeError, ValueError, ValidationError`).
  - `softschema inspect <missing-or-malformed>` → traceback (`_inspect_cmd`,
    `cli.py:267-284`, no error handling at all; `parse_schema_metadata` raising
    `TypeError` on `softschema: [1, 2]` is also uncaught).
- **HIGH. `validate_artifact` raises on missing files** instead of returning a
  structured result (`validate.py:183-186` catches `FmFormatError, YAMLError` but not
  `OSError`; same for the pure-yaml path at `validate.py:265-268`).
- **HIGH. Unknown `softschema:` keys accepted, violating the spec.** `SchemaMetadata`
  (`models.py:27-33`) lacks `extra="forbid"`; reproduced:
  `softschema: {contract: ..., bogus: 1}` validates with `ok: true` and no warning.
- **MEDIUM. `generate` exit codes conflate error and drift.** `_generate_cmd` returns 1
  for runtime errors (`cli.py:320`) where the documented convention
  (`softschema-python-design.md:159-161`) reserves 1 for validation failure or drift and
  2 for usage/runtime errors; `validate` and `compile` use 2.
- **MEDIUM. `KeyError` escapes from vocab generation**: a `pointer` to a nonexistent
  field raises `KeyError` from `SchemaView.field` (`schema_view.py:96-100`) through
  `regenerate`, which catches only `OSError, ValueError` (`cli.py:318`).
- **MEDIUM. `_dev_repo_root` falls back to `parents[4]`** (`cli.py:493`), an arbitrary
  directory when installed; return an error instead of guessing.
- **LOW. No `--version` flag** (`_installed_version` exists but is unwired).
- **LOW. `_schema_sha256` uses `default=str`** (`compile.py:111`): a
  non-JSON-serializable value in a schema would be silently stringified into the hash
  instead of failing loudly.
- **LOW. `_brief_skill_text` is a flush-left multi-line string** (`cli.py:458-472`)
  contrary to `python-rules` (use `dedent`).
- **LOW. `pytest` config sets `python_files = ["*.py"]`** (`pyproject.toml:166`), making
  every module in `testpaths` a test candidate; the default `test_*.py` is safer.
- **NIT. Enum values are interpolated into Markdown tables unescaped**
  (`generate.py:170-171`); a value containing `|` breaks the table.
- **NIT. `devtools/lint.py:74` reads files without `encoding="utf-8"`.**

### TypeScript

- **HIGH. `process.exit()` after `.then()` can truncate piped stdout** (`cli.ts:532`).
  Set `process.exitCode` and let the loop drain instead.
- **MEDIUM. No EPIPE handlers on stdout/stderr and no SIGINT handler (exit 130)**, both
  required by `typescript-cli-tool-rules`; `softschema docs guide | head` can die with
  an unhandled `EPIPE`.
- **MEDIUM. Unsafe `(err as Error).message` in catch blocks** (`cli.ts:317, 365, 378`):
  a non-Error throw prints `softschema validate: undefined`. Use
  `err instanceof Error ? err.message : String(err)`.
- **MEDIUM. Schema sidecar parsing bypasses the `parseYaml` wrapper**
  (`validate.ts:253`): malformed sidecar YAML surfaces as a raw library error with an
  inconsistent type, and the `as Record<string, unknown>` cast is unchecked for
  non-mapping roots.
- **MEDIUM. `test/` is not typechecked**: `tsconfig.json` includes only `src`, so
  `bun run typecheck` never sees `test/*.test.ts`.
- **LOW. Library entry has transitive `node:` imports** (and the bundled shared chunk
  imports `node:module`), contrary to the guideline’s node-free `"."` entry point;
  either split entries or document the package as Node-only.
- **LOW. No `--version` flag** (`packageVersion()` exists but `.version()` is never
  called).
- **LOW. No `"./cli"` export in `package.json`.**
- **LOW. Magic walk-up depth `6` in `readResource`** (`cli.ts:31`) should be a named
  constant; same fragility class as Python’s `parents[4]`.
- **NIT. Dead code**: `export type { FieldInfo }` in `generate.ts:156` (re-exported from
  nowhere), `options.order !== null` check on a field typed `number | undefined`
  (`softField.ts:29`), `isMain` fallback `endsWith("cli.js")` (`cli.ts:530`).

### Cross-Language Disparities

The corpus passes today; these are divergences just outside its input ranges.
All are reachable with ordinary artifacts:

- **MEDIUM. Number formatting in error messages.** `pyRepr` (`errors.ts:25`) uses
  `String(value)` while Python uses `repr()`: `1e-7` → `1e-07` (Python) vs `1e-7` (JS);
  `1e20` → `1e+20` vs `100000000000000000000` (the exponential threshold is 1e16 in
  Python and 1e21 in JS); `inf`/`nan` vs `Infinity`/`NaN`. The committed `2.0` vs `2`
  limitation (ss-wbnm) is documented, but it is one instance of this whole family.
- **MEDIUM. The same divergence applies to the `values` block** of validation JSON
  (`json.dumps` at `cli.py:505` vs `JSON.stringify` at `settings.ts:27`) for any
  artifact whose frontmatter contains such numbers.
- **LOW. Empty or whitespace-only frontmatter.** Python yields `no_frontmatter` or
  `parse_error`; TypeScript’s `?? {}` fallback (`validate.ts:100`) treats it as a valid
  empty mapping and proceeds.
- **LOW. Unterminated frontmatter fence.** Python raises `FmFormatError` →
  `parse_error`; TypeScript returns no-fence → `no_frontmatter`. Same input, different
  error kinds.
- **LOW. `_augment_schema` merges an existing root `x-softschema` block
  (`compile.py:97-103`); `augmentSchema` replaces it (`compile.ts:44-47`).** Latent
  until a model emits one, then sidecars diverge.
- **LOW. Sorting collation.** Python `sorted()` orders by code point; JS `.sort()` by
  UTF-16 code unit. For `required` arrays or schema keys containing astral-plane
  characters, the canonical forms (and therefore `schema_sha256`) diverge.
  Exotic, but it is exactly the kind of edge an “exact parity” promise attracts; a
  comment plus a fixture would settle it.
- **LOW. Safe-integer sentinel stripping is semantic.** Both canonicalizers silently
  delete a user-authored bound of exactly ±9007199254740991 (`canonicalize.py:88-91`); a
  legitimate constraint disappears from the sidecar.
  Worth a documented caveat.
- **LOW. Error-message punctuation.** Python `repr()` single-quotes, TypeScript
  `JSON.stringify` double-quotes in several non-corpus messages (`generate`,
  `schema_view`/`schemaView`, `registry`, `models`), and Python says `got list` where
  TypeScript says `got object`.

### Packaging and Resources

- **HIGH. Wheel omits `docs/softschema-typescript-design.md`** (`pyproject.toml:71-87`)
  while `DOC_TOPICS` advertises the topic: `softschema docs typescript-design` from an
  installed wheel raises `FileNotFoundError` (and, via the missing CLI error boundary, a
  traceback). The npm package bundles it (`copy-resources.ts:20`); the two manifests have
  already drifted.
- **MEDIUM. npm resources omit `examples/movie_page/movie-page.schema.yaml`** which the
  wheel includes; harmless today (not a topic) but the same drift channel.
- **MEDIUM. Bundled `AGENTS.md` ships the tbd integration block** to package users via
  `softschema docs agents`; `publishing` is likewise maintainer-facing.
  Strip or drop (see Improvements item 8).
- No test in either package asserts that every `DOC_TOPICS` path resolves from the built
  artifact (the TypeScript standalone test covers some topics; the wheel gap above
  shipped through this hole).

## Testing Deficiencies

### Shared Input Edge Cases (Untested in Both Languages)

No tests exercise: CRLF line endings, BOM, empty frontmatter (`---\n---`), duplicate
YAML keys, anchors/aliases, NaN/Infinity and large/small floats, non-ASCII values (the
`ensure_ascii=False` choice that exists specifically for parity is untested), deeply
nested validation-error paths, unicode envelope keys, or non-UTF-8 files.
Several of these are exactly where the implementations already diverge (see above),
which is the strongest argument for adding them as a shared fixture corpus.

### Golden Corpus and Parity Machinery

- Error-normalization coverage is min-side only: `minItems`, `minimum`,
  `exclusiveMinimum`, `multipleOf`, `type`, `enum`, `required`, `additionalProperties`
  are exercised; `maxLength`, `maxItems`, `pattern`, and `exclusiveMaximum` templates
  are not.
- No pure-yaml scenario, no semantic-path (`--model`) scenario in either per-impl
  directory, and `docs spec` is elided to its first line, so bundled-content drift
  between packages would pass.
- The golden job runs Python 3.13 only; the pytest matrix covers 3.11-3.14 but never
  compares CLI bytes.
- The TypeScript corpus runs under Bun, never Node (design issue 4).
- There is no direct cross-implementation diff step (run both CLIs on the same input in
  one job and `diff` the outputs); parity is currently transitive through the committed
  golden files, which works but reports failures on whichever side runs second.

### Per-Language Gaps

- Python: none of the traceback bugs above have tests (they would have caught them); no
  test that all `DOC_TOPICS` resolve from a built wheel.
- TypeScript: `generate.ts` error paths (missing/unknown `kind`, missing `contract`,
  unterminated marker, `renderFieldList`, `renderVocab`) are uncovered; pure-yaml
  parse-error path uncovered; `skill --install` uncovered; `coverage.test.ts` is
  legitimate unit testing (not coverage gaming) but misnamed; the in-process CLI test
  stubs `process.stdout.write` globally rather than capturing output.
- The vacuous `"<version>" not in output` assertions (see Skill section).

## Prioritized Recommendations

The priorities below group findings by impact.
The execution sequence (quick fixes first, then the parity/test safety net, then the
major design changes, then remaining cleanups) is planned in
[plan-2026-06-10-softschema-review-remediation.md](../specs/done/plan-2026-06-10-softschema-review-remediation.md).

P1 (correctness and user-facing breakage):

1. Add CLI error boundaries in both languages (clean message, exit 2); fix
   `validate_artifact` to return structured failures on missing/unreadable files.
2. Ship `docs/softschema-typescript-design.md` in the wheel; add a both-sides test that
   every doc topic resolves from the built artifact.
3. Add the TypeScript `--help` epilog.
4. Enforce the spec’s `softschema:` block rules (unknown keys, and define “malformed
   contract”) in both implementations, with shared fixtures, or amend the spec.
5. Fix TypeScript exit-path hygiene: `process.exitCode`, EPIPE handlers, SIGINT.

P2 (design alignment):

6. Move envelope/binding inference into the libraries; resolve the pure-yaml envelope
   question in spec or code.
7. Implement the decided `status` semantics (optional teeth; see the decision under
   design issue 1) and align spec, guide, and playbooks.
8. Refresh stale docs for the TypeScript port (guide sections, python-design
   Accepted/Deferred and module table, public-readiness plan disposition, publishing.md
   present state).
9. Calibrate parity claims (content-identical sidecar with equal hash) and the README’s
   “unreasonably effective.”

P3 (parity hardening and tests):

10. Shared edge-case fixture corpus (numbers, unicode, malformed frontmatter, nested
    errors, max-side keywords); fix `pyRepr` number formatting and the empty-frontmatter
    divergence the fixtures will expose.
11. Run the TypeScript golden corpus under Node (the published runtime) as well as Bun
    in CI; keep golden scenarios as the same files for both CLIs wherever possible; add
    a direct cross-implementation diff job; run golden on the full Python matrix.
12. Version/format stamp on the skill marker (or delete the dead `<version>` path);
    TypeScript mirror drift test; atomic install writes; git-root awareness for
    `skill --install`.

P4 (polish): `--version` flags, shared doc-topic and resource manifests, Ajv caching,
typecheck `test/`, dead-code removal, the LOW/NIT items above.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
