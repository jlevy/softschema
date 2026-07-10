---
title: Adjacent Schema and Document Systems
description: Primary-source comparison of content pipelines, structured document formats, and configuration languages adjacent to softschema, with strategic product decisions.
author: Joshua Levy with Codex
---
# Research: Adjacent Schema and Document Systems

**Date:** 2026-07-09

**Author:** Joshua Levy with Codex

**Status:** Complete

## Overview

softschema gives Markdown artifacts a strict, language-neutral contract without turning
their narrative body into a database, template language, or program.
Its native artifact keeps authoritative values in YAML frontmatter, preserves the
Markdown body as prose, and uses JSON Schema as the portable validation boundary.

Several established systems solve neighboring problems.
Astro content collections and Contentlayer turn content into application data.
MDX, Markdoc, and Jupyter add executable or structured body semantics.
CUE, Dhall, Nickel, and Pkl make configuration programmable or constrainable.
This brief compares those systems to identify capabilities softschema should borrow,
integration boundaries it should expose, and complexity it should keep out of the core.

## Questions to Answer

1. Which adjacent systems offer capabilities that materially improve softschema?
2. How do they compare on ergonomics, prose fidelity, portability, executable-code risk,
   tooling, agent usability, migration cost, and offline behavior?
3. Which ideas belong in softschema core, in optional adapters, or outside the product?
4. What strategic choices preserve flexibility without weakening the artifact contract?

## Scope

The research covers current official documentation available on 2026-07-09 for:

- content pipelines: Astro content collections and Contentlayer;
- structured or executable documents: MDX, Markdoc, and Jupyter notebooks; and
- configuration languages: CUE, Dhall, Nickel, and Pkl.

The evaluations are qualitative inferences from documented capabilities, not performance
benchmarks.
“Executable-code risk” means the risk introduced when processing an untrusted
artifact through its normal toolchain; it is not a claim about implementation
vulnerabilities. “Offline” assumes the runtime and ordinary dependencies are already
installed. Network-backed loaders, imports, packages, and data sources are called out
separately.

## Executive Conclusion

No reviewed system is a direct substitute for softschema because each owns a different
layer:

- Astro and Contentlayer are application content pipelines.
  Astro offers the strongest model for authoring ergonomics, but both couple contracts
  to a JavaScript application build.
  Contentlayer’s official repository now states that the project is no longer
  maintained, illustrating the lifecycle cost of framework-coupled infrastructure.
- MDX, Markdoc, and Jupyter own body semantics.
  MDX and Jupyter deliberately execute code; Markdoc offers a more controlled AST and
  registered-function model.
  All three go beyond softschema’s body-agnostic contract boundary.
- CUE, Dhall, Nickel, and Pkl are configuration languages.
  They provide valuable validation, composition, import, and tooling ideas, but adopting
  any one as the canonical contract language would reduce portability and make prose
  authoring harder.

The strategic direction should remain **strict values, inert prose, portable schema**.
softschema should improve framework-neutral ergonomics around that boundary: typed host
APIs, positioned diagnostics, editor schema associations, batch and watch workflows, and
offline schema bundles.
Optional host adapters may extract frontmatter or accept values from another system, but
core validation should never compile a document body, run a notebook, or evaluate a
configuration language.

## Findings

### Content pipelines

#### Astro content collections

