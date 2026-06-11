# Feature: softschema Terminology, Spec Clarity, and Schema Linkage

**Date:** 2026-06-11 (last updated 2026-06-11)

**Author:** Claude Code, from maintainer feedback by Joshua Levy

**Status:** Draft

## Overview

A holistic cleanup of the project’s terminology, documentation structure, and the
schema-linkage story, driven by a round of maintainer feedback on the 0.1.4 build.
The feedback items are individually small, but they share root causes: terminology that
was never pinned down (the package vs the practice; “sidecar”; envelope words used
before they are defined), docs written from the repo-developer’s seat instead of the
installed user’s, and a schema-linkage model that the spec gestures at but never makes
operational. This plan restates the challenges, then proposes coordinated fixes rather
than point edits, informed by a source review of three related formats by the same
maintainer (markform, sidematter-format, frontmatter-format; checked out under
`attic/`).

## Goals

- One consistent naming convention: `softschema` (lowercase) for the package/CLI/spec
  implementation, “soft schema(s)” (plain English) for the practice.
- A spec a first-time reader can follow top to bottom: terms defined before use, one
  genuine end-to-end example, and a complete definition of every feature it names
  (especially generated sections).
- A clear, operational schema-linkage story: JSON Schema as the canonical
  language-neutral contract artifact, Pydantic/Zod as sources that compile to it, an
  explicit way to bind an artifact to its schema, and a documented per-CLI support
  matrix.
- Docs written for installed users, not repo developers, that make the consumption
  choice explicit: pin softschema as a dependency for projects, CI gates, and library
  use; reach for zero-install (`uvx`/`npx`) for ad-hoc checks and agent bootstrap.
  Repo-developer workflows stay in development docs.
- Terminology that does not collide with the maintainer’s other formats: “sidecar”
  reserved for sidematter-format-style companions, and explicit compatibility notes for
  frontmatter-format and markform.

## Non-Goals

- Implementing sidematter-format discovery (future work; this plan only reserves the
  terminology and adds a forward pointer).
- Adopting markform as a dependency or emitting markform field tags (different layer:
  markform is an interactive form runtime; softschema is schema validation).
  Alignment stays informal (shared HTML-comment-tag mechanism, namespaced markers).
- New validation features beyond the linkage and grammar items below.

## Background: The Challenges, Restated

The maintainer’s feedback, in this plan’s own words, with the underlying causes:

1. **The name is used inconsistently.** Docs say “Softschema” (capitalized) for the
   tool, “soft schemas” for the practice, and sometimes blur the two.
   There was never a stated convention, so each doc improvised.
   Decision (made): `softschema`, always lowercase, names the package, CLI, and this
   repo’s spec; “soft schema(s)”, two words and ordinary English casing, names the
   general practice.

2. **The README straddles two audiences.** The Python walkthrough says `uv sync` and
   `uv run softschema ...` and references `examples.movie_page.model:MoviePage`, a
   module path that only resolves inside this repo; the TypeScript walkthrough next to
   it correctly uses `npx softschema@latest`. An installed user following the Python
   section hits a wall.
   Root cause: the README was written when the repo and the package were the same
   audience. The fix is not swapping one command: the whole quickstart must be reframed
   around zero-install runners (`uvx` / `npx`), with repo-relative workflows moved to
   development docs, and a separate, explicit “use as a library” surface.

3. **The spec uses its vocabulary before defining it.** The Artifact Profiles section
   (third in the document) already talks about “envelope”, “metadata”, and “payload”;
   Metadata and Envelope Selection only define those terms two and three sections later.
   The dense pure-yaml paragraph is unreadable on first contact for exactly this reason.
   The spec needs a Terminology section up front, an annotated end-to-end example, and
   the profile text rewritten in defined terms.

4. **The spec’s example is not genuine.** The Frontmatter Artifact Shape example’s body
   is the placeholder “Reader-facing prose body.”
   — which hides the most important property of the format: the body normally *overlaps*
   with the YAML (sometimes restating it as prose or a table), and how much it overlaps
   is situational. The repo already has the genuine artifact
   (`examples/movie_page/spirited-away.md`, with real prose plus a Movie Details table);
   the spec should embed a faithful trimmed version of it.
   House rule to state: examples are genuine, even when simple — no placeholders.

