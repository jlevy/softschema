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

- **`contract` vs `schema`, and why both:** the two metadata keys play different roles
  and the distinction is the heart of this design.
  - `contract` is the **stable, unified identifier** for the payload contract: a logical
    name (with the UpperCamelCase segment hinting at a Pydantic class, a Zod export, or
    a precompiled JSON Schema).
    It is *required* for a self-describing artifact and is the durable handle every
    binding mechanism keys on.
    It says *what* contract this is, not *where* the schema lives.
  - `schema` is an **optional, recommended pointer** to the concrete authoritative
    schema file. It says *where* (one way of saying where).
    It is recommended for self-validating artifacts but **never required**, because many
    applications resolve the schema out of band — a host registry, a build step, a
    company-wide convention, or some other application-specific mechanism — and
    reference it only through the `contract` ID. Those artifacts carry `contract` and
    omit `schema`, and that is fully conforming.

- **In-document binding** (new, optional): the metadata block gains the optional
  `schema` key.

  ```yaml
  softschema:
    contract: example.movies:MoviePage/v1
    schema: movie-page.schema.yaml   # optional; recommended for self-validating artifacts
    status: enforced
  ```

  With it, `softschema validate doc.md` needs no flags; without it, validation falls
  back to a flag, a registry binding, or a metadata-only check.
  Precedence (highest wins): `--schema` flag / explicit `schema=` argument > host
  registry binding (`Contract.schema_path` / `schemaPath`, library path only) >
  `softschema.schema` document metadata > none (metadata-only check).
  Host-controlled configuration outranks document-declared metadata on purpose: a
  document must not silently redirect a host’s validation to a schema the host did not
  choose. (This corrects the earlier draft, which put metadata above the registry; the
  review’s trust concern motivates the flip.)
  In the CLI there is no registry, so the chain collapses to `--schema` >
  `softschema.schema` > none, which is what gives a self-describing artifact its no-flag
  validation. The `--schema` flag is therefore an **optional override**: unnecessary when
  `softschema.schema` is present, but available to point validation at a different
  schema on a given run (a candidate revision, a stricter variant, or a schema for an
  artifact whose author omitted the key).
  Unknown-key rejection continues to apply (the known set becomes `contract`, `status`,
  `schema`).

- **API contract (settled for implementation).** The boundary is the same in both
  languages, golden-first:
  - The metadata type (`SchemaMetadata` in Python, the mirror in TypeScript) gains a
    `schema: str | None` / `schema?: string` field, parsed from `softschema.schema`. A
    present-but-empty or non-string `schema` is a malformed-metadata error, in the same
    family as a malformed `contract` or an unknown key (reported at metadata-parse time,
    not as `schema_missing`/`schema_invalid`, which are reserved for the resolved file).
  - `validate_artifact` / `validateArtifact` read `softschema.schema` and apply the
    precedence above, so the library gets no-flag binding too; the CLI is a thin
    wrapper, not a second code path.
  - `inspect` reports the `schema` pointer alongside `contract` and `status` (cheap, and
    makes the binding visible without validating).
  - Resolution in the reference CLIs: a metadata `schema` value must be a **relative**
    path (an absolute value is rejected — use `--schema` for arbitrary paths), resolved
    from the document’s directory; a path whose normalized resolution escapes **both**
    the document directory and the current working directory is rejected (the bounded
    resolution, so `../../etc/passwd`-style values cannot bind).
    A resolved path that is missing or unreadable is `schema_missing` (the out-of-bounds
    rejection also reports as `schema_missing`, with a message naming the bound); a
    resolved file that is not valid JSON Schema is `schema_invalid`. (Resolved in the
    0.2.0 pre-release review: the earlier draft said absolute paths were used as given,
    which contradicted the bound.)
  - Spec level: only that `schema`, when present, is a non-empty string.
    The bounded resolution is the reference behavior, not a conformance requirement (a
    host may resolve differently).