Astro’s content collections load local Markdown, MDX, Markdoc, YAML, TOML, or JSON, and
can also load remote data.
A collection can declare a Zod schema for validation, inferred types, editor completion,
and references between entries.
Build-time collections are cached and exposed through query APIs; live collections can
fetch remote data at runtime.
Entries preserve raw body content and can be rendered through Astro’s content APIs.
These capabilities make Astro a strong benchmark for in-framework authoring and feedback
loops. See the
[content collections guide](https://docs.astro.build/en/guides/content-collections/) and
[`astro:content` API](https://docs.astro.build/en/reference/modules/astro-content/).

The tradeoff is ownership.
The loader, schema, query model, generated types, and renderer are part of an
Astro/TypeScript build.
Markdown files remain portable, but the collection contract and application behavior are
not a language-neutral artifact interface.
Remote and live loaders also make offline behavior dependent on the selected source.

**Lesson for softschema:** match the fast feedback, completion, typed access, and batch
collection ergonomics without making an application framework the contract authority.

#### Contentlayer

Contentlayer preprocesses content into validated, type-safe application data.
Its official documentation emphasizes transforming Markdown or MDX into JSON and
importing generated data from JavaScript or TypeScript.
The documented source is the local filesystem, and the prominent integration is Next.js.
See the [Contentlayer overview](https://contentlayer.dev/),
[documentation](https://contentlayer.dev/docs), and
[concepts](https://contentlayer.dev/docs/concepts-ac167d19).

The maintenance status changes the strategic assessment.
The [official repository](https://github.com/contentlayerdev/contentlayer) states that
Contentlayer is no longer maintained because of lost funding.
Its latest official release is
[0.3.4 from June 2023](https://github.com/contentlayerdev/contentlayer/releases/tag/v0.3.4).
The design remains useful evidence for generated types and content-to-data workflows,
but it is not a prudent dependency or integration target for new core functionality.

**Lesson for softschema:** generated, typed consumption is valuable; a portable
committed contract and interchangeable runtimes are safer than a generated data layer
tied to one framework’s release cycle.

### Structured and executable documents

#### MDX

MDX combines Markdown with JSX, JavaScript expressions, and ESM imports or exports.
It is excellent for component-rich React documentation, but the artifact is a program
that must be compiled and evaluated.
MDX uses CommonMark by default, with plugins for features such as GitHub Flavored
Markdown. Frontmatter is not built in; the official guide recommends a plugin or ESM
exports, and notes that exports are not automatically typed.
See [What is MDX?](https://mdxjs.com/docs/what-is-mdx/) and the
[frontmatter guide](https://mdxjs.com/guides/frontmatter/).

MDX is therefore a poor core format for untrusted, cross-language artifacts.
A syntax error can break compilation, JavaScript can perform arbitrary effects allowed
by the host, and portability depends on the JSX component and bundler environment.

**Lesson for softschema:** an MDX host may validate parsed frontmatter through
softschema before compilation, but softschema must not compile or execute MDX and must
not treat ESM exports as artifact metadata.

#### Markdoc

Markdoc is a CommonMark superset with tags, annotations, variables, functions, and an
AST transformation and rendering pipeline.
It validates syntax and lets host-defined node or tag schemas validate content and
attributes. Unlike MDX, a document can invoke only the functions and tags registered by
the host; the document does not contain arbitrary JavaScript syntax.
See the [syntax](https://markdoc.dev/docs/syntax),
[tags](https://markdoc.dev/docs/tags), and
[validation](https://markdoc.dev/docs/validation) documentation.

Markdoc deliberately does not define a frontmatter data format.
The host parses the raw frontmatter using YAML, TOML, JSON, or another parser and passes
it into Markdoc as a variable.
That boundary is documented in the
[frontmatter guide](https://markdoc.dev/docs/frontmatter).

Markdoc is safer and more controllable than MDX for rich publishing, but it still owns
the body grammar, AST schema, host configuration, and renderer.
Registered functions and rendering components remain trusted application code.

**Lesson for softschema:** Markdoc’s host-managed frontmatter boundary composes cleanly
with `validate_values`. Its body validation should remain a separate, higher layer.

#### Jupyter notebooks

The Jupyter notebook format is a versioned JSON document containing Markdown cells, code
cells, rich outputs, and metadata.
The format is broadly implemented and specified with JSON Schema, but its JSON
container, cell boundaries, generated outputs, and incidental metadata make prose review
and line-oriented Git changes harder than ordinary Markdown.
See the [nbformat documentation](https://nbformat.readthedocs.io/en/latest/) and
[format description](https://nbformat.readthedocs.io/en/latest/format_description.html).

Execution is the product, not an edge case.
Jupyter Server documents that access to a running server enables arbitrary code
execution. Notebook signatures and trusted-output rules reduce the chance that active
HTML or JavaScript output runs merely because an untrusted notebook is opened, but they
do not make notebook execution safe.
See the
[Jupyter Server security and notebook trust model](https://jupyter-server.readthedocs.io/en/stable/operators/security.html).

Notebooks work offline when kernels, packages, inputs, and data are local.
Reproducible execution additionally requires an environment and data provenance strategy
that the file format alone does not supply.

**Lesson for softschema:** do not add notebook execution or adopt `.ipynb` as a native
artifact. A notebook workflow can validate an exported values object, a companion
Markdown artifact, or explicitly selected notebook metadata without executing cells.

### Configuration languages

#### CUE

CUE treats types and constraints as values and uses unification to validate or generate
configuration. Its CLI can validate existing YAML directly and reports locations in both
the constraint and data source.
It can also ingest and export formats such as JSON, YAML, TOML, JSON Schema, OpenAPI,
and Protocol Buffers.
See CUE’s [validation tour](https://cuelang.org/docs/tour/basics/validation/),
[YAML validation guide](https://cuelang.org/docs/howto/validate-yaml-using-cue/), and
[`cue export` input model](https://cuelang.org/docs/concept/using-the-cue-export-command/inputs/).

CUE is the strongest reviewed option for advanced external policy or configuration
validation because it can constrain existing YAML without first migrating the source
into CUE. A full CUE authoring model still introduces a new language, module system, and
runtime, and it does not preserve a narrative Markdown body.

**Lesson for softschema:** support interoperable JSON/YAML values and JSON Schema rather
than embedding CUE. A separate recipe can show how CUE validates data around the same
artifact boundary when a project needs unification or policy composition.

#### Dhall

Dhall describes itself as JSON plus functions, types, and imports.
It is a total language that forbids arbitrary side effects, supports semantic hashes,
and can render JSON or YAML. Its import model supports local files, environment
variables, and URLs; integrity hashes and caching can pin behavior and permit offline
reuse after an import is available.
See the [Dhall overview](https://dhall-lang.org/),
[language tour](https://docs.dhall-lang.org/tutorials/Language-Tour.html), and
[safety guarantees](https://docs.dhall-lang.org/discussions/Safety-guarantees.html).

Dhall offers the clearest security and reproducibility ideas in this group.
The cost is a specialized typed functional language whose records, functions,
normalization, and import semantics are a substantial migration from YAML frontmatter.
Narrative Markdown can be generated as text, but it is no longer the naturally authored
artifact.

**Lesson for softschema:** borrow explicit integrity, cache, and trust-policy concepts
for future schema bundles.
Do not require Dhall evaluation for ordinary validation.

#### Nickel

Nickel is a generic configuration language described as “JSON with functions.”
It supports record merging, defaults, documentation metadata, optional static types, and
runtime contracts with user-defined assertions.
Those features make reusable configuration expressive, but contracts can participate in
evaluation and transformation rather than acting only as inert schema annotations.
See the [Nickel introduction](https://nickel-lang.org/user-manual/introduction/),
[correctness model](https://nickel-lang.org/user-manual/correctness/), and
[contracts](https://nickel-lang.org/user-manual/contracts/).

Nickel’s package story is still a portability constraint: its documentation labels
package management experimental and says official releases have it disabled.
Local files work offline; remote Git or index packages require a package-enabled build
and prior resolution.
See [package management](https://nickel-lang.org/user-manual/package-management/).

**Lesson for softschema:** defaults and field documentation are useful authoring
metadata, but validation annotations should remain declarative and must not transform
values or depend on lazy evaluation.

#### Pkl

Pkl is a configuration-as-code language with templates, validation, object inheritance,
CLI and build integrations, code generation, and host-language bindings.
It can render multiple data formats and provides native executables on major desktop
platforms. See the
[Pkl introduction](https://pkl-lang.org/main/current/introduction/index.html),
[CLI](https://pkl-lang.org/main/current/pkl-cli/index.html), and
[language bindings](https://pkl-lang.org/main/current/language-bindings.html).

Pkl evaluation can load file, HTTPS, package, environment, and other resources.
Its CLI provides module and resource allowlists, root-directory restrictions, timeouts,
package caching, and explicit package-download and dependency-resolution commands.
These controls are strong, but they confirm that Pkl source is evaluated configuration
rather than inert data.
See the
[language security checks](https://pkl-lang.org/main/current/language-reference/index.html#security-checks)
and
[CLI common options](https://pkl-lang.org/main/current/pkl-cli/index.html#common-options).

**Lesson for softschema:** copy the explicit resolver-policy and offline-prefetch ideas
for optional bundle distribution.
Keep Pkl as a possible external producer of JSON/YAML, not as a core runtime dependency
or contract source.

## Comparison Matrix

The ratings are relative to softschema’s target: reviewable Markdown/YAML artifacts with
portable, offline validation.
“Risk” is the normal untrusted-artifact execution surface.
“N/A” under prose means the system is not a narrative document format.

### Authoring, prose, execution, and offline behavior

| System | Authoring ergonomics | Prose fidelity | Executable-code risk | Offline behavior |
| --- | --- | --- | --- | --- |
| Astro collections | High inside Astro; schema-driven completion and queries | High for Markdown; renderer owns use | Low for plain Markdown; high when MDX or custom loaders execute | Strong for local build-time collections after dependencies are installed; remote/live sources need network or a host cache |
| Contentlayer | High in its supported local Next.js workflow | High for Markdown or MDX source | Low for plain Markdown; high for MDX and trusted build plugins | Strong for local sources after dependencies are installed; maintenance makes future toolchain compatibility uncertain |
| MDX | High for React authors; mixed for prose-only writers | Medium-high; JSX and ESM interrupt Markdown and affect parsing | High; the document compiles to executable JavaScript/JSX | Strong after compiler, plugins, and components are local |
| Markdoc | High for controlled publishing; authors learn tags | High; CommonMark plus explicit extensions | Low-medium; source is declarative, but registered functions and renderers are trusted code | Strong after parser, configuration, and renderer dependencies are local |
| Jupyter | High for interactive computation; low for raw source review | Medium; Markdown is split into cells inside JSON with outputs and metadata | High; arbitrary kernel code and active outputs are core capabilities | Conditional on local kernels, packages, data, and environment |
| CUE | Medium; concise for experts, unfamiliar to many authors | N/A | Low-medium; configuration is evaluated, but it is not a general-purpose document runtime | Strong for local modules and data; remote modules require prior availability |
| Dhall | Medium-low until its typed functional model is learned | N/A | Low; total evaluation forbids arbitrary side effects, subject to explicit import access | Strong for local inputs and cached, integrity-pinned imports |
| Nickel | Medium; familiar records plus functions, merging, and contracts | N/A | Medium; functions, imports, contracts, and transformations add evaluation complexity | Strong for local files; remote package support is experimental and disabled in official builds |
| Pkl | Medium-high for configuration specialists | N/A | Medium; evaluation can read allowed modules and resources | Strong for local or cached projects; HTTPS and unresolved packages need network |

### Portability, tooling, agents, and migration

Contract portability asks whether another runtime can apply the same validation rules,
not merely whether a common data format can be exported.
Source/output portability records that separate concern.

| System | Contract/schema portability | Source/output portability | Tooling | Agent usability | Migration cost from Markdown/YAML |
| --- | --- | --- | --- | --- | --- |
| Astro collections | Low outside Astro: contracts are Zod schemas interpreted by Astro loaders | Markdown and common data files remain portable; queries and generated types do not | Excellent within Astro | High for agents familiar with TypeScript and Astro; framework context is required | Medium-high unless the application already uses Astro |
| Contentlayer | Low outside Contentlayer: document types and transforms are JavaScript/TypeScript configuration | Markdown/MDX inputs remain portable; generated application data APIs do not | Good historical DX, but the official project is unmaintained | Familiar surface, but agents must account for stale framework compatibility | High for new adoption; migration also inherits replacement risk |
| MDX | Low: body and metadata contracts come from host components, plugins, or JavaScript types | Medium-low outside JSX ecosystems; components and plugins define behavior | Broad compiler, editor, and framework ecosystem | High syntax familiarity, but safe handling requires a strict trust boundary | Medium from Markdown; higher when replacing JSX components or ESM exports |
| Markdoc | Medium-low: node and tag schemas are portable only with equivalent host configuration | Medium; the text format is open, but extensions and rendering are host-defined | Solid JavaScript parser, validator, and render integrations | Medium-high once project-specific tags and config are available | Medium; ordinary Markdown largely carries over, extensions do not |
| Jupyter | High for the notebook container’s versioned JSON Schema; payload contracts for computed values remain external | High document-format reach; reproducible execution still depends on kernel and environment | Excellent interactive ecosystem | Medium with notebook-aware tools; low for raw JSON patching and review | High when replacing prose documents or requiring reproducible execution |
| CUE | Medium: CUE constraints require its evaluator; format interop does not preserve every constraint as JSON Schema | High for exported JSON/YAML; CUE source still needs the CUE runtime | Strong CLI, diagnostics, modules, and Go API | Medium; semantics and unification require specialized context | Low for sidecar validation of existing YAML; high for full CUE authoring |
| Dhall | Low-medium: types and normalization require a Dhall evaluator and are not retained in plain output | High normalized data output; source needs a Dhall runtime | Good formatter, type checker, semantic hash/diff, and editor support | Medium-low because the language is specialized | High for full authoring; medium when used only as an upstream generator |
| Nickel | Low: runtime contracts, merging, and lazy evaluation require Nickel | High common-data output; source portability depends on a less mature runtime and package story | Useful CLI, formatter, LSP, and contracts | Medium-low because lazy contracts and merge semantics are specialized | High for full authoring |
| Pkl | Low-medium: types, templates, and validators require Pkl evaluation | High rendered output and several bindings; source needs Pkl | Strong CLI, IDE, build, package, documentation, and code-generation tools | Medium; familiar object syntax but substantial language semantics | High for full authoring; medium as an upstream generator |

## Key Insights

### The most important boundary is execution, not syntax

Markdown-like appearance does not imply inert data.
MDX and Jupyter are programs.
Markdoc is more constrained, but its tags and functions still acquire meaning from
trusted host configuration.
Conversely, Dhall’s unusual syntax has a smaller arbitrary-code surface because its
language is total and side-effect constrained.
softschema should document trust by processing stage instead of describing whole file
extensions as simply safe or unsafe.

### A portable result is not the same as a portable source

Every reviewed configuration language can produce common data, but its source remains
coupled to that language’s evaluator, import rules, package availability, and semantics.
Likewise, Astro and Contentlayer start with portable Markdown but make the operational
contract an application API. JSON Schema plus ordinary YAML/Markdown remains a better
source-level interoperability boundary for softschema’s target users.

### Existing YAML is a strategic adoption advantage

CUE’s sidecar validation path is notable because it can constrain existing YAML without
rewriting the authoring source.
softschema has the same adoption advantage for existing frontmatter documents.
Features should preserve incremental adoption: add a contract, validate at the boundary,
and leave narrative prose untouched.

### Offline behavior is a resolver policy

Local-only tools are straightforward; module systems introduce hidden network and trust
choices. Dhall’s semantic hashes, Pkl’s allowlists and cache controls, and Astro’s
explicit build-time versus live loaders point to the same product rule: core validation
must be network-free, while any future external resolver must be explicit,
policy-controlled, cacheable, and integrity-verifiable.

### Framework coupling is an organizational risk

Contentlayer’s official maintenance notice is stronger evidence than a feature
checklist. A schema contract outlives individual build frameworks.
softschema should keep its portable schema and conformance suite primary, then offer
thin recipes or adapters that can be replaced without migrating artifacts.

## Strategic Decisions for softschema

These decisions are ordered by importance.

1. **Keep artifacts inert by default.** File adapters parse and normalize
   YAML/frontmatter; the portable core accepts normalized JSON-compatible values plus
   optional source locations.
   Neither layer compiles MDX, executes notebook cells, invokes Markdoc functions, or
   evaluates a configuration language.
2. **Keep JSON Schema as the portable contract ABI.** Python/Pydantic and TypeScript/Zod
   may be authoring sources, but compiled JSON Schema and conformance vectors define the
   cross-language boundary.
   Do not add CUE, Dhall, Nickel, or Pkl semantics to `x-softschema`.
3. **Keep `x-softschema` annotation-only.** Nickel-style transforming contracts and
   Pkl-style inherited evaluation are powerful, but they make results order-, runtime-,
   or evaluator-dependent.
   Validation rules remain JSON Schema or explicit host semantic validators.
   `x-softschema` may describe contract identity, compiler provenance, authoring, and
   presentation, but its values never assert or transform instance validity.
4. **Standardize the values boundary, not body adapters.** The stable integration point
   is a contract reference plus a JSON-compatible values object and optional source
   locations. Astro, MDX, Markdoc, Jupyter, or a configuration generator may produce that
   object outside core.
   No body parser belongs in the portable runtime.
5. **Make core resolution offline and deterministic.** Validation must not fetch schemas
   or imports over the network.
   If remote registries or bundles arrive later, require an explicit resolver,
   allowlist, integrity metadata, cache behavior, and an offline mode.
6. **Pursue Astro-class ergonomics without Astro coupling.** Prioritize editor schema
   associations, typed library results, positioned diagnostics, batch validation, watch
   mode, stable machine output, and clear collection-level summaries.
7. **Document trust tiers.** Distinguish inert artifact parsing, schema loading,
   optional model imports, host plugins, renderers, and executable document runtimes.
   An adapter must validate metadata before body execution and must not imply that body
   content was security-reviewed.
8. **Prefer recipes over runtime dependencies.** Publish small, replaceable integration
   recipes only where users demonstrate demand: validating Astro collection frontmatter,
   validating MDX or Markdoc metadata before rendering, checking exported notebook
   values, or using CUE alongside the same YAML.
9. **Do not become a content platform or configuration language.** Query layers,
   renderers, notebook kernels, component systems, remote content loaders, and general
   configuration evaluation remain explicit non-goals.

## Integration Opportunities

| Priority | Opportunity | Boundary |
| --- | --- | --- |
| Now | Explain how softschema differs from content pipelines, body runtimes, and configuration languages | Documentation only; no dependency |
| Now | Expose identical positioned diagnostics and JSON-compatible validated values in Python, TypeScript, and the CLI | Portable core API |
| Near term | Add editor schema-association guidance and fast batch/watch validation | Tooling around the existing contract |
| Near term | Define schema-bundle integrity and offline resolution behavior | Versioned bundle/conformance work |
| Later, demand-driven | Publish Astro, MDX, Markdoc, Jupyter-export, or CUE recipes | Separate examples or adapters; metadata/values only |
| Not planned | Execute document bodies, query collections, fetch content, or embed a configuration evaluator | Outside softschema |

## Recommendations

Use this brief to add a concise “related systems” section to the public guide after the
v0.3 behavior and terminology are settled.
The section should classify systems by layer, state the execution boundary plainly, and
point to recipes rather than promising native integrations.

For product work, prioritize portable diagnostics and offline bundles over new syntax.
Those investments capture the best parts of Astro, CUE, Dhall, and Pkl while preserving
softschema’s differentiator: strict validation that does not take over the document.

## Next Steps

- [ ] Use these decisions in `ss-v6bv` when restructuring the guide, README, and agent
  skill.
- [ ] Add explicit network-free resolver and trust-boundary requirements to the relevant
  v0.3 normative design work.
- [ ] Evaluate adapter recipes only after the portable conformance kit and diagnostics
  contract are stable.
- [ ] Recheck primary sources before publishing any version-specific interoperability
  claim.

## Methodology

Research used official project documentation, specifications, and official repositories.
Sources were reviewed on 2026-07-09. The assessment intentionally excludes secondary
comparison articles and community popularity claims.
Contentlayer’s maintenance status comes from its own repository rather than an inference
from commit frequency.

No benchmark, installation, or adversarial security test was performed.
Tooling quality, agent usability, migration cost, and prose fidelity are reasoned
assessments based on document formats, documented workflows, trust models, and the
current softschema design.

## References

### softschema

- [softschema Guide](../../softschema-guide.md)
- [softschema Spec](../../softschema-spec.md)
- [softschema runtime design](research-2026-05-24-softschema-runtime-design-v8.md)

### Astro and Contentlayer

- [Astro content collections](https://docs.astro.build/en/guides/content-collections/)
- [Astro content API](https://docs.astro.build/en/reference/modules/astro-content/)
- [Contentlayer documentation](https://contentlayer.dev/docs)
- [Contentlayer concepts](https://contentlayer.dev/docs/concepts-ac167d19)
- [Contentlayer official repository](https://github.com/contentlayerdev/contentlayer)
- [Contentlayer 0.3.4 release](https://github.com/contentlayerdev/contentlayer/releases/tag/v0.3.4)

### MDX, Markdoc, and Jupyter

- [MDX overview](https://mdxjs.com/docs/what-is-mdx/)
- [MDX frontmatter](https://mdxjs.com/guides/frontmatter/)
- [Markdoc syntax](https://markdoc.dev/docs/syntax)
- [Markdoc validation](https://markdoc.dev/docs/validation)
- [Markdoc frontmatter](https://markdoc.dev/docs/frontmatter)
- [Jupyter notebook format](https://nbformat.readthedocs.io/en/latest/)
- [Jupyter Server security](https://jupyter-server.readthedocs.io/en/stable/operators/security.html)

### CUE, Dhall, Nickel, and Pkl

- [CUE validation](https://cuelang.org/docs/tour/basics/validation/)
- [CUE YAML validation](https://cuelang.org/docs/howto/validate-yaml-using-cue/)
- [CUE export inputs](https://cuelang.org/docs/concept/using-the-cue-export-command/inputs/)
- [Dhall overview](https://dhall-lang.org/)
- [Dhall safety guarantees](https://docs.dhall-lang.org/discussions/Safety-guarantees.html)
- [Dhall language tour](https://docs.dhall-lang.org/tutorials/Language-Tour.html)
- [Nickel introduction](https://nickel-lang.org/user-manual/introduction/)
- [Nickel contracts](https://nickel-lang.org/user-manual/contracts/)
- [Nickel package management](https://nickel-lang.org/user-manual/package-management/)
- [Pkl introduction](https://pkl-lang.org/main/current/introduction/index.html)
- [Pkl CLI](https://pkl-lang.org/main/current/pkl-cli/index.html)
- [Pkl language reference](https://pkl-lang.org/main/current/language-reference/index.html)
- [Pkl language bindings](https://pkl-lang.org/main/current/language-bindings.html)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