5. **Generated sections are named but not defined.** The spec lists `enum_table`,
   `field_list`, and `vocab` without saying what any of them renders.
   The feature also leaks into first-contact examples, where it confuses.
   It needs: removal from introductory examples, a complete definition of each kind
   (input, deterministic output shape, a rendered example), full marker grammar, and
   explicit framing as an optional advanced feature for regenerating pieces of Markdown
   from the schema/YAML when a workflow earns it.

6. **Possible alignment with markform.** markform (reviewed at `attic/markform`) binds
   typed, fillable fields to Markdown using HTML comment tags
   (`<!-- field kind="string" id="name" -->` … `<!-- /field -->`), including `table`
   fields with typed columns, and supports YAML/JSON/Markdown round-trips.
   softschema’s generated markers already use the same mechanism (HTML comment tags with
   `key="value"` attributes) with a `softschema:` namespace.
   Assessment: the two serve different layers — markform is an interactive form data
   model and editing API; softschema’s generated sections are read-only projections of a
   schema. Full adoption would import a form runtime for no validation benefit.
   The right alignment is informal and cheap: document that the marker mechanism follows
   the same HTML-comment-tag convention as markform, keep the `softschema:` namespace to
   avoid collisions, and keep the attribute syntax (`key="value"`) identical so the
   files feel like one family.

7. **Contract IDs are under-specified.** Today only “non-empty string” is enforced; the
   `namespace:UpperCamelCaseName/version` form is purely advisory.
   Direction: enforce the *shape* (a real grammar), make the namespace segment optional,
   keep UpperCamelCase a recommendation, and say plainly that the name may correspond to
   a Pydantic class, a Zod export, or a precompiled JSON Schema — all equally valid.

8. **The schema-linkage story is incomplete.** The spec insists a contract ID is not
   tied to a schema file, and that schema files “are not normally referenced from
   authored document metadata” — but then the only ways to validate are a `--schema`
   flag or a host-registry binding, and nothing explains the end-to-end workflow (define
   a model → produce the schema → bind artifacts to it → validate in CI). Direction:
   lean JSON-Schema-first.
   The compiled JSON Schema is the canonical, language-neutral contract artifact;
   Pydantic and Zod are *sources* that compile to it (provably identically — the
   conformance machinery already guarantees an equal `schema_sha256`). Add an explicit,
   optional in-document binding so a soft schema header can point at its authoritative
   schema, and document the per-CLI support matrix (which CLI loads Pydantic, which
   loads Zod, both load JSON Schema).

9. **“Sidecar” is the wrong word and collides with sidematter-format.** In
   sidematter-format (reviewed at `attic/sidematter-format`), a sidecar is a companion
   file *paired with a specific document* (`doc.md` → `doc.meta.yml`, `doc.assets/`).
   softschema’s compiled JSON Schema is nothing like that: one schema serves many
   artifacts; you would never pair a schema with every record.
   Direction: stop calling it a sidecar anywhere (docs, spec section title, *and* the
   public error kinds `schema_sidecar_missing` / `schema_sidecar_invalid`); call it the
   **compiled schema**. Reserve "sidecar"/"sidematter" for a possible future
   sidematter-format alignment, recorded as a forward pointer only.

10. **frontmatter-format compatibility should be explicit.** The Python implementation
    already depends on `frontmatter-format` (it reads artifacts via `fmf_read`), so
    compatibility is real on that side by construction.
    The TypeScript implementation hand-parses frontmatter and supports only the Markdown
    `---` style (frontmatter-format also defines comment-style fences for
    HTML/Python/Rust/CSS/SQL files).
    That boundary should be documented: the `frontmatter-md` profile *is*
    frontmatter-format’s YAML/Markdown style; other styles are out of scope today.
    One real divergence found in review: frontmatter-format raises on a non-mapping
    frontmatter while the TS parser passes it through (tracked as `ss-eero`) — under
    this plan frontmatter-format’s behavior is authoritative and the TS side must match.
    The maintainer maintains all of these projects and wants the engineering kept
    consistent.

