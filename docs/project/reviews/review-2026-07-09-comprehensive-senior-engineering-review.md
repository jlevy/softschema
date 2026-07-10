---
title: Comprehensive Senior Engineering Review
description: Architecture, security, parity, release, documentation, and agent-portability review of softschema at main commit 3f31aa8.
author: Joshua Levy with Codex
---
# Comprehensive Senior Engineering Review

**Date:** 2026-07-09

**Review target:** `main` at `3f31aa8`

**Status:** Findings complete; remediation is tracked in `ss-22fi`

## Executive Assessment

softschema has a strong and differentiated core idea: keep consumed values in YAML, keep
narrative Markdown inert, and validate at a language-neutral JSON Schema boundary.
The Python and TypeScript implementations already demonstrate unusually serious parity
work through canonical schemas, golden CLI tests, and interchangeable package surfaces.

The project was not ready for a broader trust claim at the reviewed commit.
The main risks were concentrated at boundaries that the existing happy-path corpus did
not exercise: remote schema resolution, parser representation differences, malformed
schema handling, meaning-changing canonicalization, installed-resource lookup, skill
writes, and publication reproducibility.
Several public explanations also described intended behavior more strongly than the
packages and workflows could guarantee.

No P0 issue was identified.
The P1 findings are release blockers because they cross a trust boundary, permit silent
cross-runtime divergence, or invalidate a published behavioral guarantee.

The recommended direction is evolutionary, not a rewrite.
Preserve the artifact model and interchange surface, define the portable behavior
precisely, split the implementation into pure core and runtime adapters, and publish the
shared vectors as an independent conformance kit.
The ordered implementation is in the
[hardening and conformance plan](../specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md).

## Review Method

The review covered:

- Python and TypeScript source, public APIs, CLIs, tests, and package manifests;
- canonical schema generation, structural and semantic validation, and SchemaView;
- YAML parsing, JSON Schema references, enforced overlays, error normalization, and
  golden parity;
- wheel, sdist, npm tarball, bundled docs, skills, and installer behavior;
- CI, OIDC publication, artifact verification, GitHub repository controls, and recovery
  from partial releases;
- README, guide, normative spec, design references, examples, agent instructions, and
  skill activation across major coding agents; and
- adjacent content, document, and configuration systems using current primary sources.

The healthy baseline was also verified: 146 Python tests, 170 TypeScript tests, package
builds, `publint`, Python/Node/Bun golden runs, and the direct Python-to-Node diff
passed at the reviewed commit.
Findings below therefore concern missing boundary coverage or incorrect guarantees, not
a generally broken codebase.

## Highest-Priority Findings

### P1: Schema validation could cross the network boundary

The Python JSON Schema path could follow an unresolved remote reference.
Validation of an untrusted checkout must never perform implicit HTTP, HTTPS, or
filesystem retrieval.
Both runtimes need the same deny-by-default resource registry, with only already-loaded
resources available to trusted library callers.

### P1: Malformed schemas did not share one result boundary

Syntax, dialect, metaschema, reference, regex, and engine compilation failures could
surface as different exceptions, tracebacks, or CLI exit classes.
Every readable but invalid schema needs a stable `schema_invalid` record and exit 1;
invocation and access failures belong to exit 2.

### P1: YAML did not yet have a cross-runtime value domain

Python and JavaScript disagree on timestamps, integer precision, negative zero,
non-finite numbers, aliases, merge keys, mapping keys, duplicate keys, and Unicode edge
cases. Parsing directly into ordinary objects can erase evidence needed to reject those
forms. The portable boundary must inspect representation structure first, enforce
resource budgets, normalize safe values, and attach stable paths and source positions.

### P1: Canonicalization and enforced overlays could change meaning

Blanket recursive rewrites can alter annotations, nullable unions, composed schemas,
boolean subschemas, and `unevaluatedProperties` behavior.
Canonicalization needs a recognized-keyword traversal, and enforced strictness must
either prove that its overlay is safe or return `enforcement_unsupported`.

### P1: Installed commands could trust consumer files

Resource lookup from the current working directory let a colliding consumer checkout
shadow packaged docs or skills.
Installed artifacts must use bundled bytes; source-tree overrides require an exact
checkout identity. Wheel, sdist, and npm tests need malicious collision sentinels, not
only clean installations.

### P1: Skill installation could write too broadly or clobber files

The installer needed explicit project versus personal scope, exact agent targets,
canonical containment checks, repository-bound project writes, ownership receipts,
prior-digest allowlists, deterministic locking, dry-run non-mutation, staged
replacement, rollback, and crash repair.
Unmanaged or user-modified skills must never be overwritten.