- **Resolution is a convention, not an enforced rule.** By convention the `schema` value
  is a path to the compiled schema *relative to the document that carries it* (the
  common case: the schema sits in the same folder or repository as the artifacts it
  validates). The reference CLIs resolve it that way, bounded to the document directory
  and the current working directory so a relative path cannot silently bind to an
  unrelated schema in a parent tree.
  But the spec **does not mandate a single resolution for every conforming consumer**:
  how the file is laid out and referenced is too situational across applications, so the
  relative-from-document rule is recommended (and is what the reference tools do), not a
  conformance requirement.
  The spec validates that `schema`, when present, is a non-empty string; it does not
  dictate that every host resolve it identically.

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

- **The spec is the normative source of the output contract; the renderers are tested
  against it** (not the other way around).
  For a language-neutral spec, “whatever `generate.py` emits” cannot be the definition,
  or parity drifts toward one implementation.
  The spec states, for each kind, the exact output so both renderers and any third party
  can be checked against it:
  - `enum_table`: a GFM table, columns `Field` then `Allowed values`; one row per
    enum-valued property; rows in the schema’s property order; values comma-space joined
    in schema order; a property whose enum includes `null` shows the non-null members
    only; `|` in a value is escaped.
  - `field_list`: one `-` bullet per top-level property in schema order: `` `name` `` —
    JSON type (the JSON Schema `type`, or `anyOf`/`$ref` rendered as a stable label),
    `required`/`optional`, then the property `description` (omitted, with no trailing
    dash, when absent).
  - `vocab`: the allowed values of the single property addressed by `pointer` (RFC
    6901), comma-space joined in schema order, on one line.
  - Every kind: equal inputs produce byte-equal output; an unknown `kind` is rejected
    rather than silently emitting a fallback; a missing/unreadable schema is an error.
- **Marker attribute rename (breaking, 0.2.0): `contract="path/to/schema.yaml"` →
  `schema="path/to/schema.yaml"`.** Today the generated-marker attribute that holds a
  *schema file path* is spelled `contract=` (`docs/softschema-spec.md:216`,`:230`,
  example READMEs), which directly contradicts the new terminology where `contract` is
  the logical payload ID and `schema` is the concrete file pointer.
  The attribute is renamed to `schema=` so one word means one thing everywhere.
  This is a hard migration (no dual-accept): both parsers/renderers, the spec examples,
  the movie-page README marker, and the goldens move together; an old
  `contract="...path..."` marker is rejected with a clear message pointing at the
  rename. (See Compatibility and Breaking Changes.)
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

- **frontmatter-format**: the `frontmatter-md` profile matches frontmatter-format’s
  YAML/Markdown (`---` delimited) style exactly — and only that style.
  The “exactly” is scoped to the Markdown `---` profile; frontmatter-format’s
  comment-style fences for other file types (HTML, Python, Rust, CSS, SQL) are
  explicitly out of scope here today, so the boundary cannot be misread as “every
  frontmatter-format file type.”
  The Python implementation consumes the `frontmatter-format` library; the TypeScript
  implementation implements the same `---` subset and is held to it by the golden
  corpus. Behavioral authority: where the implementations differ from
  frontmatter-format’s Markdown rules, frontmatter-format wins.
  This resolves `ss-eero` (non-mapping frontmatter must be rejected the way `fmf_read`
  does), and the fix is scoped **by entrypoint, not by intent**: every public surface
  that reads frontmatter must reject a non-mapping document — `validate`, `inspect`, the
  exported `readFrontmatter` parser, and the library validation path — with golden/test
  coverage for each, so one path cannot be fixed while another stays divergent.
- **sidematter-format**: the forward pointer for future per-document companion data (see
  design 6).
- **markform**: the shared marker mechanism note (see design 7).

## Compatibility and Breaking Changes