11. **The consumption model is undecided and undocumented.** softschema can be used two
    ways, and the docs never say which to reach for: (a) **pinned as a dependency** of a
    project (a Python dev dependency / `uv tool install`, or an npm `devDependency`), or
    (b) **zero-install** via `uvx softschema@<v>` / `npx softschema@<v>`. These are not
    interchangeable, and conflating them is part of why the README felt wrong (challenge
    2): library usage (`import`) is only possible as a dependency, and a reproducible CI
    gate wants a pinned dependency, while an agent bootstrapping in a fresh container or
    a human running a one-off check wants zero-install.
    The docs should make the choice explicit and steer each audience to the right one
    rather than leaving every example in one mode.

## Design

### 0. Consumption model: pinned dependency vs zero-install

Two supported ways to consume softschema, both first-class, with a clear default for
each audience. This decision shapes the README, `docs/installation.md`, the guide’s CI
playbook, and the skill’s runner ladder, so it is settled first.

**(a) Pinned as a dependency — the default for projects, CI, and library use.** A
project adds softschema to its lockfile at a fixed version and invokes the local binary
(or imports the library).
This is the right choice whenever softschema runs more than once or its result must be
reproducible:

- **Reproducible and auditable.** The version is recorded in `uv.lock` /
  `package-lock.json` / `bun.lock`; every run, local and CI, uses the same bytes, and
  the supply-chain age gate applies once at lock time, not on every invocation.

- **Fast and offline.** No per-call resolution or download; the binary is already on
  disk. Matters for tight CI loops and editor/agent feedback.

- **The only way to use the library.** `from softschema import validate_artifact` /
  `import { validateArtifact } from "softschema"` requires the package installed; you
  cannot import from a `uvx`/`npx` runner.

  Recipes (pinned):
  - Python: `uv add --dev softschema==X.Y.Z` (a dev dependency), or
    `uv tool install softschema@X.Y.Z` (a user tool); invoke `uv run softschema ...` or
    the tool binary.
  - TypeScript/Node: `npm i -D softschema@X.Y.Z` (or `bun add -d`); invoke via
    `npx softschema ...` (resolves the local pinned copy), `bunx`, or
    `node_modules/.bin/softschema`.

**(b) Zero-install (`uvx` / `npx`) — the default for ad-hoc and agent bootstrap.** No
project setup; the runner fetches and runs on demand.
The right choice when there is nothing to install into, or nothing to reuse:

- **One-off checks** ("does this file validate?") with no project to add a dependency
  to.
- **Ephemeral / cloud agents** and fresh containers where nothing persists, where the
  agent skill bootstraps the CLI on first use.
- **Trade-offs to state plainly:** a cold-start fetch on first call, a network
  requirement, and — critically — an **unpinned** runner (`uvx softschema@latest`,
  `npx softschema@latest`) re-resolves to the newest release on every run, which
  bypasses any consumer-side cool-off.
  For repeatable use, pin the runner too (`uvx softschema@X.Y.Z`,
  `npx -y softschema@X.Y.Z`).

**The recommendation, stated once and reused:** *if softschema runs more than once, or
in CI, or you import it — pin it as a dependency.
For a quick one-off or an agent bootstrapping with nothing installed — use a
zero-install runner, pinned where the result must be repeatable.* The skill’s runner
ladder (local binary → `uvx`/`npx`) already encodes “prefer an installed copy, fall back
to zero-install,” which matches this recommendation; the docs make it explicit for
humans.

**Reconciling `@latest` in the skill (open question 5 below):** the skill text uses
`@latest` for the agent-bootstrap case, justified by the repo’s release-age cool-off.
That stays for the *bootstrap* path, but the consumer-facing README/installation docs
and the CI playbook recommend a **pinned** dependency or runner, because a project’s
reproducibility is the project’s responsibility, not the publisher’s cool-off.
Both audiences get the guidance that fits them, in the doc that fits them.

