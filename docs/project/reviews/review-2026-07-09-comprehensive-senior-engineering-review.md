---
title: Comprehensive Senior Engineering Review
description: Architecture, security, parity, release, documentation, and agent-portability review of softschema at main commit 3f31aa8.
author: Joshua Levy with Codex
---
# Comprehensive Senior Engineering Review

**Date:** 2026-07-09

**Review target:** `main` at `3f31aa8`

**Status:** Code remediation complete; live publication gates remain in `ss-22fi`

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

### P1: Deterministic JSON serialization was not actually portable

The TypeScript serializer sorted keys and then delegated to `JSON.stringify`, but
JavaScript reorders integer-like object keys and compares other keys as UTF-16 code
units. Python sorts by Unicode code point and preserves the requested insertion order in
its encoder. Astral keys, integer-like payload keys, small exponent numbers, hashes, and
JSONL could therefore diverge despite the deterministic-output claim.
Use one explicit serializer over the portable value domain and shared byte/digest
vectors.

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
smoke-tested after installation, and published by OIDC-only jobs that check out only the
exact source verifier and never rebuild candidate artifacts.

## Adversarial Closure Findings

The first remediation pass exposed additional P1 edge cases that ordinary valid-input
tests did not reveal:

- artifact and schema readers checked byte limits only after allocating the complete
  file;
- TypeScript source-position lookup rescanned prefixes and line starts for each YAML
  node, creating quadratic work within the supported node budget;
- coded YAML composer exceptions could enter a broad `error.code` filesystem branch;
- ruamel.yaml and `yaml` disagree on compact flow spellings such as `{a:}` and `[a:]`,
  and their empty-null source anchors differed at CRLF, flow delimiters, comments, and
  EOF;
- recursive discovery used call-stack recursion, had no directory-identity visit set,
  and materialized an entire directory before enforcing any entry budget;
- escaped lone surrogates could survive standalone `json.loads`/`JSON.parse` boundaries
  and fail later during UTF-8 serialization;
- publication could retain undeclared output nodes or verify live schemas without
  byte-checking the live index; and
- a complete registry classification could survive failed provenance postconditions in
  the bounded retry loop.

These are tracked as `ss-zknx`, `ss-3o3w`, `ss-qu2u`, `ss-dz2o`, `ss-23yg`, `ss-yn4e`,
`ss-o04h`, `ss-tge8`, and `ss-prjf`. Each now has a hostile or complexity-oriented
regression in the candidate; the active plan records their dependency order and closure
evidence.

### Independent Red-Team Pass

A separate adversarial pass over the complete candidate found additional release
blockers before handoff:

- TypeScript undercounted compact-flow mapping nodes, normalized two plain scalar
  spellings that Python preserved, classified one malformed flow input differently, and
  sorted canonical `required` arrays by UTF-16 rather than Unicode scalar value.
- Document-controlled TypeScript schema bindings checked lexical containment but could
  follow an in-tree symlink outside both allowed roots.
- npm provenance accepted an expected workflow identity as a raw certificate-byte
  substring rather than an exact X.509 URI SAN.
- The extracted conformance consumer ignored root-level nodes and empty directories and
  had no per-file or aggregate declared-byte budget.
- Pages could treat all-404 as a fresh namespace after prior publication and a deploy
  artifact could omit future version/root files.
- Release recovery depended on a seven-day Actions artifact; subject sizes and retry
  delays were insufficiently bounded; the stable GitHub latest pointer was not a
  postcondition; and candidate metadata forced public bootstrap pins to an unpublished
  version.
- Generated Copilot links, trusted-publisher state claims, the TypeScript result
  wrapper, golden coverage descriptions, and registry-versus-source install instructions
  had concrete documentation drift.

The candidate now covers these with shared YAML/canonicalization vectors, realpath
confinement, a strict DER SAN parser validated against a live npm Fulcio certificate, an
exact bounded archive inventory, an append-only Pages root index plus reviewed promotion
marker, attested draft-asset recovery, release-size/latest/retry policies, and separate
candidate versions versus last-verified bootstrap pins.
The corresponding beads are recorded in the active plan; live Pages, the protected
GitHub release environment, publisher authorization, and actual registry publication
remain deliberately open.

### Final Boundary Audit

The final independent pass found one more trust-boundary layer:

- standalone adapters accepted generic case objects without enforcing each operation’s
  required input fields and primitive types, allowing raw `KeyError`/`TypeError`
  tracebacks instead of the documented malformed-request exit;
- recovery assets were attested only to a tag ref before executing the frozen driver,
  while the exact workflow commit was checked afterward;
- a mutable checksum asset reached `sha256sum` before authentication, so attacker-chosen
  filenames could trigger arbitrary reads before the exact inventory check;
- recovery extraction created unbounded implicit parent directories before applying
  depth and node budgets;
- immutable-release policy was not rechecked immediately before the final GitHub release
  mutation;
- Bun’s coverage gate counted runtime-created integration copies as separate source
  files and could exit nonzero after every TypeScript test passed; and
- the documented `github-release` reviewer gate was absent from the live environment
  inventory and would therefore not provide the claimed protection on a first run.