softschema is pre-1.0 and the affected surfaces are young, so the policy is simple and
deliberate: **a clean 0.2.0 break — no compatibility shims, no dual-accept, no
error-kind aliases, no migration paths.** Downstream consumers upgrade fully.
We do not invest in seamless migration; the value we provide instead is that **every new
or stricter check fails loudly with a clear, documented error** a human or agent can act
on. A clear failure is better than lenient acceptance: if a check is worth adding, an
artifact that violates it should be rejected with a message that says what is wrong and
how to fix it, not silently tolerated.
A downstream agent reading that error can upgrade the artifact or the code.

The table below is reference documentation of what changes and the clear error each
breaking surface produces (not a migration procedure):

| Surface | 0.1.x | 0.2.0 | What a violating input sees |
| --- | --- | --- | --- |
| Contract-ID grammar | any non-empty string accepted | grammar enforced (design 4), at metadata-parse time regardless of `status` | exit 2 with a diagnostic naming the malformed ID and the expected shape; the recommended form already passes |
| Metadata keys | `contract`, `status` | adds optional `schema`; unknown keys still rejected | additive; nothing breaks for existing docs |
| Validation error kinds | `schema_sidecar_missing`, `schema_sidecar_invalid` | `schema_missing`, `schema_invalid` (renamed, **no alias**) | a consumer branching on the old `kind` strings stops matching; the new strings are documented |
| Generated-marker attribute | `contract="...path..."` | `schema="...path..."` (renamed, hard) | the old attribute is rejected with a message pointing at the `schema=` rename |
| No-flag validation | `--schema` or registry required | `softschema.schema` binds with no flag | additive; nothing breaks |
| Library APIs | `validate_artifact`, `validateArtifact`, `compile_model`, `compileSchema` | unchanged signatures; metadata type gains a `schema` field | additive; existing calls compile unchanged |

The release note lists the breaking items and the clear error each produces, so an
upgrading consumer knows exactly what to fix.
That note, plus the errors themselves, is the whole of the “migration” story.

**Trust note (carried into the installed-user docs).** `--model module:Class` /
`--model path:export` imports and executes local code to build the validator, so it must
be used only with trusted models.
`--schema` (a compiled JSON Schema) executes nothing and is the safe, language-neutral
path for validating artifacts from an untrusted source.
The README/guide examples say this where they introduce `--model`.

## Implementation Plan

### Phase 1: Conventions and Docs (no validation behavior change)

- [ ] Write the naming convention into AGENTS.md and apply the softschema/"soft schema"
  sweep across all docs, SKILL.md, and CLI strings.
  Note: the sweep touches user-visible CLI output (bundled doc-topic titles, the
  skill-brief header), so the shared golden `inspect-and-docs.md` updates with it — a
  terminology diff, not a validation change.
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
  tests, design-doc table; no aliases — see Compatibility and Breaking Changes).
- [ ] Generated-marker attribute rename `contract="...path..."` → `schema="...path..."`
  per design 7 (both parsers/renderers, spec examples, movie-page README marker,
  goldens; old form rejected with a rename hint).
- [ ] TS frontmatter parser: reject non-mapping frontmatter per frontmatter-format
  authority across every entrypoint (`validate`, `inspect`, `readFrontmatter`, library;
  closes `ss-eero`; golden + unit coverage per entrypoint).
- [ ] Update the per-CLI support matrix in docs and `--help` text to match.

### Phase 3: Follow-through

- [ ] Re-render and re-verify everything derived (skill mirrors, generated sections,
  golden corpus on py/ts/ts-bun, cross-impl diff).
- [ ] Release as **0.2.0** (behavior changes: grammar enforcement, new metadata key,
  error-kind renames) with release notes; defer the sidematter-format work to its own
  bead.

## Testing Strategy

Phase 1 is prose plus the terminology sweep: lint, doc-footer checks, and the existing
golden corpus (with the `inspect-and-docs.md` terminology diff) prove no validation
behavior moved. Phase 2 follows the repo’s golden-first loop: shared scenarios before
code, both implementations ported, byte-identical output on py/ts/ts-bun plus the
cross-impl diff job.
The error-kind, metadata-key, and marker-attribute changes update existing scenarios;
their diffs are reviewed as the behavioral spec.