How this threads through the rest of the plan: `docs/installation.md` gains a short
decision table (dependency vs zero-install, when to use each) and the recipes above; the
README quickstart leads with the zero-install try-it path and links to “pin it as a
dependency” + the library surfaces (design 2); the guide’s “Validate In CI” playbook is
rewritten to pin softschema as a consumer dependency rather than the current
repo-relative `uv run`.

### 1. Naming convention (write it down, then sweep)

- Add the rule to `AGENTS.md` doc rules and the spec’s front matter: **`softschema`**
  (lowercase, code-styled where it names the CLI/package) for the implementation;
  **“soft schema(s)”** for the practice.
  The lowercase brand is a deliberate exception to Title Case in headings ("softschema
  Spec", “The softschema Guide”).
- Sweep README, spec, guide, both design docs, SKILL.md, AGENTS.md, package READMEs, and
  CLI help strings. Code identifiers (`SchemaStatus` etc.)
  are unaffected.

### 2. README and doc-surface rework (installed-user first)

- Quickstart: parallel `uvx softschema@latest ...` and `npx softschema@latest ...`
  blocks, runnable from any directory.
  To make the validate example genuinely runnable outside the repo, add a
  `docs example-schema` topic (the compiled movie schema is already bundled in both
  packages but unaddressable); the quickstart becomes: print the example artifact and
  schema to local files, then validate them.
- A short “Use as a Library” section in the README (install lines plus a pointer); the
  per-package READMEs (`packages/python/README.md`, `packages/typescript/README.md`)
  gain the actual library examples (register a contract, `validate_artifact` /
  `validateArtifact`, `compile_model` / `compileSchema`).
- Every `uv sync` / `uv run` workflow moves to `docs/development.md` (repo developers
  only); the README states that assumption explicitly nowhere — because it no longer
  makes it.

### 3. Spec restructure (terminology first, genuine example)

New section order:

1. Scope; Conformance Language.
2. **Terminology** (new): one- or two-line definitions of *artifact*, *frontmatter*,
   *metadata block* (`softschema:`), *payload*, *envelope* (and envelope key),
   *contract* and *contract ID*, *model* (Pydantic/Zod source), *compiled schema* (JSON
   Schema), *profile*, *status*, *generated section* — followed by one small annotated
   artifact showing which part is which.
3. Artifact Profiles, rewritten in the defined terms; the pure-yaml rules become a short
   list with its own four-line example instead of the current dense paragraph.
4. Frontmatter Artifact Shape, embedding a faithful trimmed `spirited-away.md`: real
   prose body that restates the Oscar context and a genuine Movie Details table
   overlapping the YAML — explicitly discussed as the normal, situational overlap.
   No generated markers here.
5. Metadata (gains the optional `schema` key; see design 5).
6. Envelope Selection, with a worked multi-key example (the `title:` + `movie:` case).
7. Contract IDs (see design 4).
8. Status Values; Source of Truth.
9. **Compiled Schemas** (renamed from “Schema Sidecars”; see design 6).
10. Validation Expectations.
11. Generated Sections, fully defined (see design 7).
12. **Compatibility and Related Formats** (new; see design 8).
13. Out of Scope.

### 4. Contract ID grammar (enforced shape, advisory style)

Enforced grammar (validated by both implementations, golden-first):

```text
contract-id = [ namespace ":" ] name [ "/" version ]
namespace   = segment *( "." segment )      ; segment = [a-z0-9_]+
name        = [A-Za-z_][A-Za-z0-9_]*
version     = [A-Za-z0-9_.-]+
```

No whitespace; at most one `:`; at most one `/`; no empty segments.
Advisory (recommended, never enforced): UpperCamelCase names; reverse-DNS or a short
product tag for the namespace; short versions (`v1`, `1.0`). The spec states explicitly
that the name may correspond to a Pydantic class, a Zod export, or a precompiled JSON
Schema, and is never required to be an import path.

### 5. Schema linkage (JSON-Schema-first, explicit binding)

- **Canonical artifact**: the compiled JSON Schema (YAML or JSON) is the
  language-neutral contract artifact.
  Pydantic and Zod are sources; `softschema compile` produces the identical canonical
  schema from either (already enforced by `schema_sha256` conformance).

- **In-document binding** (new, optional): the metadata block gains a `schema` key — a
  relative path to the compiled schema, resolved from the document’s directory (relative
  paths only; the bounded resolution prevents surprising binds):

  ```yaml
  softschema:
    contract: example.movies:MoviePage/v1
    schema: movie-page.schema.yaml
    status: enforced
  ```

  With it, `softschema validate doc.md` needs no flags.
  Precedence: `--schema` flag > `softschema.schema` metadata > registry `schema_path` >
  none (metadata-only check).
  Unknown-key rejection continues to apply (the known set becomes `contract`, `status`,
  `schema`).

- **Workflow documentation**: the guide’s validation playbook becomes the canonical loop
  — author the model (Pydantic or Zod) → `softschema compile` → commit the compiled
  schema → bind artifacts via `softschema.schema` (or CI flags) → `softschema validate`
  everywhere, plus the `compile --check` drift gate.

- **Per-CLI support matrix** (spec or design docs, plus `--help`):

| Capability | Python CLI | TypeScript CLI |
| --- | --- | --- |
| `--schema` (compiled JSON Schema) | yes | yes |
| `--model` Pydantic (`module:Class`) | yes | no |
| `--model` Zod (`path:export`) | no | yes |
| `compile` source | Pydantic | Zod |
| Compiled output | identical canonical schema, equal `schema_sha256` | same |

### 6. Retire “sidecar” for the compiled schema

- Prose: “schema sidecar” → “compiled schema” everywhere (spec section, guide, README,
  design docs, golden README, code comments).
- Behavior (golden-first): rename the public error kinds `schema_sidecar_missing` →
  `schema_missing` and `schema_sidecar_invalid` → `schema_invalid`; update the
  design-doc kind table, goldens, and tests in both implementations.
- The spec’s “data sidecar” paragraphs are replaced by a forward pointer in the new
  Compatibility section: a future version may adopt sidematter-format (`doc.meta.yml` /
  `doc.assets/` discovery) for per-document companion data; not specified now.
  Tracked as a deferred bead.

### 7. Generated sections, fully specified

- Each kind gets a normative definition with a rendered example:
  - `enum_table`: one GFM table row per enum-valued property in the compiled schema
    (columns: Field, Allowed values), in deterministic order.
  - `field_list`: one bullet per top-level property: name, JSON type, required marker,
    description.
  - `vocab`: the allowed values of the single field addressed by `pointer` (RFC 6901),
    as a comma-separated list.
    The reference renderers (`generate.py` / `generate.ts`) are the source of truth; the
    spec documents exactly what they emit.
- Marker grammar specified completely: attribute syntax (`key="value"`, double quotes),
  the open/close pair on their own lines, no nesting, unknown attributes rejected, body
  fully generator-owned.
- Framing: an explicitly optional, advanced feature — useful when a workflow needs
  pieces of Markdown regenerated from the schema (vocabulary tables in runbooks); never
  part of the basic artifact shape, and absent from all introductory examples.
- markform: note (in Compatibility) that the marker mechanism intentionally matches
  markform’s HTML-comment-tag convention with a `softschema:` namespace; no formal
  dependency in either direction.

### 8. Compatibility and Related Formats (new spec section)

- **frontmatter-format**: the `frontmatter-md` profile is frontmatter-format’s
  YAML/Markdown style, exactly.
  The Python implementation consumes the `frontmatter-format` library; the TypeScript
  implementation implements the same Markdown-style subset and is held to it by the
  golden corpus. Comment-style fences for other file types (HTML, Python, Rust, CSS, SQL)
  are defined by frontmatter-format and out of scope here today.
  Behavioral authority: where the implementations differ from frontmatter-format’s
  Markdown rules, frontmatter-format wins — which resolves `ss-eero` (the TS parser must
  reject non-mapping frontmatter the way `fmf_read` does).
- **sidematter-format**: the forward pointer for future per-document companion data (see
  design 6).
- **markform**: the shared marker mechanism note (see design 7).

## Implementation Plan

### Phase 1: Conventions and Docs (no behavior change)

- [ ] Write the naming convention into AGENTS.md and apply the softschema/"soft schema"
  sweep across all docs, SKILL.md, and CLI strings.
- [ ] Restructure the spec per design 3 (Terminology section, annotated example,
  rewritten profiles, genuine trimmed spirited-away example, worked envelope example);
  fully specify generated sections per design 7.
- [ ] Add the Compatibility and Related Formats section (frontmatter-format,
  sidematter-format pointer, markform note).
- [ ] Prose-only “compiled schema” rename across docs (error-kind renames wait for Phase
  2).
- [ ] Consumption-model docs per design 0: a dependency-vs-zero-install decision table
  plus pinned recipes in `docs/installation.md`; the guide’s “Validate In CI” playbook
  rewritten to pin softschema as a consumer dependency; the recommendation wording
  reused (not re-derived) in the README.
- [ ] README rework per design 2 (zero-install try-it quickstart that links to “pin it
  as a dependency” and the library surfaces, dev workflows moved out); library examples
  into the per-package READMEs; guide playbooks updated to the JSON-Schema-first
  workflow and renamed terminology.

### Phase 2: Behavior (golden-first, both implementations)

- [ ] `docs example-schema` topic (+ resource manifests) so the quickstart is runnable
  anywhere.
- [ ] Contract-ID grammar enforcement per design 4 (shared golden scenarios; clean
  exit-2 diagnostics).
- [ ] `softschema.schema` metadata binding per design 5 (precedence chain, bounded
  relative resolution, unknown-key set update, golden scenarios for bound validate with
  no flags).
- [ ] Error-kind renames `schema_missing` / `schema_invalid` per design 6 (goldens,
  tests, design-doc table).
- [ ] TS frontmatter parser: reject non-mapping frontmatter per frontmatter-format
  authority (closes `ss-eero`; golden scenario).
- [ ] Update the per-CLI support matrix in docs and `--help` text to match.

### Phase 3: Follow-through

- [ ] Re-render and re-verify everything derived (skill mirrors, generated sections,
  golden corpus on py/ts/ts-bun, cross-impl diff).
- [ ] Release as **0.2.0** (behavior changes: grammar enforcement, new metadata key,
  error-kind renames) with release notes; defer the sidematter-format work to its own
  bead.

## Testing Strategy

Phase 1 is prose: lint, doc-footer checks, and the existing golden corpus prove no
behavior moved. Phase 2 follows the repo’s golden-first loop: shared scenarios before
code, both implementations ported, byte-identical output on py/ts/ts-bun plus the
cross-impl diff job.
The error-kind and metadata-key changes update existing scenarios; their diffs are
reviewed as the behavioral spec.

## Rollout Plan

One PR per phase (or Phase 1+2 stacked if review prefers); 0.2.0 ships after Phase 2
with both packages in lockstep as usual.

## Open Questions

- Metadata key name: `schema` (proposed) vs `schema_path`? `schema` reads better in YAML
  and matches the `--schema` flag.
- Error-kind rename targets: `schema_missing` / `schema_invalid` (proposed) — confirm
  before goldens are rewritten.
- Contract-ID grammar: enforce everywhere (proposed: yes, it is cheap to comply) or only
  warn under `soft` status?
- Heading style for the lowercase brand: “softschema Spec” as a documented Title Case
  exception (proposed) vs renaming the docs ("The softschema Spec").

## References

- Maintainer feedback (this plan’s Background restates it).
- [Full engineering review](../../reviews/review-2026-06-10-softschema-full-eng-review.md)
  and [remediation plan](plan-2026-06-10-softschema-review-remediation.md) (complete).
- Reference repos reviewed in `attic/`: jlevy/markform (`docs/markform-spec.md`),
  jlevy/sidematter-format (`README.md`, `src/sidematter_format/`),
  jlevy/frontmatter-format (`README.md`, `src/frontmatter_format/`).
- `ss-eero` (TS non-mapping frontmatter parity), folded into Phase 2.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