The code-side findings are closed as `ss-j81s`, `ss-3x0g`, `ss-pykr`, `ss-qezc`,
`ss-1mf4`, and `ss-bhz6`, with focused cross-runtime, release-security, or coverage-gate
regressions. Live-state bead `ss-8dt9` remains open until an authorized maintainer
provisions and re-reads the protected environment.

### Final Runtime and CI Audit

The first draft pull-request run and independent runtime/adversarial passes exposed a
final set of implementation-level gaps:

- the transferred artifact verifier generated Python bytecode inside the frozen
  candidate before authenticating its exact checksum inventory;
- `SchemaView` and compile drift checks still allocated complete schema files before
  applying the documented byte limit, could open special nodes before classifying them,
  and decoded committed TypeScript schemas with replacement characters;
- the source-resource trust test implicitly required an editable install and failed
  after CI correctly installed the candidate wheel;
- recursive portable-glob matchers could exhaust the Python or JavaScript stack on a
  valid long pattern or path;
- TypeScript constructed a complete YAML CST before checking its node/depth budgets; the
  first incremental pass then undercounted flow scalars and implicit maps, rescanned
  flow items quadratically, and could let a later limit beat earlier syntax or semantic
  failures;
- several TypeScript failure-selection traversals still used UTF-16 rather than Unicode
  scalar order, while Python materialized-value traversal still used insertion order;
- implicit and explicit flow mappings and custom-tag failures did not share all Python
  source boundaries and property-token coordinates;
- the release-manifest schema omitted the runtime subject-size ceiling and aggregate
  semantic limit; and
- the compatibility text overgeneralized the legacy single-file JSON result to unsafe
  non-files and discovery failures.

The adversarial inventory pass also found that exact verification ignored FIFOs and
other non-regular nodes and could be redirected by replacing a verified file or parent
directory with a symlink before hashing.
A final workflow review then found that the unprivileged smoke jobs executed the
transferred verifier before authenticating the candidate, Windows junctions were not
classified as redirects, and the actual candidate tree and checksum writer lacked
matching hard bounds.
These findings are tracked as `ss-lp5a`, `ss-tpr2`, `ss-1v5i`, `ss-dku3`, `ss-i32z`,
`ss-kfnc`, `ss-n7m1`, `ss-c8ix`, `ss-j2ps`, `ss-96ih`, and `ss-3i41`. The closure keeps
candidate verification non-mutating and descriptor-bound, runs an exact-commit checkout
verifier before candidate code, rejects POSIX and Windows redirects, and bounds both
inventory directions.
It also centralizes identity-stable limit-plus-one readers, makes wheel-first resource
tests explicit, uses iterative glob dynamic programming, enforces CST construction
budgets with global error precedence, applies one scalar comparator to parity-visible
traversal, aligns source locations and manifest limits, and narrows the legacy output
claim to implemented CLI behavior.

### Post-remediation resource-bound audit

A final complexity, compiler, and identity audit challenged the fixes at their declared
maximums instead of accepting bounded-looking constants at face value.
It found:

- the compilers applied value budgets before adding the digest field; Python check mode
  treated booleans and integers as equal, and Windows text translation could change
  already-sized output bytes;
- a Thompson NFA removed catastrophic backtracking but its first implementation still
  scanned large active-state and character-class sets, repeated pattern/key work across
  `patternProperties`, and retained no aggregate validation fuel;
- wildcard segments had a bounded inner matcher but an invocation could multiply many
  patterns by every discovered candidate without a total work budget;
- diagnostics reopened a schema after validation and could project locations from
  replacement bytes, while TypeScript’s missing-path canonicalization did not follow a
  dangling symlink’s target prefix;
- the final privileged release job executed a transferred helper before trusted
  verification, and the frozen state driver still had racy unbounded reads; and
- skill dry runs read arbitrary target, recovery, and lock files without a managed-file
  byte ceiling.

The resulting work is tracked as `ss-84vm`, `ss-7ykr`, `ss-v2h3`, `ss-clz0`, `ss-bcdi`,
and `ss-2upc`. The remediation validates the final sidecar, writes exact UTF-8 bytes,
uses normalized character intervals and cached bounded automata with total fuel, caps
discovery pattern and invocation work, carries the exact parsed source map, resolves
missing symlink components consistently, verifies transfers before candidate execution,
and bounds release and skill-installer reads.
These late findings reinforce the main review lesson: a limit is credible only when it
charges the actual expensive operation and is exercised at the supported boundary.

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

## Remediation Status on 2026-07-09

The code candidate passes 776 Python tests with one platform skip, 591 TypeScript tests,
62/60/62 Python/Node/Bun golden cases, a 26-command direct Python-to-Node byte
comparison, and 25 ready artifact cases plus 80 portable vectors under all three
runtimes. These are dated review observations, not stable product claims.
Python and Bun dependency audits report no known vulnerabilities.
The deterministic wheel, sdist, npm tarball, and extracted conformance consumer smoke
tests pass.

The repository API shows active `main` and `v*` rulesets, SHA-pinned Actions policy, and
`pypi`/`npm` protected environments restricted to `v*` tags.
It also shows immutable GitHub releases disabled and no configured Pages site.
No `github-release` environment exists in the same inventory, so its required reviewer
gate remains an explicit live prerequisite.
Registry trusted-publisher claims and a real publication have not been exercised.
The candidate therefore remains unreleased, the conformance identifiers remain draft
URNs, and the live-state beads stay open.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