These outputs are stable and behavioral (no unstable values), so the goldens capture
them exactly. Shared scenario checklist for Phase 2 (each a golden unless noted):

- **Contract-ID grammar — accept:** bare `Name`; namespaced `ns:Name`; versioned
  `ns:Name/v1`; underscores in name; dotted namespace `a.b.c:Name`; a lowercase name
  (UpperCamelCase is advisory, asserted to pass).
- **Contract-ID grammar — reject (exit 2, clean diagnostic):** empty string;
  whitespace-only; whitespace around separators; empty namespace segment (`:Name`);
  repeated `:`; repeated `/`; empty version (`Name/`).
- **Metadata `schema` binding:** `softschema.schema` present → `validate` succeeds with
  **no** flags; `--schema` overrides `softschema.schema` (different schema wins);
  `inspect` reports the `schema` pointer; an unknown metadata key still rejects after
  `schema` joins the known set; a non-string/empty `schema` is a malformed-metadata
  error; a `schema` pointing at a missing file → `schema_missing`; a `schema` pointing
  at an invalid schema file → `schema_invalid`; a `..` path escaping the doc-dir/cwd
  bound is rejected.
- **Registry fallback (library unit tests, not CLI goldens):** a registered
  `Contract.schema_path` still resolves; the registry binding outranks
  `softschema.schema` per the precedence; an explicit `schema=` argument outranks both.
- **Error-kind rename:** every scenario emitting `schema_sidecar_*` now emits
  `schema_missing` / `schema_invalid`; no alias remains.
- **Generated-marker rename:** a block with the new `schema="..."` attribute renders;
  `generate --check` is byte-stable; a block still using `contract="...path..."` is
  rejected with the rename hint; one golden per kind (`enum_table`, `field_list`,
  `vocab`) pins the normative output (columns, ordering, escaping, optional/required,
  missing-description, pointer-failure).
- **Non-mapping frontmatter rejection (per entrypoint):** `validate`, `inspect`, the
  exported `readFrontmatter`, and the library path each reject a non-mapping document.

## Rollout Plan

One PR per phase (or Phase 1+2 stacked if review prefers); 0.2.0 ships after Phase 2
with both packages in lockstep as usual.

## Bead Map (tbd tracking)

The implementation is tracked under epic **`ss-20i3`** (these IDs are real beads; they
also live on the `tbd-sync` branch, so a checkout that has not fetched it will not show
them via `tbd show` — this list keeps the plan self-contained).
Phase ordering is enforced by blocker dependencies.

| Bead | Phase | Scope | Blocked by |
| --- | --- | --- | --- |
| `ss-ltxx` | 1 | Naming sweep (`Softschema` → `softschema`) — **done** | — |
| `ss-3oz6` | 1 | Prose-only “compiled schema” rename (docs) | — |
| `ss-oe39` | 1 | Spec restructure: terminology-first, genuine example, generated sections fully defined | — |
| `ss-dif0` | 1 | Consumption-model docs (dependency vs zero-install), design 0 | — |
| `ss-hrnm` | 2 | `docs example-schema` topic (+ resource manifests) | — |
| `ss-kkdl` | 1/2 | README installed-user rework + library surfaces + trust note | `ss-dif0`, `ss-hrnm` |
| `ss-5a4w` | 2 | Enforce contract-ID grammar (design 4) | `ss-oe39` |
| `ss-69f4` | 2 | `softschema.schema` metadata binding (design 5) | `ss-oe39` |
| `ss-brlt` | 2 | Generated-marker attribute rename `contract=` → `schema=` (design 7) | `ss-oe39` |
| `ss-m25c` | 2 | Error-kind rename `schema_sidecar_*` → `schema_missing`/`schema_invalid` (design 6) | `ss-3oz6` |
| `ss-7cbb` | 2 | Reject non-mapping frontmatter across every entrypoint (closes `ss-eero`) | `ss-eero` |
| `ss-15bv` | 3 | Re-verify derived surfaces, release 0.2.0 | all Phase 2 |