### P1: Publication was not a closed, reproducible boundary

Release builds depended on ambient project state and did not fully prove archive
contents, metadata identity, SBOM subjects, checksums, console aliases, runtime loading,
or partial-release recovery.
A release candidate should be a manifest-closed set of artifacts built once,
smoke-tested after installation, and published by OIDC-only jobs that neither check out
source nor rebuild.

## Design and Product Findings

### Separate logical contract identity from schema resource identity

A contract ID names an artifact payload contract; it is not necessarily a URI. Copying
it into JSON Schema `$id` conflated two registries and made reference resolution
ambiguous. Compiler APIs should require a validated contract ID in
`x-softschema.contract` and accept a separate optional canonical HTTPS or URN schema ID.
All metadata, registry, API, CLI, and compiler entrypoints must use one validator.

### Version independent contracts independently

The artifact metadata grammar, `x-softschema` compiler block, compiled-schema profile,
diagnostic wire format, conformance kit, package release, and logical contract version
evolve for different reasons.
Reusing one version across those layers creates accidental compatibility promises.
Each needs its own explicit identifier and negotiation rule.

### Extract a portable core without a big-bang rewrite

The target architecture has three layers:

1. a JSON-compatible core for metadata, identity, schema profile, canonicalization, and
   result contracts;
2. Python and Node/Bun adapters for YAML, filesystems, Pydantic, Zod, and trusted
   resources; and
3. thin argparse and Commander adapters for paths, model loading, output, and exits.

This separation makes a third implementation practical and prevents Node-only modules
from leaking into the TypeScript library root.

### Complete the product surface around the core

The existing library supports more than the CLI exposes.
Important additions are explicit pure-YAML validation, batch ordering, JSONL, positioned
diagnostics, SARIF, serializable TypeScript contract descriptors, and coherent Node/Bun
model-loading rules.
These should remain adapters over the same single-file result contract, not forked
validation implementations.

### Publish conformance, not only two matching implementations

Python/TypeScript parity can preserve the same mistake twice.
The project needs public, versioned schemas and raw input/output vectors that execute
without either package.
That kit should cover parser representations, every normalized error, references,
regexes, formats, canonicalization, identities, resources, CLIs, and installed
artifacts.

## Strategic Positioning

The adjacent-system research supports a clear product boundary: **strict values, inert
prose, portable schema**. Astro and Contentlayer demonstrate typed content ergonomics;
MDX, Markdoc, and Jupyter own body semantics; CUE, Dhall, Nickel, and Pkl own executable
or constrainable configuration.
None is a direct replacement for softschema.

softschema should borrow fast feedback, typed access, source-positioned diagnostics,
editor associations, offline bundles, and integrity policies.
It should not compile a Markdown body, execute notebook cells, evaluate a configuration
language, or make an application framework the contract authority.
Framework and configuration integrations belong in optional adapters around
`validate_values`.

See the primary-source
[adjacent systems research](../research/research-2026-07-09-adjacent-schema-document-systems.md)
for the full comparison and recommendations.

## Documentation and Coding-Agent Findings

The documentation set had good depth but blurred current behavior, future plans, exact
format rules, and implementation details.
The remediation should:

- keep the README short and adoption-oriented;
- keep the standalone guide conceptual and the language-neutral spec normative;
- move Python and TypeScript internals into design references;
- describe trust boundaries and migration behavior in present tense;
- make examples executable and keep proprietary context out;
- use one terminology table for artifact, payload, contract, compiled schema, profile,
  envelope, status, and extension;
- keep historical plans out of the active-spec directory; and
- follow the common documentation footer and practical-prose structure throughout.

The skill should be a concise routing layer, not a second manual.
It needs standard frontmatter, progressive disclosure, capability-aware local-first
discovery, exact release pins, no unportable tool grant, and a self-contained brief.
Activation and safe installation must be tested for Codex, Claude Code, Gemini CLI,
GitHub Copilot, Cursor, Windsurf, OpenCode, Cline, and Roo Code; agents without a
documented native skill target should get an explicit compatibility recipe rather than a
guessed path.

## Delivery Recommendation

Do not release the full claim set incrementally from partially compatible artifacts.
Land the work in dependency order, keep Python/Node/Bun and direct parity green at each
behavior boundary, regenerate canonical sidecars exactly once, then build and verify one
release candidate. Publish only after repository controls, protected environments, and
both registry trusted-publisher claims are verified.

The release-specific threat model and residual controls are recorded in the
[release boundary review](review-2026-07-09-release-boundary.md).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