A deferred, out-of-epic bead tracks the future sidematter-format companion-data work
(design 6); it is not part of 0.2.0.

## Resolved Decisions

Every decision needed to start implementation is settled (maintainer direction and the
PR #13 review). Recorded here so the implementation beads inherit the final shape:

- **`schema` key is recommended, not required.** A self-describing artifact must carry
  `contract`; `schema` is an optional, recommended pointer.
  Artifacts that resolve the schema out of band (registry, build step, company
  convention) carry `contract` alone and are fully conforming.
  See Design 5.
- **`--schema` is an optional override, not the primary path.** When `softschema.schema`
  is present, validation needs no flag; `--schema` exists to point a given run at a
  different schema. Precedence (highest wins): `--schema` flag / explicit `schema=` arg >
  host registry binding (`Contract.schema_path`, library only) > `softschema.schema`
  metadata > none. Host config outranks document metadata so a document cannot redirect a
  host’s validation (see Design 5).
- **Metadata key name is `schema`** (not `schema_path`): it reads better in YAML and
  matches the `--schema` flag.
- **Relative-from-document resolution is a convention, not a conformance rule.** The
  reference CLIs resolve `schema` relative to the document (bounded to doc-dir + cwd),
  but the spec only requires that `schema`, when present, be a non-empty string.
- **Error-kind rename targets are `schema_missing` / `schema_invalid`, with no alias**
  (clean 0.2.0 break; see Compatibility and Breaking Changes).
- **Contract-ID grammar is enforced at metadata-parse time regardless of `status`** (it
  is cheap to comply and the recommended form already passes).
  UpperCamelCase stays advisory.
- **Generated-marker attribute renames `contract=` → `schema=`** (hard migration; see
  Design 7 and Compatibility and Breaking Changes).
- **Heading style: the lowercase brand stays lowercase even in Title Case headings**
  (“softschema Spec”), a documented exception — already applied in the Phase 1 sweep.
- **Backward compatibility: a clean 0.2.0 break, no shims or aliases; clear documented
  errors instead of migration paths** (see Compatibility and Breaking Changes).
- **`softschema.envelope` joins the metadata block** (0.2.0 pre-release review,
  maintainer decision): an optional declared envelope key, so multi-key artifacts are
  fully self-describing and validate with zero flags.
  The metadata quartet is `contract` / `schema` / `envelope` / `status`. Precedence
  mirrors `schema` and keeps host-over-document: `--envelope` flag > registry
  `envelope_key` > `softschema.envelope` > single-key inference.
  A declared-but-absent envelope key is `envelope_mismatch`.
- **Metadata `schema` paths are relative-only in the reference CLIs** (same review):
  absolute values are rejected with a pointer to `--schema`; see the API contract in
  Design 5.

## Open Questions

None block implementation.
All drafting questions above are now settled; if review reopens any (for example
registry-vs-metadata precedence, or a softer migration than a hard break), that item
returns here and its Phase 2 bead waits on it.

## References

- Maintainer feedback (this plan’s Background restates it).
- PR #13 senior-engineering review (maintainer): drove the decision reconciliation, the
  generated-marker rename, the Compatibility and Breaking Changes section, the schema-
  linkage API contract, the golden checklist, the entrypoint-scoped frontmatter fix, and
  the normative generated-section output.
- [Full engineering review](../../reviews/review-2026-06-10-softschema-full-eng-review.md)
  and [remediation plan](plan-2026-06-10-softschema-review-remediation.md) (complete).
- Reference repos reviewed in `attic/`: jlevy/markform (`docs/markform-spec.md`),
  jlevy/sidematter-format (`README.md`, `src/sidematter_format/`),
  jlevy/frontmatter-format (`README.md`, `src/frontmatter_format/`).
- `ss-eero` (TS non-mapping frontmatter parity), folded into Phase 2.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
