# Feature: softschema Hardening, Conformance, and Agent Portability

**Date:** 2026-07-09

**Author:** Codex, from the July 2026 senior engineering review

**Status:** In Progress

**Tracking:** `ss-22fi` (July 2026 review remediation epic)

## Overview

This plan fixes the security, parity, schema-correctness, packaging, documentation, and
agent-integration findings verified against `main` at commit `3f31aa8`. It is ordered
around three release gates:

1. Contain trust-boundary vulnerabilities and make every malformed input fail through a
   stable result boundary.
2. Define the portable YAML, JSON Schema, canonicalization, and identity semantics that
   both runtimes implement.
3. Publish those semantics as a standalone conformance kit, expose the missing CLI and
   library capabilities, harden distribution, and rewrite public documentation against
   the settled behavior.

The existing Python, Node, and Bun golden corpus remains the behavioral safety net.
Every cross-runtime behavior change is golden-first: add the shared failing case, make
Python pass, port the behavior to TypeScript, then require all three golden runs and the
direct Python-to-Node comparison to pass.

## Goals

- Prevent compiled-schema validation from initiating network access under every profile.
  Trusted library callers may separately supply already-loaded offline resources; doing
  so never permits retrieval.
- Ensure installed packages always use their own reviewed docs and skills, never a
  consumer repository’s colliding files.
- Return deterministic, structured failures for every malformed artifact or compiled
  schema; no engine traceback or usage-error substitution.
- Define one JSON-compatible YAML value domain and one JSON Schema 2020-12 validation
  profile for both runtimes.
- Make canonical compilation and the `enforced` overlay semantics-preserving within a
  precisely documented compiler-output profile.
- Validate logical contract IDs at every metadata, library, registry, CLI, and compiler
  boundary while separating them from JSON Schema URI identifiers.
- Expose the existing `pure-yaml` profile through both CLIs without changing the default
  profile or inferring behavior from a filename extension.
- Make the TypeScript runtime contract, model-loading policy, error exits, and public
  result types coherent and usable as a library.
- Add safe batch validation, source-positioned diagnostics, and SARIF output while
  preserving the current single-file interface.
- Publish a versioned, language-neutral conformance kit that a third implementation can
  consume without installing Pydantic, Zod, Python, or Node.
- Make skill bootstrap and installation reproducible, non-interactive, explicit-scope,
  standards-conformant, and non-clobbering.
- Harden built artifacts and the PyPI/npm publishing boundary, including partial-release
  recovery.
- Reorganize the README, guide, spec, examples, design references, and agent instruction
  surfaces around current behavior and the common documentation guidelines.
- Leave `docs/project/specs/active/` and tbd with only genuinely active work.

## Non-Goals

- Parsing Markdown body prose or tables as structured data.
- Introducing a new schema language or replacing JSON Schema, Pydantic, or Zod.
- Executing or automatically downloading remote schemas.
- A hosted schema registry, hosted validation service, or network protocol.
- A full language server or editor extension.
  This plan provides source locations, SARIF, schemas, and conformance artifacts that a
  later LSP can consume.
- An MCP server. The CLI remains the primary execution surface.
- Inferring `pure-yaml` from `.yaml` or `.yml`; profile selection stays explicit.
- Silently accepting old invalid behavior for compatibility.
  Safety and parity restrictions fail loudly with migration guidance.
- Reopening completed June work.
  The July items are follow-on corrections or narrower deltas against shipped behavior.

## Background

The repository is healthy on its committed corpus: Python lint and 146 tests pass; the
wheel and sdist build; 170 TypeScript tests pass with 98.53% line coverage; TypeScript
build and `publint` pass; Python, Node, and Bun golden runs pass; and the direct
Python-to-Node comparison is byte-identical.

The review found that the strongest failures sit outside that corpus:

- Python’s default JSON Schema resolver follows remote `$ref` values.
- malformed schemas can escape as Python tracebacks or TypeScript usage errors;
- `format` assertions and YAML scalar types differ between the runtimes;
- canonicalization and the `enforced` overlay can change schema meaning;
- installed resource lookup can prefer consumer-repository instructions;
- skill bootstrap uses unpinned runners under a guarantee the package cannot enforce;
- `skill --install` can write at user scope unintentionally and overwrite unmanaged
  files;
- published artifact, runtime dependency, and OIDC workflow boundaries are not fully
  reproducible;
- the language-neutral spec does not yet contain enough machine-readable material for an
  independent implementation.

### Relationship to Earlier Plans

Earlier plans remain design history and are not reimplemented here:

- [Public readiness](../done/plan-2026-05-24-softschema-public-readiness.md) records the
  original concept and Python surface.
- [TypeScript/Zod parity](../done/plan-2026-06-01-softschema-typescript-zod-parity.md)
  records the canonicalization and golden-first parity process.
- [June review remediation](../done/plan-2026-06-10-softschema-review-remediation.md)
  records the current validation, metadata, and `enforced` architecture.
- [Terminology and linkage](../done/plan-2026-06-11-softschema-terminology-and-linkage.md)
  records the contract-versus-schema distinction and the v0.2 compatibility policy.

This plan supersedes their stale checklists, unsafe trust claims, and forward-looking
statements. It preserves shipped decisions unless the compatibility table below names an
intentional change. `docs/softschema-spec.md` remains normative; this plan describes the
amendments to make there.

## Design

### Delivery Invariants

- **Golden-first parity:** specified behavior starts as a shared failing fixture or
  conformance vector, then lands in Python and TypeScript in the same slice.
- **No hidden I/O:** artifact and compiled-schema validation performs no network access
  and no implicit filesystem reference retrieval.
- **JSON-compatible boundaries:** parsed YAML is normalized or rejected before it can
  enter validation, hashing, output serialization, or a semantic model.
- **Stable failures:** readable but invalid inputs return structured validation results
  and exit 1. Exit 2 is reserved for invocation or setup failures that prevent a
  validation result.
- **Host precedence:** explicit host configuration and registry bindings continue to
  outrank document-declared bindings.
- **Recoverable writes:** compilation, generation, and skill installation preflight
  every input and destination, stage complete outputs, replace each file atomically, and
  roll back recoverable failures.
  Cross-directory crash atomicity is not promised; rerunning must detect and repair any
  interrupted managed state idempotently.
- **Installed means bundled:** packaged CLIs read packaged resources.
  Development source overrides require an exact, testable source-checkout identity.
- **One behavior, multiple adapters:** filesystem, YAML parser, model, and CLI adapters
  may differ; the value domain, contract semantics, normalized results, and conformance
  vectors do not.
- **Documentation ships with behavior:** every behavior bead updates its immediate
  normative, safety, help, and migration text.
  The final documentation bead reorganizes and verifies settled material; it is not the
  first point at which behavior is documented.

### Architecture Direction

Refactor incrementally toward three layers rather than attempting a big-bang rewrite:

1. **Portable contract core:** JSON-compatible values, metadata grammar, contract IDs,
   schema-profile checks, canonicalization, normalized results, and wire schemas.
   It has no filesystem, network, dynamic-import, or terminal dependencies.
2. **Runtime adapters:** Python and Node/Bun YAML parsing, filesystem access, Pydantic
   or Zod semantic validation, and explicitly supplied offline schema resources.
3. **CLI adapters:** argparse/Commander, trusted model loading, path expansion, output
   formats, packaged documentation, skill installation, and exit-code translation.

Existing public entrypoints remain available while implementation moves behind these
boundaries. The TypeScript package exposes a transitively runtime-neutral
`softschema/core` entry and an explicit `softschema/node` adapter.
Through the documented one-minor compatibility period, the existing package root remains
a Node/Bun facade so its synchronous filesystem APIs do not break; an exact export
allowlist prevents that facade from becoming an accidental dependency boundary.

### Portable YAML Value Domain

The portable domain is recursive JSON data:

- objects with string keys;
- arrays;
- strings, booleans, and null;
- finite IEEE-754 binary64 numbers; and
- mathematically integral numbers in the inclusive range
  `[-9007199254740991, 9007199254740991]`, regardless of YAML spelling.

Both parsers must inspect the YAML representation graph before constructing ordinary
runtime objects.
Composer/AST checks reject duplicate keys, non-string keys, custom tags,
aliases, merge keys, cycles, and resource-limit violations while exact source spans and
scalar spellings still exist.
The TypeScript parser must use a key-preserving AST or `Map` mode for this check; object
construction must not erase duplicate keys.

The default untrusted-input budget is machine-readable and identical in both runtimes: 8
MiB encoded bytes per artifact/schema resource, 64 MiB across an offline bundle, 256
resources, 100,000 representation nodes per resource, depth 128, and 1 MiB Unicode code
points per scalar. Reject aliases and merges before expansion.
The CLI always enforces these defaults; a trusted library caller may supply explicit
lower or higher limits, which become part of typed/diagnostic-v1 result metadata while
the legacy serializer omits them.
Enforce byte limits before parsing and node/depth/scalar limits while composing, not in
a post-parse walk.

For an already-materialized library resource, apply node/depth/scalar limits first and
charge its per-resource/bundle byte budget as compact canonical UTF-8 JSON after
portable normalization.
Booleans therefore have their literal JSON size; cycles fail before size serialization.

Both parsers then reject, rather than stringify or coerce:

- duplicate or non-string mapping keys;
- non-finite numbers, unsafe integers, sets, binary objects, timestamp objects, and
  other non-JSON runtime values; and
- aliases or merge keys until both runtimes enforce the same bounded, acyclic expansion
  semantics.

Plain date-looking and timestamp-looking scalars follow YAML 1.2 Core behavior and stay
strings. Values that require YAML-specific runtime types must be quoted or rewritten as
ordinary JSON-compatible values.
The shared lexical policy rejects compact plain flow keys immediately before a
delimiter, a comment immediately after a flow opener without separation, an implicit
flow-sequence mapping with no key, and a suffix-only document-end marker.
Malformed explicitly tagged core scalars are positioned value-domain failures at the tag
property rather than host conversion exceptions.

Interpret each numeric scalar exactly before conversion.
If its mathematical value is integral, enforce the safe-integer interval regardless of
decimal or exponent spelling.
Otherwise convert with IEEE-754 round-to-nearest, ties-to-even; reject a non-finite
result or a rounded integral result outside the safe interval.
Shared vectors cover `1e20`, `100000000000000000000.0`, `9007199254740991.5`,
subnormals, overflow, underflow, and signed zero.

After representation checks, materialized artifacts, compiled schemas, and supplied
schema resources pass through the same recursive normalizer.
Every YAML spelling of numeric negative zero, including integer, decimal, and exponent
forms, normalizes to ordinary numeric `0` before validation, hashing, or output.
A domain failure carries a stable reason code, a JSON path, and a source location when
available; it never echoes an unserializable runtime value.

### Compiled Schema Profile and Reference Policy

- The dialect is JSON Schema Draft 2020-12. `$schema` may be absent or equal the
  official 2020-12 URI; any other value is `schema_invalid`.
- A compiled-schema file has an object root as a softschema reference-profile rule.
  Boolean schemas remain valid in subschema positions.
  Hand-authored root schemas may omit `x-softschema`; compiler output must include valid
  `x-softschema` metadata.
- Registry keys and root-resource schema IDs are canonical absolute HTTPS or URN
  identifiers with no non-empty fragment.
  Relative and fragment-only root IDs fail.
  Nested `$id` values may be relative and resolve under Draft 2020-12 against their
  containing resource base; their resolved identities participate in collision checks.
- Through 0.3, an explicit `legacy-0.2` compatibility profile also accepts an existing
  softschema compiler output only when root `$id` exactly equals the valid logical ID in
  `x-softschema.contract`. Treat that value as opaque and non-resolving, allow only
  fragment references, and emit migration guidance.
  Phase 1 keeps this compatibility; Phase 2 stops generating it and enforces HTTPS/URN
  IDs for new-profile output.
- Default validation allows fragment references such as `#/$defs/Address` and performs
  no HTTP, HTTPS, file, or implicit relative-file retrieval.
- An ID-less root has no synthetic filesystem or cwd base: fragment-only references are
  valid and every other relative reference is a `reference` failure.
  Such a root must refer to an explicitly supplied resource by its absolute mapping URI.
- Library callers may provide an in-memory mapping from canonical absolute URI to an
  already-loaded object or boolean schema resource.
  Every resource passes the same YAML value-domain, dialect, metaschema, and
  no-retrieval boundary as the root.
- The mapping key is authoritative.
  A resource `$id` may be absent or canonically equal to its key; a mismatch, duplicate
  canonical URI, or collision with the root URI is a structured failure.
  Relative references resolve against the resource `$id` or its authoritative mapping
  URI; neither runtime may discard `$id` during registration.
- External schemas are validated but never run through compiler canonicalization.
  Canonicalization is a model-compiler output profile, not a generic transform for
  arbitrary authored JSON Schema.
- Draft 2020-12 `format` is annotation-only in the default portable profile.
  This is the `annotation-only-v1` policy specified in
  [softschema Spec](../../../softschema-spec.md#format-annotations) and encoded in
  `tests/parity/format-annotations.json`. Python supplies no format checker for instance
  validation; Ajv sets `validateFormats: false` and does not install `ajv-formats`.
  Known and unknown names produce neither violations nor logger/stderr output, while
  other structural assertions and the trusted semantic model continue independently.
  A future opt-in assertion vocabulary may be added only with cross-runtime conformance
  vectors. This 0.3 compatibility change is owned by `ss-k381`, not the 0.2.x
  parser-safety patch.
- JSON Schema regexes use `portable-regex-v1`, the grammar specified in
  [softschema Spec](../../../softschema-spec.md#portable-regular-expressions) and
  encoded with its differential vectors in `tests/parity/portable-patterns.json`. Its
  contract is ECMA-262-derived Unicode, no-flag, unanchored-search semantics; bounds are
  at most 1000. It supports literals, dot, both anchors, capturing/noncapturing groups,
  alternation, classes/ranges, simple/lazy/bounded quantifiers, ASCII digit/word
  shorthands, ECMA whitespace shorthands, controls, hex/Unicode escapes, and escaped
  syntax. It rejects lookaround, backreferences, word boundaries, named/atomic groups,
  inline flags, property escapes, possessive quantifiers, surrogate escapes, and
  ambiguous future class operators.
  Both runtimes compile the authored expression to the same bounded portable automaton;
  neither delegates untrusted matching to a native backtracking engine.
  Compiled bytes and hashes stay unchanged, and error records restore the authored
  pattern. Eager traversal covers actual Draft 2020-12 schema positions, not annotation
  payloads; unsupported syntax returns the stable `pattern` record before engine
  compilation.

URI comparison is lexical and offline.
Apply RFC 3986 normalization to HTTPS IDs: lowercase scheme and DNS host, remove port
443, remove dot segments, uppercase percent hex, decode percent-encoded unreserved
characters, turn an empty path into `/`, and drop an empty fragment while rejecting a
non-empty one. Reject userinfo.
For URNs, lowercase `urn` and the namespace identifier, preserve
namespace-specific-string and component case, normalize percent hex/unreserved
characters, and reject non-empty fragments.
Do not resolve DNS or apply scheme-specific equivalence beyond these rules.
Reject duplicate root, supplied, or nested resolved identities after normalization;
shared vectors fix every normalization and non-equivalence case.

Schema loading is one boundary per runtime:

1. parse YAML or JSON through the representation checks;
2. normalize the portable value domain and enforce the root profile;
3. check the dialect and metaschema for the root and all supplied resources;
4. canonicalize resource identifiers and install schema bodies unchanged for only
   internal and explicitly supplied offline resources;
5. compile the validator; and
6. translate every failure to a stable `schema_invalid` result.

Every `schema_invalid` record requires `kind: "schema_invalid"`, `reason`, the constant
`message` below, and `schema_path` as an RFC 6901 JSON Pointer.
The root pointer is the empty string; escape tokens as `~0`/`~1` and render array
indexes as unsigned decimal.
Syntax/root failures use the root pointer.
Optional diagnostic-v1 position fields are `schema_source`, `line`, and `column`; there
is no ambiguous `path` alias.

| Reason | Constant Message | Additional Required Field |
| --- | --- | --- |
| `syntax` | `compiled schema is not valid YAML or JSON` | none |
| `value_domain` | `compiled schema contains a non-portable YAML value` | none |
| `root` | `compiled schema root must be a mapping` | none |
| `dialect` | `compiled schema uses an unsupported JSON Schema dialect` | `dialect` |
| `metaschema` | `compiled schema does not conform to Draft 2020-12` | none |
| `identity` | `compiled schema resource identity is invalid` | `detail` |
| `profile` | `compiled schema is outside the softschema profile` | `detail` |
| `pattern` | `compiled schema contains an unsupported or invalid pattern` | `pattern` |
| `reference` | `compiled schema reference is unavailable offline` | `reference` |
| `compile` | `compiled schema could not be compiled` | none |

`identity.detail` is one of `invalid_root_id`, `resource_id_mismatch`,
`duplicate_resource_id`, `root_resource_collision`, or `nested_resource_collision`.
`profile.detail` is a versioned enum in the result schema.
Portable messages never substitute values, paths, parser prose, or resolver prose;
structured fields carry them.

Engine-native exception prose does not enter the portable output contract.
When the artifact payload can still be extracted and a trusted semantic model was
supplied, semantic validation runs independently; the overall result still fails
structurally.

### Canonical Compilation and `enforced`

Canonical compilation must preserve validation semantics for every instance in the
portable value domain and every source shape supported by the model compilers:

- Rewrite nullable `oneOf` to `anyOf` only when the null branch is provably exactly null
  and the other branch excludes null through an explicit type or an internal `$ref`
  resolved within the same compiler-output profile.
  If proof would require an external resource, leave the union unchanged.
  Alternatively, change the source generator so Pydantic and Zod already emit the same
  supported shape.
- Traverse every Draft 2020-12 subschema position used by the supported compiler
  profile, including `$defs`, `dependentSchemas`, conditionals, `prefixItems`,
  `unevaluatedProperties`, and `contentSchema`.
- Preserve boolean subschemas.
- Keep current deterministic key ordering, required-field ordering, canonical JSON bytes
  used for hashing, and byte-identical UTF-8 YAML sidecars from both official compilers.
  `compile --check`, committed examples, package smokes, and direct parity compare the
  sidecar bytes as well as parsed values and `schema_sha256`.

This equivalence claim deliberately excludes inputs outside the portable domain, such as
integers beyond the shared safe range, and excludes arbitrary external schemas.

The `enforced` overlay must not close individual `allOf`, `anyOf`, `oneOf`, or
conditional branches in a way that rejects properties evaluated by sibling branches.
Use `unevaluatedProperties: false` only at an object evaluation boundary whose property
set is statically safe.
An explicit `additionalProperties` or `unevaluatedProperties` at that boundary wins and
is normalized through the same rule.
For every external or compiler-produced schema marked `enforced`, either traverse the
full supported Draft 2020-12 applicator surface or return a structural
`enforcement_unsupported` record with exit 1; never partially enforce it.
Its exact record inside `structural.errors` has `kind: "enforcement_unsupported"` and
the constant `message: "enforced validation cannot be applied safely to this schema"`.
An optional `schema_path` is an RFC 6901 pointer into an in-memory schema; diagnostic-v1
may add an optional `schema_source` URI/file display path plus line/column.
The message never depends on a filesystem path.
Semantic validation still runs independently when a trusted model is available.

### Contract Identity and Schema Identity

One exported validator in each runtime owns the existing contract-ID grammar.
It is used by metadata parsing, `Contract` construction, registries, explicit CLI
overrides, and compile/build APIs.
Invalid IDs fail before registration, model import, schema generation, or file writes.

A logical contract ID is not a JSON Schema URI. In the corrected compiler contract:

- `contract_id` / `contractId` remains in `x-softschema.contract`;
- compilation no longer copies a contract ID into `$id`;
- an optional `schema_id` / `schemaId` and `compile --schema-id <absolute-uri>` control
  `$id`; and
- schema IDs receive the canonical absolute-URI validation described above.

The shared schema-ID profile has one byte spelling for each accepted identity.
HTTPS IDs use lowercase scheme and authority, canonical dotted-decimal IPv4 or
compressed lowercase IPv6, no credentials or default/zero-padded port, an explicit
slash-prefixed path, no dot segments, and RFC 3986 path/query characters.
URNs use a lowercase RFC 8141 namespace identifier and the ASCII NSS core; this version
excludes r-, q-, and fragment components.
In both forms, percent escapes are uppercase and never encode an unreserved byte.
The input must already equal this canonical spelling; validators do not silently
normalize aliases.

This intentionally changes compiled schema bytes and `schema_sha256` once.
Both model compilers and every committed example are regenerated in one reviewed
rebaseline.

### Format and Extension Versioning

This runtime behavior is tracked separately as `ss-wuva`; the conformance kit records it
but does not define it after the fact.

The artifact-format version is independent of package releases.
Newly authored artifacts use the explicit quoted format identifier `"1"`:

The metadata block may be a compact contract ID or one closed mapping with `contract`,
`schema`, `envelope`, `status`, and `extensions` fields.
The contract ID is the only authored version string.

The metadata mapping may carry one `extensions` mapping.
A key is either an absolute HTTPS namespace normalized by the schema-URI rules or a
lowercase reverse-DNS name matching
`^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$`. Values may be
any portable JSON value.
Reject duplicate canonical namespaces; preserve unknown extensions value-semantically
through parse/serialize but ignore them for core validation.
Format 1 exposes no extension-registration API and the CLI never imports or executes
extension code. A later versioned proposal may add trusted host validators with its own
precedence and wire contract.
Unknown top-level metadata keys remain errors.
Encode all current opaque-extension rules in the metadata schema and positive/negative
compatibility vectors.

The compiled-schema profile, normalized result schema, and conformance kit each have an
independent versioned schema URI. Do not reuse the package version or the logical
contract version for these formats.

### TypeScript Library and Model Loading

Add a serializable `ContractDescriptor` and a typed runtime contract or binding that can
hold a Zod schema. Preserve the current `Contract` surface through a documented
deprecation period; remove the need for callers to keep `contract.model` and a separate
`semanticModel` option synchronized.

The published Node CLI supports model modules Node can import reliably: built `.js` or
`.mjs`. Direct `.ts` loading is explicitly Bun-only and does not promise tsconfig path
aliases or non-erasable TypeScript syntax.
Error messages tell Node users to compile the model or invoke the supported Bun path.

Commander usage failures map to exit 2, matching Python.
Public validation output gains named, discriminated types for artifact results,
structural errors, semantic issues, warnings, and wire serialization instead of
`Record<string, unknown>`.

The supported Bun source-model invocation is tested explicitly as
`bunx --bun softschema@<npm-pin> compile --model ./model.ts ...`; Node tests use built
`.js`/`.mjs` modules.
Local-package equivalents may replace the registry pin in CI but must exercise the same
executable and loader path.

### Schema View and Artifact Boundaries

- A `$ref` resolution merges legal property-local siblings such as `description` and
  `x-softschema`; it does not discard them.
- Only an exact reference-plus-null union is unwrapped.
  Genuine unions remain unions in the view rather than being represented as the first
  reference.
- Envelope inference consumes only objects that already passed the portable key check;
  `ss-l41u`, not `SchemaView`, owns non-string-key rejection.
- `SchemaView` deep-copies validated input at construction and `raw` returns a defensive
  deep copy of that immutable internal snapshot.
  Mutating constructor input or a `raw` return value never changes later navigation.
  Its actual exception types match its public documentation.

### CLI Profiles, Batch Validation, and Diagnostics

Both CLIs gain explicit `validate --profile frontmatter-md|pure-yaml`. The default
remains `frontmatter-md`. In `pure-yaml` mode, root `softschema` metadata is removed
from the payload; without an explicit envelope the remaining root is the payload,
preserving the existing library behavior.

Batch validation extends `validate` without breaking a single-path invocation:

- accept multiple paths and, with `--recursive`, directories.
  One explicit `--profile` applies to the whole invocation: recursive `frontmatter-md`
  discovers `.md`/`.markdown`, while `pure-yaml` discovers `.yaml`/`.yml`; optional
  repeatable `--include`/`--exclude` globs refine, but never infer, that profile.
  Globs match the normalized `/`-separated path relative to each directory operand,
  case-sensitively, with shared `*`, `?`, `[]`, and complete-segment `**` semantics;
  excludes win and hidden entries are ordinary candidates.
  Reject empty, absolute, drive-qualified, backslash-containing, dot-segment,
  unterminated-class, and partial globstar patterns as invocation errors.
  Include/exclude flags require `--recursive`;
- treat a directory without `--recursive` as
  `input_error: directory_requires_recursive`. Do not follow discovered symlinks; allow
  an explicit symlink to a file only after canonical target and access checks.
  Enumerate command-line operands in given order and each directory in its normalized
  sorted order; the first occurrence of a canonical file identity wins global
  deduplication and supplies its display spelling.
  Prefer device/inode identity so hard links deduplicate, with canonical realpath
  fallback when a stable file ID is unavailable.
  Broken explicit symlinks are `not_found`; loops, directories, and other non-files are
  `unreadable`. The adapter does not claim race-free no-follow semantics if a file is
  replaced between inspection and read;
- display paths relative to the invocation directory when contained there and absolute
  otherwise, with `/` separators.
  Sort by case-sensitive Unicode code-point order over the unnormalized filesystem
  spelling of that display path on every OS; never case-fold, locale-sort, or silently
  NFC/NFD-normalize;
- preserve the current single-result JSON for a request containing one single explicit
  file operand with default format or `--format json` when discovery classifies that
  operand as a regular file, including when a later read fails and when harmless
  `--recursive` is present.
  A single explicit missing path or broken symlink is the narrow legacy
  `input_error/not_found` exception.
  Directory expansion, multiple operands, JSONL, SARIF, and every other single-path
  discovery failure select diagnostic-v1, even when discovery or deduplication leaves
  one result;
- use aggregate diagnostic-v1 JSON by default for multiple/discovered paths,
  one-result-per-line diagnostic-v1 for `--format jsonl`, and SARIF 2.1.0 for
  `--format sarif`. A one-path request for JSONL/SARIF opts into diagnostic-v1;
- exit 0 when every discovered artifact passes and 1 when any readable artifact fails
  validation. A recursive directory with no matches emits `input_error/no_matches` so a
  wrong profile or filter cannot produce a false green run.
  In diagnostic mode, missing, unreadable, and no-match paths produce per-path
  input-error records, processing continues, and the aggregate exits 2 if any such input
  failure occurred; and
- report partial success honestly.

Parse and access records are discriminated results, not partially populated validation
results; they omit unavailable `contract_id`, status, and document metadata:

| Kind/Reason | Stable Message Template | Required Fields | Optional Diagnostic-v1 Fields |
| --- | --- | --- | --- |
| `parse_error/frontmatter` | `artifact frontmatter delimiters are malformed` | `kind`, `reason`, `message`, `source` | `line`, `column` |
| `parse_error/syntax` | `artifact is not valid YAML` | `kind`, `reason`, `message`, `source` | `line`, `column` |
| `parse_error/root` | `artifact YAML root must be a mapping` | `kind`, `reason`, `message`, `source` | `path`, `line`, `column` |
| `parse_error/value_domain` | `artifact contains a non-portable YAML value` | `kind`, `reason`, `message`, `source`, `path` | `line`, `column` |
| `input_error/not_found` | `artifact path does not exist` | `kind`, `reason`, `message`, `source` | none |
| `input_error/unreadable` | `artifact path cannot be read` | `kind`, `reason`, `message`, `source` | none |
| `input_error/directory_requires_recursive` | `artifact directory requires --recursive` | `kind`, `reason`, `message`, `source` | none |
| `input_error/no_matches` | `artifact directory contains no matching files` | `kind`, `reason`, `message`, `source` | none |

`ss-pvu9` implements frontmatter, syntax, root, and access records in Phase 1; `ss-l41u`
adds `value_domain` after defining the portable value semantics.
A readable parse error exits 1. A missing, unreadable, or unexpanded directory single
input exits 2. For a batch, process every discoverable input and apply aggregate
precedence `2 (any input_error) > 1 (any readable failure) > 0`; JSONL record order is
the same as aggregate JSON. `path` uses the same RFC 6901/root/escaping rules as
`schema_path`; messages never interpolate source or parser prose.
YAML node spans are retained long enough to map JSON paths to file, line, and column.
Lines and columns are one-based, columns count Unicode code points, a BOM has no width,
and CRLF is one line break.
Existing-key errors anchor to the key, exact instance-path errors to the value,
missing-property errors to the containing object, and unavailable paths fall back to the
nearest mapped ancestor.
Frontmatter parsing passes the exact raw substring, including its final newline, rather
than split/rejoining text.

The current one-file JSON serializer remains byte-compatible and omits new location
fields. Positioned errors use a separately versioned `diagnostic-v1` schema in new
multi-path JSON/JSONL and SARIF outputs.
The typed core may retain location data internally, but the legacy serializer must omit
it.
In diagnostic mode, an artifact with invalid metadata or no resolvable contract emits
a binding diagnostic, counts as a validation failure, and does not abort remaining
inputs; legacy one-file behavior remains exact.
JSONL emits one independently self-describing record per result and no summary record.
SARIF 2.1.0 uses stable sorted rules, percent-encoded artifact URIs,
`columnKind: unicodeCodePoints`, and the official OASIS schema; validation findings at
exit 1 are a successful invocation while any input failure at exit 2 is not.
Add `--format sarif` only after the diagnostic-v1 wire contract is stable.

### Skill Bootstrap and Installation

The distributed skill remains a routing layer.
It points at CLI help and bundled docs instead of duplicating flag tables.

Bootstrap resolution is local-first and reproducible:

1. derive required capabilities from the requested operation/model (`.py` needs Python,
   `.js`/`.mjs` needs Node or Bun, and direct `.ts` needs Bun) or an explicit documented
   runner override;
2. use a `softschema` on `PATH` only when `doctor --json` reports the discovery
   protocol, runtime, model loaders, and operation capabilities required;
3. otherwise try capable runtimes in deterministic order:
   `uvx --from 'softschema==<python-pin>' softschema`, `npx --yes softschema@<npm-pin>`,
   then `bunx --bun softschema@<npm-pin>`; validate each candidate with `doctor --json`;
   and
4. stop with an actionable compatibility/install message if no candidate qualifies.

Root `release-metadata.json`, validated by `release-metadata.schema.json`, is the single
source for logical release coordinates: metadata schema version, release state,
discovery protocol plus separate Python/npm pins, Python PEP 440 version, npm SemVer
version, conformance-kit version/status, supported runtime bounds, and expected artifact
names. Conformance availability is `unavailable`, `candidate`, or `release_asset`; a
digest is absent for unavailable/source candidates and supplied only by built metadata
for an immutable release-asset set.
This describes source and artifact bytes, not live registry state.
Immutable package bytes never change after publication; a separate verified follow-up
commit advances source bootstrap pins and `release_state` only after both registries
pass.

Stable tag `vX.Y.Z` maps to Python and npm `X.Y.Z`. Prerelease tag `vX.Y.Z-rc.N` maps to
Python `X.Y.ZrcN` and npm `X.Y.Z-rc.N`; every other publish tag fails preflight.
Generated bootstrap text uses the last dual-registry-verified stable pins; Bun uses the
npm pin. Registry package READMEs use the candidate artifact versions so PyPI/npm pages
describe the bytes they contain without making source discovery unresolvable.
Development checkouts advertise the last published stable pin pair and
`release_state: development`, never an unresolvable VCS version.
Preflight derives non-self-referential `build-metadata.json` after building the kit but
before building packages; it contains the logical metadata digest, source commit, build
ID, and kit digest, but never the containing package digest.
Packages embed this build metadata.
After package bytes are final, preflight generates external `release-manifest.json` as
the only owner of package/artifact SHA-256 values; the manifest is never embedded by an
artifact it hashes. Versioned `doctor --json` reports logical/build metadata, not a
self-referential release-manifest digest.
Tests cross-check every source skill, mirror, help epilog, README, guide,
install/publish/E2E document, and package/tag check.

Omit `allowed-tools`: no minimal portable grant covers the installed executable plus all
three pinned fallback runners.
`skill --brief` is self-contained and never uses an undefined shell variable.
Validate the source and both mirrors with a pinned `skills-ref`, byte-drift tests, a
line-budget check, executable bootstrap smoke tests, and a positive/negative activation
matrix recording agent, surface, model, version, date, prompt, and observed result.
Deterministic CI also checks skill name/directory agreement, description length and
activation cues, referenced resources, mirror bytes, and every advertised discovery
path.

Installation resolves scope before any write:

```text
softschema skill --install [--project | --global] [--dir PATH]
                          [--agent NAME ... | --all-agents]
                          [--no-repo-check] [--dry-run]
```

- `--project` and `--global` are mutually exclusive.
  `--global` and `--dir` are mutually exclusive; `--dir` requires explicit `--project`
  and never implies it.
  `--agent` is repeatable and mutually exclusive with `--all-agents`; selectors replace,
  rather than add to, the default project target set.
- Inside a non-home Git repository, no scope flag keeps the current implicit project
  behavior and current `.agents`/`.claude` target set.
  Explicit project mode outside Git requires `--no-repo-check`; repository checks apply
  to the canonical target, not cwd.
- Project mode always refuses the filesystem root and the actual home directory,
  including with `--no-repo-check`.
- Global mode is explicit and requires one or more `--agent` selectors or
  `--all-agents`. Each target defaults from the process’s actual home.
  Honor only the vendor configuration-home environment variables named in the verified
  target table; surface every override as a separately selected base in dry-run/JSON,
  canonicalize it, reject filesystem root or containment escape, and apply its own
  lock/policy checks. A versioned target table names each supported agent’s
  project/personal path, override, OS behavior, and whether that surface supports
  skills.
- Resolve real paths before policy checks.
  Accept Git worktree roots and treat a submodule as its own repository; reject
  target/parent symlinks that escape the selected base.
  Acquire per-base locks in sorted path order, then revalidate every existing target
  immediately before the first replacement.
- Preflight every target before writing any target: absent is created; identical is
  unchanged; only a byte-exact known prior emission is updated.
  A locally modified managed file, unmarked file, unknown digest, or newer format aborts
  without overwrite; this release adds no force flag.
- Preflight every destination, stage complete temporary files, roll back recoverable
  failures, and use per-file atomic replacement.
  Cross-directory process-crash atomicity is not promised; an idempotent rerun detects
  and repairs managed partial state.
- `--dry-run` creates no directories, locks, temporary files, or backups.
  It returns 0 for a fully actionable/unchanged plan, 1 for ownership/path conflicts,
  and 2 for invalid invocation.
  Fault-injection tests cover every stage/replacement boundary, recoverable rollback,
  process-kill residue, concurrent installers, and repair.
- JSON output adds scope, resolved base directory, dry-run state, ownership, and action
  without removing current fields.

### Packaged Resources and Release Boundary

Installed wheel and npm CLIs read bundled resources first and do not walk consumer
ancestors. Source-mode resource lookup is enabled only when the module path and project
markers identify this checkout exactly.

The release workflow separates building, attestation/assets, and registry publication:

1. An unprivileged preflight job runs all checks, builds the conformance archive,
   derives build metadata, builds wheel/sdist/npm tarball once, generates SPDX 2.3 JSON
   SBOMs, and only then generates the external release manifest over those immutable
   primary subjects. It verifies versions, contents, entrypoints, resource hashes, and
   installed behavior before upload.
2. A separate GitHub-assets/attestation job receives `contents: write`,
   `id-token: write`, and `attestations: write`, uses a full-SHA-pinned current
   `actions/attest` surface, and attaches candidate bytes, manifest, checksums, and
   SBOMs to a draft GitHub release.
   Linked artifact storage is not used, so `artifact-metadata: write` is omitted.
   Every attestation subject is an exact primary manifest filename/digest; publish the
   GitHub release only after both registries verify.
3. Minimal PyPI and npm jobs receive only those verified artifacts and the
   registry-specific OIDC permission.
   PyPI uses the full-SHA-pinned `pypa/gh-action-pypi-publish`; npm uses an exact Node
   patch with the bundled npm version asserted, never installs npm globally, and
   publishes directly with provenance only after protected-environment approval.
   Each receives `contents: read` for draft assets and `id-token: write` for its
   publisher, but neither checks out the repository or resolves arbitrary dependencies.
4. A final GitHub-release job depends on both registry verification jobs and changes the
   already-verified draft to published with `contents: write`, without rebuilding or
   replacing any asset.
5. Every third-party action is pinned to a full commit SHA with the reviewed release tag
   in a comment.
6. Registry jobs use protected environments, least permissions, concurrency control, and
   a roll-forward-only recovery protocol.

Only a protected `vX.Y.Z` or `vX.Y.Z-rc.N` tag whose commit is reachable from protected
`main` may publish. `workflow_dispatch` remains a non-publishing dry run.
Recovery uses an environment-approved rerun of failed jobs from the original tag run and
re-downloads the manifest-verified GitHub release assets; it never rebuilds or accepts a
new digest. Stable npm releases use dist-tag `latest`; release candidates use `next` and
set the GitHub prerelease flag.
Recovery and post-publish checks verify those channel flags plus the Python/npm versions
mapped from the same logical release coordinate.

The release manifest hashes only primary subjects: wheel, sdist, npm tarball,
conformance archive, the exact logical and build metadata bytes embedded by the
packages, and artifact-specific SBOMs.
It never hashes itself.
Detached checksums, attestation service records, and `release-index.json` are derived
control records excluded from their own digest set; the index records the
release-manifest digest and expected control filenames.
CI regenerates and byte-compares control records, which prevents a digest cycle.

Before publishing, apply registry-specific state machines:

- **PyPI:** query the version’s file API and compare the exact wheel/sdist basenames and
  SHA-256 values. Absent uploads both; complete/exact is a no-op; partial stages only the
  missing file for the pinned publisher; an unknown filename or mismatch fails.
- **npm:** query the exact version’s `dist.integrity`/tarball, download it, and verify
  the manifest digest.
  The version is either absent, complete/exact, or conflicting; npm has no partial-file
  state.
- **GitHub:** compare primary assets to the manifest and control assets to regenerated
  expected bytes. Upload only missing assets; any same-name mismatch or unexpected
  release artifact fails.

A successful half-release is never unpublished.
Post-publish verification checks GitHub attestations with `gh attestation verify`, npm
registry provenance, and PyPI’s published attestation/digest metadata against the
release manifest. Long-lived PyPI/npm tokens are removed only after both
trusted-publisher paths have passed a controlled release.

For npm, a credentialed maintainer audit records the registered trusted publisher’s
exact owner/repository, workflow filename, environment, allowed action, GitHub-hosted
runner, package `repository.url`, and current official Node/npm minimums in a signed
`docs/release/npm-trusted-publisher-audit.json` snapshot.
Recertify before every release or after 90 days, whichever comes first; unauthenticated
CI validates snapshot schema, signature, age, and repo/workflow/package fields it can
observe rather than claiming to read private npm configuration.
Protected-environment approval is the human gate; there is no second token/2FA publish
path.

Build explicitly before `npm pack`; do not rely on `prepublishOnly`. Define direct
dependency policy by behavior: exact-pin output-sensitive CLI dependencies, bound and
test public library/peer ranges, commit lockfiles, install frozen, and audit in CI. The
supported matrix is explicit: Python 3.11 and 3.14, Node 22.12 and 24, and Bun 1.3.11
plus one separately reviewed exact compatibility pin recorded before preflight.
Apply the dependency-age/exception policy to that pin; a floating latest-stable lane is
non-privileged and advisory only.
Ubuntu runs full suites and package installs.
Windows and macOS each smoke-test wheel/npm-tarball install, CLI entrypoints, resource
shadowing, paths/model loading, and real project/global installs inside isolated
temporary homes, including locking, atomic replacement, injected residue, content
verification, and repair.

### Conformance Kit

Keep `tests/golden/` as the reference-CLI byte contract.
Add a separate root `conformance/` distribution for language-neutral semantics.
`ss-pvxi` creates draft schemas, a manifest, representative cases, and the shared runner
before behavior work.
Those Phase-1 files use non-public draft URNs and are not a released kit.
`ss-sbvh`, `ss-yxfm`, and `ss-wuva` finalize compiler/profile schemas before the single
Phase-2 rebaseline; `ss-xnr6` finalizes diagnostic-v1 before kit publication.
`ss-6i6d` fills, assigns verified v1 HTTPS IDs to, and publishes the complete kit after
semantics settle.

```text
conformance/
  README.md
  manifest.yaml
  schemas/
    manifest.schema.json
    case.schema.json
    metadata.schema.json
    compiled-schema-profile.schema.json
    validation-result-legacy.schema.json
    validation-result-diagnostic-v1.schema.json
    artifact-input-result-v1.schema.json
    structural-error.schema.json
    x-softschema.schema.json
    release-metadata.schema.json
    build-metadata.schema.json
    release-manifest.schema.json
    doctor-result.schema.json
    public-claims.schema.json
  cases/
    <case-id>/
      case.yaml
      artifact.*
      schema.*
      expected.json
```

The manifest records the kit version, artifact-format version, schema dialect, profiles,
YAML value domain, format policy, reference policy, serialization and hashing rules,
case paths, and digests.
`case.yaml` selects an operation, inputs, resources, and expected result schema.
Canonicalization cases start from raw language-neutral JSON Schema that itself validates
against the machine-readable compiler-input profile, never arbitrary external schema or
Pydantic/Zod model files; unsupported inputs are explicit negative cases.
Every schema validates against its metaschema; every path and digest is checked in CI.

Formalize `x-softschema` as an optional Draft 2020-12 annotation vocabulary with a
versioned metaschema.
Ordinary hand-authored schemas and validators may omit or ignore it; softschema-aware
tooling validates its shape, and compiler output must emit it.
Before minting identifiers, verify control and dereferenceability of the proposed
immutable namespace `https://jlevy.github.io/softschema/schema/v1/`. Static hosting of
versioned schemas is not a hosted registry or runtime dependency.

Cases cover both profiles, metadata, envelopes, status, malformed schemas, no-network
references, offline resources, YAML edge values, format annotations, contract ID versus
schema ID, every normalized error kind, canonicalization, strictness composition, and
stable hashes. Both official runtimes execute every case; Python, Node, and Bun results
are compared directly.

Freeze the compiler profile and emitted `x-softschema` fields before Phase 2’s single
schema rebaseline. Phase 3 may document and package that frozen vocabulary but may not
silently alter compiler bytes.
The kit versions independently from packages: patch adds non-changing cases, minor adds
backward-compatible capability, and major changes an existing result or wire shape.
`release-metadata.json` declares the kit version and status each package implements;
non-self-referential build metadata supplies the kit digest embedded by built packages,
while the external release manifest hashes final package bytes.
A deterministic archive and SHA-256 ship as a GitHub release asset and remain usable
without installing softschema.

### Documentation and Agent Surfaces

- Reduce the root README to roughly 100-150 lines: outcome, pinned quickstart, runtime
  chooser, source-of-truth rule, and links.
- Keep the guide task-oriented and language-neutral, with Pydantic and Zod paths side by
  side.
- Keep normative grammar, defaults, profiles, versions, extensions, reference policy,
  and result shapes only in the spec.
- Keep Python and TypeScript implementation details in their design references.
- Add a language-neutral artifact/schema plus paired `model.py` / `model.ts` and host
  snippets that compile to the same schema.
- Correct the `softschema.contract` versus `softschema.schema` rule, typographic shell
  quotes, stale version pins and parity claims, false cool-off and `npm pack` claims,
  and schema-path contradiction.
- Keep `.agents/skills` as the portable skill and `.claude/skills` as the identical
  Claude mirror. Keep `AGENTS.md` as the canonical project-instruction surface; add thin
  `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` shims only through
  each platform’s verified inclusion mechanism.
- Publish and test an agent compatibility matrix covering Codex, Claude Code, Gemini
  CLI, GitHub Copilot coding agent and IDE surfaces separately, Cursor, Windsurf, and
  OpenCode, Aider, and Cline/Roo Code.
  For each, record product surface/version, project and personal instruction and skill
  paths, precedence/import behavior, activation behavior, OS/config-home rules,
  primary-source URL, and last verification date.
  Prefer native `AGENTS.md` and Agent Skills discovery.
  Where real import/transclusion exists, test it; otherwise use a generated,
  drift-checked native file rather than an unverified prose request to read another
  file.
- Add `CHANGELOG.md` and a 0.2.x release note before the patch publish gate, covering
  validation limits/errors, network/resource trust, skill/bootstrap/installer behavior,
  and every safety migration.
  Add a separate 0.3 migration/release note covering contract/schema-ID rebaseline,
  format/regex policy, Node/Bun model loading, and legacy versus diagnostic-v1 result
  shapes.
- Maintain `docs/public-claims.yaml`, validated by
  `conformance/schemas/public-claims.schema.json`. Each stable claim ID points to an
  authoritative JSON Pointer in release metadata or the conformance manifest and lists
  target file plus generated-marker/snippet ID. A shared runner generates or extracts
  exact values for defaults/profiles, exits, network/reference policy, artifact/result
  versions, supported runtimes, and install destinations; CI fails on missing markers,
  stale generated text, or snippet output mismatch.
  Unmarked explanatory prose remains human-reviewed and is not falsely advertised as
  semantically linted.
- Preserve current `docs --list` topic names during this remediation.
  Validate every bundled topic and example from clean installed packages.
- Add a dated research appendix and concise alternatives/decision section comparing
  named related efforts such as Astro content collections/Contentlayer, MDX/Markdoc and
  Jupyter notebooks, and CUE/Dhall/Nickel/Pkl.
  Use current primary sources and explicit dimensions: authoring ergonomics, prose
  fidelity, schema portability, executable-code risk, editor/tool ecosystem, agent
  usability, migration cost, and offline behavior.
  Keep strategic claims traceable without copying the full research appendix into the
  user guide.
- Validate and regenerate the managed tbd `AGENTS.md` integration with the installed tbd
  version, including marker syntax and unsupported attributes, and test that the
  generated block and linked plan/spec paths are current.

### Implementation Guidance Baseline

Every implementation bead loads the applicable tbd guidance before design and review:

| Work | Required Guidance |
| --- | --- |
| Python core and CLI | Python rules, modern Python, Python CLI, error handling, and testing |
| TypeScript core and CLI | TypeScript rules, TypeScript CLI, YAML, error handling, and testing |
| Cross-runtime behavior | TDD, golden testing, and engineering-agent principles |
| Documentation and skills | Common documentation guidelines and CLI/agent-skill patterns |
| Packaging and release | Supply-chain hardening and commit conventions |

Treat these as review inputs rather than copied prose.
If implementation exposes a missing, generally reusable rule, track and review the
improvement in tbd itself, then refresh this repository’s generated tbd integration.
Do not block product security fixes on a speculative tbd upgrade or fork the guidance
silently inside product docs.

## Components

| Area | Primary Files |
| --- | --- |
| Python core and adapters | `packages/python/src/softschema/{models,validate,canonicalize,compile,schema_view}.py` |
| Python CLI/resources | `packages/python/src/softschema/cli.py`, wheel resource manifest |
| TypeScript core and adapters | `packages/typescript/src/{models,validate,canonicalize,compile,schemaView}.ts` |
| TypeScript CLI/resources | `packages/typescript/src/cli.ts`, `packages/typescript/resources/` |
| Shared behavior | `tests/golden/`, `tests/golden/cross-impl-diff.sh`, `conformance/` |
| Skills and project agents | `skills/softschema/`, `.agents/`, `.claude/`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` |
| Public docs/examples | `README.md`, `docs/`, `examples/movie_page/` |
| Packaging/release | `release-metadata.json`, `pyproject.toml`, `packages/typescript/package.json`, `.github/workflows/` |
| Tracking/history | `.tbd/`, `docs/project/specs/` |

## API Changes

- Add public contract-ID and schema-ID validators in both runtimes.
- Add an optional in-memory schema-resource registry to structural validation; no
  implicit network/file resolver.
  Resource keys, `$id` values, collisions, and supplied resource schemas follow the
  compiled-schema profile above.
- Add shared `ValidationLimits`/`validationLimits` options for trusted library callers;
  CLI defaults remain bounded and fixed by the conformance profile.
- Add `schema_id` / `schemaId` to compiler options and `compile --schema-id`.
- Keep artifact metadata to one compact-or-mapping grammar with no format discriminator.
- Add `ContractDescriptor` and a typed runtime Zod binding while keeping the current
  TypeScript `Contract` through deprecation.
- Add named TypeScript wire/result/error types.
- Version `doctor --json` identically in Python and TypeScript with logical/build
  metadata plus runtime/model-loader/operation capabilities for bootstrap selection.
- Add `validate --profile`, multiple paths, `--recursive`, include/exclude globs,
  diagnostic-v1 JSON/JSONL, and SARIF.
- Add explicit scope, agent targeting, and dry-run options to `skill --install`.
- Add structured artifact `parse_error` and compiled-schema `schema_invalid` reasons.
- Add source locations to the typed core and diagnostic-v1 outputs.
  The legacy single-file serializer remains exact and omits the new fields.

## Backward Compatibility

| Surface | Policy | Decision |
| --- | --- | --- |
| Internal code | Do not maintain | Refactor callers directly; leave no internal compatibility wrappers. |
| Public library APIs | Keep deprecated | Preserve current entrypoints and types through v0.3; additive APIs become preferred and removals wait for a documented pre-1.0 release. |
| CLI commands | Support existing | Preserve command names, flags, and single-file output. Additive flags are allowed. Commander usage errors normalize to the documented exit 2. |
| Skill installation | Intentional safety break | Ambiguous/outside-repo installs and unmanaged targets now fail before writing. No compatibility path preserves unsafe writes. |
| Artifact files | Do not maintain unmerged format discriminator | Validators accept the compact contract ID or one closed metadata mapping. Safe-YAML and portable-value restrictions apply to both and fail clearly. |
| Compiled schemas | Migrate | Existing official output continues through the narrow `legacy-0.2` profile with fragment-only references and migration guidance. Other schemas must satisfy the new portable, offline profile; external resources must be supplied in memory. New compilation separates contract ID from `$id`, regenerating committed schemas and hashes once. |
| Result/error wire shape | Support existing | Preserve the exact legacy single-file JSON serializer for representable validation results. Readable parse failures gain a new discriminated result instead of usage-error substitution. New batch/location output uses diagnostic-v1 JSON/JSONL or SARIF; schemas distinguish every contract. |
| `SchemaView.raw` | Tighten documented behavior | It was documented read-only but returned mutable internal state. It now returns a defensive deep snapshot; mutation of returned values never changes the view. |
| Server APIs | N/A | No server API. |
| Database schemas | N/A | No database. |

## Implementation Plan

### Phase 1: Trust and Failure Boundaries

This phase was initially planned as a separate 0.2.x security and correctness patch.
Implementation reached the later 0.3 semantic changes before that patch was released, so
the delivery decision is now one consolidated 0.3.0 release rather than a risky
after-the-fact backport from mixed commits.
The known 0.2.2 boundary risks remain a release blocker until 0.3.0 is published; no
text or metadata may imply that 0.2.3 shipped.
Draft conformance files remain unreleased test infrastructure until Phase 3. Independent
slices may run in parallel, but each includes regression tests and affected safety docs.

- [x] **Bootstrap conformance contracts (`ss-pvxi`).** Create draft manifest, case,
  compiled-profile, legacy-result, diagnostic-v1, discriminated parse/access,
  release/build/doctor, and public-claims schemas; a small language-neutral case set;
  and one shared runner that Python, Node, and Bun invoke.
  Freeze the Phase-1 error envelopes/reasons, but keep compiler/profile schemas on draft
  URNs until their Phase-2 owners finalize them.
- [x] **Normalize malformed schemas (`ss-dbkh`).** Add the shared schema-loading
  boundary and golden cases for malformed YAML, null/list/scalar roots, bad keyword
  values, unsupported dialects, unresolved references, and engine compilation
  exceptions. Reserve the `pattern` reason but make no portable-pattern acceptance claim
  before `ss-vn04`. Use `legacy-0.2` identity compatibility until `ss-yxfm` migrates
  compiler output. All failures return `schema_invalid`, exit 1, and never expose engine
  prose or tracebacks.
- [x] **Normalize artifact parsing and access (`ss-pvu9`).** Make readable malformed
  frontmatter syntax/root failures return discriminated `parse_error` results and exit
  1. Preserve exit 2 for missing/unreadable/directory inputs; define batch per-path
     access records and aggregate precedence.
     `value_domain` remains reserved until `ss-l41u` defines it.
- [x] **Bound and normalize YAML (`ss-l41u`).** Enforce byte/resource/node/depth/scalar
  budgets before and during composition, reject unsafe representation-graph features,
  implement the exact JSON-compatible numeric/value domain and `value_domain` result,
  and add shared edge vectors.
  These safety limits are required in the consolidated release; JSON Schema `format`
  behavior changes only in Phase 2.
- [x] **Disable implicit retrieval (`ss-0sgk`).** Install a no-retrieval Python
  registry; keep TypeScript offline; allow internal fragments and explicitly supplied
  in-memory resources only.
  Tests intercept URL/file access and prove zero calls.
- [x] **Fix packaged resource trust (`ss-7eoa`).** Make installed wheel/tarball commands
  use bundled docs/skills even from an adversarial consumer directory with colliding
  paths. Preserve a separate exact-checkout source drift path.
- [x] **Verify coding-agent discovery (`ss-slas`).** Build the dated, primary-source and
  smoke-tested compatibility/target matrix for Codex, Claude, Gemini, Copilot, Cursor,
  Windsurf, OpenCode, Aider, and Cline/Roo Code before bootstrap or installer paths are
  finalized.
- [x] **Harden bootstrap (`ss-1aa6`).** Replace `@latest`, interactive `npx`, undefined
  `$SS`, and non-standard frontmatter with the capability-aware local-first/pinned
  design. Implement the versioned, byte-compatible Python/TypeScript `doctor --json`
  contract, then add official skill validation, mirror, execution, line-budget, and
  activation-matrix checks.
- [x] **Make install safe (`ss-bj47`).** Add explicit scope, ambiguous-location refusal,
  ownership/version preflight, dry-run, staged per-file replacement, rollback and repair
  behavior, and symmetric Python/TypeScript golden coverage.
- [x] **Harden CI and the pre-publish artifact boundary (`ss-o21w`).** SHA-pin actions,
  build and verify immutable candidate artifacts before any privileged job, build before
  `npm pack`, add clean installed-artifact/resource-shadow tests, define dependency
  policy, introduce and validate root `release-metadata.json`, and add the
  minimum/cross-platform smoke matrix.
  Bound Python runtime requirements to reviewed compatible lines while retaining npm
  caret compatibility, audit the frozen Python and Bun graphs without severity
  downgrade, and resolve the npm artifact consumer once under pinned npm and a recorded
  14-day cutoff. Transfer its validated lock and control record with one recursively
  checksummed candidate; every downstream matrix job uses `npm ci --ignore-scripts`
  against those exact bytes rather than rebuilding or resolving again.
  Deliver the minimum protected, tag-authorized, manifest-verified PyPI/npm publisher,
  risk-review it, and add a complete disclosure of every 0.2.2 safety boundary and 0.3
  migration before release; `ss-trn7` owns the full 0.3 GitHub assets, provenance,
  registry state machines, and post-publish recovery.
- [x] **Reconcile stale tracking (`ss-qq77`).** Verify old specs and beads against main,
  explicitly disposition `ss-rm2v`, `ss-l592`, `ss-08np`, and `ss-h8u4`, mark/move
  implemented plans, update historical spec links, validate/regenerate the managed tbd
  `AGENTS.md` block with supported marker syntax, and leave this document as the sole
  active implementation plan.

**Phase gate:** no validation-triggered network access, no consumer resource shadowing,
no malformed schema/artifact exception escapes, untrusted input limits fail before
resource exhaustion, the draft result schemas validate every Phase-1 result, no unpinned
generated runner or ambiguous skill write remains, the protected publish path has passed
a dry run/risk review, the complete safety and migration disclosure is ready, and all
existing suites plus installed-package adversarial tests are green.

### Phase 2: Portable Semantics and Identity

This phase freezes the 0.3.0 core schema, identity, artifact-format, compiler, legacy
result, and diagnostic-envelope semantics; positioned diagnostic details remain owned by
Phase 3. It does not produce a release candidate.
Each bead first updates its normative/safety text and red conformance cases; `ss-v6bv`
later reorganizes the complete documentation set.
Rebaseline compiled schemas and hashes only once, after all semantic decisions land.
Do not publish 0.3.0 until Phase 3 is complete.

- [x] **Portable regular expressions (`ss-vn04`).** Choose and specify a
  machine-readable Python/ECMA-262-compatible pattern grammar or one shared engine,
  eagerly validate `pattern`/`patternProperties`, return the stable `pattern` reason,
  and add matching as well as syntax differential vectors.
- [x] **Portable format annotations (`ss-k381`).** Configure Ajv with
  `validateFormats: false`, prove known/unknown formats are warning-free annotations in
  both runtimes, preserve independent semantic-model validation, document the 0.3
  compatibility change, and reserve a versioned future assertion vocabulary.
- [x] **Semantics-preserving canonicalization and enforcement (`ss-sbvh`).** Tighten the
  nullable rewrite, complete the supported subschema traversal, preserve boolean
  subschemas, and make composition-aware closure pass `allOf`, conditional,
  `dependentSchemas`, `$defs`, pattern, tuple, explicit-opt-out, and stable
  `enforcement_unsupported` cases.
- [x] **Contract and schema identity (`ss-yxfm`).** Apply the shared contract-ID
  validator at every boundary, add independent schema IDs, and regenerate both compiler
  outputs to one equal schema/hash.
- [x] **Define artifact metadata (`ss-wuva`).** Support compact and mapping metadata,
  add the namespaced extension mapping, reject unknown top-level keys, and publish a
  machine-readable schema plus compatibility vectors.
- [x] **Use one authored version string (`ss-rpq0`).** Remove the unmerged
  `softschema.format` discriminator so only the contract ID carries an authored version;
  collapse metadata schemas, capabilities, examples, docs, and skills onto the single
  grammar.
- [x] **Artifact and schema-view boundaries (`ss-3n2k`).** Preserve ref siblings,
  represent genuine unions, consume only values normalized by `ss-l41u`, and align
  mutability and exception documentation.
- [x] **Core/adapters separation (`ss-0uj9`).** Extract portable value, identity,
  schema, and result logic behind compatible APIs; isolate filesystem/YAML/model and CLI
  adapters; add a Node-import guard for `softschema/core` and an exact compatibility
  allowlist for the TypeScript package root.

**Phase gate:** every portable-value, regex, format-annotation, and schema-applicator
vector passes in Python, Node, and Bun; raw-versus-canonical validity invariants hold;
contract IDs and schema URIs cannot be confused; the one intentional
compiled-schema/hash rebaseline is reviewed; compact/mapping metadata and extension
vectors pass; `SchemaView` snapshot behavior is identical; `softschema/core` is
transitively free of Node/runtime/CLI adapters and the legacy root facade matches its
exact compatibility allowlist; full goldens and direct parity remain green.

### Phase 3: Public Conformance, Usability, Documentation, and Release

This phase exposes the settled contract, freezes the full 0.3.0 release candidate only
after public APIs/CLI/docs are complete, and then publishes it.

- [x] **Expose pure YAML (`ss-6jp1`).** Add the explicit profile flag to both CLIs, a
  language-neutral example, help/docs, and shared cases for metadata-only, schema,
  semantic, envelope, precedence, malformed-root, and value-domain behavior.
- [x] **Align TypeScript API and CLI (`ss-b5l4`).** Add runtime contract bindings,
  descriptor/wire types, Node-versus-Bun model policy, Commander exit parity, Windows
  URL-safe imports, and deprecation guidance.
- [x] **Make JSON serialization portable (`ss-u30p`).** Replace JavaScript’s implicit
  UTF-16 and integer-index property ordering with a runtime-neutral serializer that
  matches Python for Unicode keys, portable finite numbers, compact hashes, pretty CLI
  JSON, and JSONL without changing ordinary existing bytes.
- [x] **Normalize compiler numbers before hashing (`ss-hwws`).** Pass the complete
  canonical compiler output through the portable JSON value boundary so equivalent
  Python and TypeScript bounds such as `10.0` and `10` produce the same schema bytes and
  hash; reject non-finite and unsafe integer-valued schema numbers before any write.
- [x] **Reserve root compiler metadata (`ss-2d33`).** Reject model-supplied root
  `x-softschema` values identically in both runtimes so the compiler alone owns the
  exact contract/version/hash block; preserve supported per-field annotations and prove
  every official compiler output validates its public conformance profile.
- [x] **Validate field annotations (`ss-fbtq`).** Reject empty groups/instructions,
  fractional order values, and invalid enum spellings at both authoring boundaries so
  Python and TypeScript can emit only annotations accepted by the public vocabulary.
- [x] **Reject non-portable literal YAML separators (`ss-0tb1`).** Reject literal
  U+0085, U+2028, and U+2029 in YAML source while permitting their escaped scalar
  values, and count only CR, LF, and CRLF as source line breaks.
- [x] **Anchor extra-property diagnostics to the key (`ss-y82x`).** Preserve structured
  validator metadata for each offending property so `additionalProperties` and
  `unevaluatedProperties` locations select the actual escaped key without parsing engine
  prose.
- [x] **Normalize coded YAML parser failures (`ss-qu2u`).** Translate parser and
  composer exceptions to positioned syntax errors before any generic error-code branch,
  and recognize filesystem errors only from the complete Node error shape.
- [x] **Settle compact-flow YAML (`ss-dz2o`).** Reject the parser-divergent plain forms
  `{a:}` and `[a:]` while preserving separated, quoted, URL, and colon-content forms;
  publish the restriction as a portable-YAML conformance vector.
- [x] **Align implicit-null anchors (`ss-23yg`).** Use the same zero-width boundary for
  empty mapping values, sequence items, flow entries, comments, CRLF, and EOF in both
  runtimes and diagnostic outputs.
- [x] **Bound file reads before allocation (`ss-zknx`).** Read artifacts and schema
  resources through `limit + 1` boundaries in both runtimes, including diagnostic
  source-map reloads, and reject oversize before decoding or parsing.
- [x] **Scale TypeScript source mapping (`ss-3o3w`).** Pre-index line starts and
  surrogate-pair boundaries so source-point lookups are logarithmic rather than
  rescanning prefixes for every YAML node, with exact legacy-coordinate equivalence
  tests.
- [x] **Bound recursive discovery (`ss-yn4e`).** Traverse iteratively, detect directory
  revisits, stop native enumeration at the shared 64-depth/100,000-entry per-operand
  limits, discard partial operand matches, and continue later operands.
- [x] **Batch and positioned diagnostics (`ss-xnr6`).** Add deterministic multi-path and
  recursive validation, JSON/JSONL aggregation, source spans, SARIF, partial-success
  reporting, and single-file compatibility tests.
- [x] **Harden conformance boundaries (`ss-tge8`).** Bound and strictly validate every
  standalone JSON/config/index/lock/adapter input; reject invalid Unicode scalars,
  duplicate keys, non-finite values, unsafe paths, symlink escapes, undeclared nodes,
  and output inventory drift before a write or deploy.
- [ ] **Complete the conformance kit (`ss-6i6d`).** Fill the foundation with every
  settled behavior, the optional `x-softschema` vocabulary, offline-resource and
  compound-bundle rules, evolution metadata, standalone cases, third-implementation
  walkthrough, deterministic archive, and Python/Node/Bun execution.
  Verify the stable namespace before publishing it.
- [x] **Make the namespace immutable and release-capable (`ss-oyr4`).** Classify live
  Pages state as absent, exact, or conflicting before deployment; bind publication to
  protected upstream `main`; validate released/final-ID metadata; and byte-check the
  live index plus every schema after deployment.
- [x] **Reject hostile standalone JSON (`ss-o04h`).** Apply bounded iterative depth,
  node, finite-number, duplicate-key, and Unicode-scalar validation to publication,
  archive-consumer, adapter, runner, and frozen release-state inputs before canonical
  output can fail with a raw runtime exception.
- [x] **Validate operation-specific adapter requests (`ss-j81s`).** Enforce the exact
  required fields, optional fields, primitive types, validation limits, and source
  pointers for every portable-core operation before dispatch; malformed requests must
  exit 2 with one stable error line in both standalone adapters.
- [x] **Make numeric limit typing explicit (`ss-gr29`).** Reject JSON booleans before
  integer range validation in the JavaScript adapter and preserve the rule in the shared
  invalid-request corpus for Python, Node, and Bun.
- [x] **Close final runtime parity (`ss-jfat`, `ss-ycm4`, `ss-ihzl`).** Count compact
  flow mapping pairs identically, preserve portable plain-scalar spellings, normalize
  the remaining flow error class, sort schema set arrays by Unicode scalar value, and
  reject metadata-schema symlink escapes in both runtimes.
- [x] **Close extracted-kit boundaries (`ss-stbo`, `ss-6okz`).** Require the exact root,
  directory, and file inventory with bounded traversal plus per-file and aggregate byte
  budgets before hashing.
- [x] **Make Pages promotion monotonic (`ss-4uki`, `ss-ej3x`).** Bind prior publication
  to an independently reviewed root-index digest, fail on later absence, and hydrate the
  complete append-only namespace so a deployment cannot delete future versions or root
  files.
- [x] **Close release recovery and identity (`ss-a43v`, `ss-x6iq`, `ss-ap6l`, `ss-23vm`,
  `ss-2t5m`, `ss-1157`).** Parse the exact npm X.509 URI SAN; separate candidate
  versions from verified bootstrap pins; persist an attested bounded recovery closure;
  bound release subjects and retry delays; and verify stable/latest channel
  postconditions.
- [x] **Close final release trust boundaries (`ss-3x0g`, `ss-pykr`, `ss-qezc`,
  `ss-1mf4`).** Authenticate the complete recovery closure against the exact workflow
  commit before parsing or execution, bound implied extraction directories before any
  write, and recheck immutable-release policy immediately before publication.
- [x] **Close final docs and agent drift (`ss-c305`, `ss-nsto`, `ss-9tx6`, `ss-uywa`,
  `ss-22gw`, `ss-2n7g`, `ss-ode8`, `ss-6a90`, `ss-vnul`, `ss-yaii`, `ss-75lu`,
  `ss-fj2k`).** Make generated adapters durable and link-correct, distinguish required
  versus verified live state, align executable docs/goldens/API wrappers, reconcile the
  tracker, and separate registry artifact instructions from source bootstrap.
- [x] **Research adjacent systems (`ss-srtz`).** Produce the dated primary-source brief
  and strategic comparison across content collections, executable/AST documents, and
  full configuration/model languages; turn evidence into concise product decisions.
- [x] **Repair docs and agent surfaces (`ss-v6bv`).** Perform the
  README/guide/spec/design split, paired Python/TypeScript examples, corrected commands
  and claims, agent compatibility matrix/instruction adapters, research-derived
  alternatives section, changelog/migration note, public-claims drift matrix, and
  docs-as-written package tests.
- [x] **Qualify activation-fixture coverage (`ss-66i9`).** Describe the shared positive
  and negative prompts separately from the per-product availability observations; do not
  imply ten independent live product test matrices.
- [x] **Reconcile research follow-ups (`ss-azpv`).** Mark the product decisions and
  network-free trust-boundary requirements complete while retaining future adapter
  recipe and pre-publication source-review work.
- [x] **Stabilize the TypeScript coverage gate (`ss-bhz6`).** Keep package source under
  the configured thresholds while excluding generated bundles and runtime-created
  integration copies that Bun otherwise treats as separate per-file coverage subjects.
- [x] **Keep frozen verification non-mutating (`ss-lp5a`).** Suppress Python bytecode
  writes while the transferred driver imports its candidate-local helpers, then restore
  the interpreter setting.
  Prove in a subprocess with default bytecode behavior that a fresh candidate verifies
  its exact inventory without creating `.pyc` or `__pycache__` nodes; continue rejecting
  every genuinely unexpected node.
- [x] **Bound every schema-file read (`ss-tpr2`).** Route `SchemaView`, compile drift
  checks, validation, and diagnostic reloads through shared limit-plus-one readers in
  both runtimes; resolve the complete path once, reject non-regular targets before open,
  bind the descriptor to the inspected device/inode, loop short reads, and decode strict
  UTF-8. Carry a document-declared schema’s authorized canonical path and identity from
  containment into the read; reject parent substitution before it can redirect the
  schema. Prove oversized and special files stop before whole-file allocation or
  blocking, and reject compiler output that its own bounded readers could not reopen.
- [x] **Make source-resource tests installation-independent (`ss-1v5i`).** Bind the
  exact-checkout fixture to the source module path explicitly so wheel-first CI and
  editable runs test the same source-versus-bundle trust decision.
- [x] **Make portable glob matching iterative (`ss-dku3`).** Replace recursive segment
  and globstar matchers in Python and TypeScript with bounded dynamic programming, and
  execute shared long-pattern and long-path vectors without stack exhaustion.
- [x] **Replace regex backtracking with bounded linear engines (`ss-7ykr`).** Parse the
  shared `portable-regex-v1` grammar within explicit pattern, group, and automaton
  budgets; execute pattern, pattern-properties, additional-property, and
  unevaluated-property checks through Thompson-style engines in both runtimes; and prove
  nested repetition plus deep groups cannot trigger native-engine ReDoS or stack leaks.
- [x] **Bound retained lazy-DFA subsets (`ss-9zsj`).** Cap per-engine and aggregate
  cached NFA-state membership as well as state and transition counts; stop caching or
  evict before retained subset arrays can amplify memory across the 32-entry cache, and
  cover the adversarial accepted pattern in both runtimes.
- [x] **Validate the final compiled sidecar (`ss-84vm`).** Reapply the portable budget
  after inserting the digest field, distinguish JSON booleans from integers in Python
  drift checks, use canonical JSON as the cross-writer byte acceptance criterion, and
  write exact LF-normalized UTF-8 bytes on Windows.
- [x] **Carry the validated schema source into diagnostics (`ss-clz0`).** Bind size,
  mtime, and ctime as well as path/device/inode; retain the exact source map produced by
  the schema bytes used for structural validation; and consume that map without a second
  diagnostic read or any new public wire field.
- [x] **Make wildcard segment matching linear (`ss-v2h3`).** Replace the quadratic
  segment bitset with the bounded exact prefix/interior/suffix algorithm, define the
  shared interior-complexity limit and stable invocation error, and prove the long
  adversarial shapes scale as `O(pattern + C * path)` in both runtimes.
- [x] **Enforce YAML construction budgets incrementally (`ss-i32z`).** Drive the
  TypeScript lexer/parser token by token, stop CST node/depth growth at the configured
  limits, retain syntax precedence with bounded lookahead, and preserve exact semantic
  node thresholds.
- [x] **Complete Unicode-scalar traversal ordering (`ss-kfnc`).** Use the shared scalar
  comparator for parity-visible pattern scans, structural records, materialized object
  traversal, resource registration, and portable sizing; cover astral-versus-BMP keys.
- [x] **Align multiline flow-pair spans (`ss-n7m1`).** Extend implicit flow-mapping
  spans through trailing newline tokens so Python and TypeScript share the mapping-end
  event boundary and exact source-location vectors.
- [x] **Align release-manifest size policy (`ss-c8ix`).** Enforce the runtime 512 MiB
  per-subject ceiling in the schema, document the 1 GiB aggregate semantic invariant,
  and test schema/runtime agreement at both sides of the boundary.
- [x] **Qualify legacy JSON compatibility (`ss-j2ps`).** Limit the single-result claim
  to one single explicit path classified as regular during discovery, including later
  read failures, plus the narrow `not_found` exception; document the diagnostic
  aggregate used for every other discovery-input failure.
- [x] **Reject every non-regular frozen-candidate node (`ss-96ih`).** Authenticate the
  checksum file and each subject through descriptor-bound regular-file reads, traverse
  parents without following POSIX links or Windows reparse redirects, stream bounded
  bytes, bound actual traversal and generated inventory output, and reject empty or
  hidden inventory nodes.
  In unprivileged smoke jobs, run the exact-commit checkout verifier before any
  transferred driver or helper; prove final-file and parent-directory swaps cannot
  redirect verification.
- [x] **Use fresh Windows candidate identities (`ss-6crf`).** Do not retain
  `DirEntry.stat()` identity fields, which are documented as zero on Python 3.11 for
  Windows. Use a fresh path `lstat()` for redirect/type admission, retain authenticated
  descriptor metadata for stability comparisons, and prove the inventory neither
  consults cached directory-entry identity nor compares path and descriptor timestamp
  representations.
- [x] **Force UTF-8 installed-artifact smoke (`ss-wepj`).** Set `PYTHONIOENCODING=utf-8`
  and `PYTHONUTF8=1` for every smoke subprocess so bundled Unicode docs preserve exact
  bytes under Windows console code pages; prove it with a real child process under a
  hostile inherited ASCII setting.
- [x] **Resolve the npm launcher portably (`ss-ap9s`).** Resolve `npm` through `PATH`
  before strict non-shell subprocess execution so Windows selects `npm.cmd`; reject a
  missing launcher explicitly and cover both paths with focused tests.
- [x] **Preserve exact CLI example bytes (`ss-07xe`).** Verify the installed schema
  topic alongside the other bundled examples and materialize Python and npm CLI output
  with explicit UTF-8 bytes so Windows newline translation cannot alter validation
  input.
- [x] **Separate path and descriptor snapshots (`ss-zlhf`).** Keep bounded-file name
  authorization path-to-path and compare opened/final read stability
  descriptor-to-descriptor in both runtimes, avoiding false Windows drift without
  weakening identity, size, mutation, or parent-substitution checks.
- [x] **Use supported Node Windows open flags (`ss-j64g`).** Restrict Windows to
  Node-documented file-open flags while retaining canonical path and descriptor identity
  checks; keep no-follow and nonblocking flags on POSIX and test platform selection.
- [x] **Isolate legacy libuv Windows identity (`ss-b8lx`).** For Node 22.12’s libuv
  1.49.1, which predates upstream fixes to the Windows
  [stat field order](https://github.com/libuv/libuv/commit/abe59d6319973cbff0686f41869cf8ae50bab1d2)
  and
  [volume serial handling](https://github.com/libuv/libuv/commit/82cdfb75ff9bbd0dc65820ca418b7c5d412ff4d7),
  version-gate only the unreliable path-to-descriptor ID comparison.
  Preserve exact size, path-to-path authorization, descriptor-to-descriptor stability,
  canonical path checks, and the Windows second read.
- [x] **Bound every frozen release-driver read and verify before execution
  (`ss-bcdi`).** Route manifests, controls, subjects, and npm fixtures through
  descriptor-bound limit-plus-one reads with explicit per-format budgets.
  Require the exact-checkout verifier to run before the first transferred helper in
  every consumer, and prove growth, oversized controls, and workflow-order regressions
  fail closed.
- [x] **Descriptor-bind remaining release-state reads (`ss-xsp8`).** Route JSON parsing
  through the explicit-budget regular-file reader and bind streaming recovery/asset
  hashes to lstat/open/fstat/path identity plus stable metadata; reject replacement,
  growth, special nodes, and Windows second-pass drift.
- [x] **Keep the post-open limit regression cross-version (`ss-yodf`).** Mock the
  lstat/fstat identity boundary consistently so Python 3.11–3.14 all exercise the
  limit-plus-one read instead of a version-dependent `Path.stat()` delegation detail.
- [x] **Correct the release-checkout review claim (`ss-ud65`).** State that registry
  jobs check out only the exact preflight commit for the trusted verifier and do not
  resolve dependencies, rebuild, or execute candidate lifecycle scripts.
- [x] **Bound skill-installer inspection reads (`ss-2upc`).** Apply one shared 1 MiB
  managed-skill byte ceiling to target, stage, and backup inspection in both runtimes.
  Read regular files through limit-plus-one descriptor checks, give installer locks a
  separate 4 KiB ceiling, treat oversized or replaced nodes as non-mutating conflicts,
  and cover dry-run plus repair parity.
- [x] **Align YAML property-token locations (`ss-3i41`).** Associate composed scalars
  and collections with their CST tag property so custom-tag diagnostics select the same
  source coordinate in Python, Node, and Bun.
- [ ] **Provision the GitHub release approval gate (`ss-8dt9`).** Create or re-read the
  `github-release` environment with a `v*` deployment restriction, required reviewer,
  and no administrator bypass before any protected-tag execution; preserve the
  authenticated configuration evidence.
- [ ] **Verify live release authorization (`ss-0rqn`).** Merge the final candidate
  through a protected PR with every required context, run the manual preflight, verify
  the exact PyPI/npm trusted-publisher and protected-environment configuration while
  authenticated, and record durable repository, environment, ruleset, and workflow
  evidence. This external-state gate is separate from `ss-o21w` so credentials do not
  block the code-side conformance dependency graph.
- [x] **Implement idempotent release orchestration (`ss-g8m8`).** Add standalone
  manifest-driven GitHub/PyPI/npm state classifiers, a draft-assets and attestation
  stage, conditional exact-byte uploads, final-release gating, and post-publish
  verification hooks. Privileged jobs check out only the exact preflight commit for the
  trusted verifier, then consume the frozen transfer without dependency resolution or
  rebuilding; live authorization and publication remain separate gates.
- [x] **Require retry postconditions (`ss-prjf`).** Retain a complete registry decision
  only after its required publisher/provenance postcondition succeeds; exhaust the
  bounded retry window and fail closed when metadata never qualifies.
- [ ] **Publish and recover idempotently (`ss-trn7`).** Publish the immutable preflight
  artifacts through separate protected PyPI, npm, and GitHub-assets jobs; classify
  absent/complete/partial/conflicting artifact sets by filename and digest; guard
  discovery, artifact-format, and conformance versions; preserve dry-run behavior; roll
  forward after a partial release; and run post-publish verification.
- [ ] **Close the plan (`ss-1mdr`).** After release verification, update this plan to
  Implemented, move it to the completed-spec convention, update linked spec paths, and
  close `ss-22fi`.

**Phase gate:** the standalone kit validates under every official runtime; installed
wheel and npm tarball pass from clean and adversarial directories; docs commands run
verbatim; deterministic skill checks and dated activation observations pass; release dry
run succeeds; every primary GitHub asset matches the manifest and every derived
control/attestation record verifies; PyPI/npm versions and stable/prerelease channels
map to one logical release coordinate while each artifact matches its own manifest
digest; and post-publish provenance and zero-install smoke tests pass.

## Dependency Map

Only genuine blockers become tbd dependencies; phase order alone does not serialize
independent security work.

| Bead | Depends On | Reason |
| --- | --- | --- |
| `ss-dbkh` | `ss-pvxi` | Freeze the portable schema-error contract before implementing it. |
| `ss-pvu9` | `ss-pvxi` | Artifact parse/access failures use the same public result foundation. |
| `ss-0sgk` | `ss-dbkh` | Offline reference failures need the stable schema-error boundary. |
| `ss-l41u` | `ss-dbkh`, `ss-pvu9` | Artifact and schema YAML share the normalized parser/error boundary. |
| `ss-1aa6` | `ss-slas`, `ss-pvxi` | Bootstrap claims need verified agent paths and the public doctor-result schema. |
| `ss-bj47` | `ss-slas` | Installer selectors and destinations come from the verified agent matrix. |
| `ss-o21w` | `ss-pvxi` | Release/doctor schemas are added to the shared draft foundation before CI consumes them. |
| `ss-vn04` | `ss-pvxi`, `ss-dbkh` | The public pattern result and schema-loading boundary precede regex-profile convergence. |
| `ss-k381` | `ss-pvxi`, `ss-dbkh` | The result foundation and loader precede the 0.3 format-policy convergence. |
| `ss-sbvh` | `ss-dbkh`, `ss-l41u` | Canonicalization/enforcement relies on valid schema objects and portable values. |
| `ss-yxfm` | `ss-pvxi` | Identity decisions finalize the draft compiler-profile schema. |
| `ss-1yt7` | `ss-yxfm` | Nested resource identity follows the settled separation between contract IDs and schema resource IDs. |
| `ss-3n2k` | `ss-l41u`, `ss-sbvh` | Schema views and envelope inference consume settled values and schema traversal. |
| `ss-wuva` | `ss-pvxi`, `ss-l41u`, `ss-yxfm` | Metadata and extensions extend the conformance foundation after value and identity rules settle. |
| `ss-rpq0` | `ss-wuva`, `ss-j81s` | The single metadata grammar replaces the settled unmerged discriminator across public and standalone boundaries. |
| `ss-0uj9` | `ss-dbkh`, `ss-l41u`, `ss-vn04`, `ss-k381`, `ss-sbvh`, `ss-yxfm`, `ss-wuva`, `ss-1yt7` | Extract the core after its boundaries, identities, semantics, formats, and nested-resource ownership are defined. |
| `ss-6jp1` | `ss-l41u`, `ss-yxfm`, `ss-wuva` | Do not expose more YAML until values, binding IDs, and metadata versions are portable. |
| `ss-b5l4` | `ss-pvxi`, `ss-0uj9`, `ss-yxfm` | Runtime contracts and wire types implement the frozen public result schemas on the portable core. |
| `ss-u30p` | `ss-l41u`, `ss-0uj9` | Serialization consumes the settled portable value domain and extracted core before batch wire formats depend on it. |
| `ss-hwws` | `ss-sbvh`, `ss-u30p` | Cross-runtime compiler hashes consume both settled schema transforms and the portable serializer/value representation. |
| `ss-2d33` | `ss-sbvh`, `ss-hwws` | The reserved root metadata block is enforced after compiler transforms and portable hashing settle. |
| `ss-fbtq` | `ss-pvxi`, `ss-2d33` | Authoring helpers must emit only annotations accepted by the finalized compiler-owned profile. |
| `ss-0tb1` | `ss-l41u` | Source separator policy extends the settled portable YAML boundary. |
| `ss-y82x` | `ss-l41u` | Key-level source anchors require the settled YAML source map. |
| `ss-qu2u` | `ss-l41u` | Composer exceptions must terminate at the shared portable parser boundary. |
| `ss-dz2o` | `ss-l41u` | Compact-flow policy narrows the settled portable YAML grammar. |
| `ss-23yg` | `ss-l41u`, `ss-xnr6` | Empty-node anchors build on the parser source map and positioned diagnostic contract. |
| `ss-zknx` | `ss-l41u` | Bounded file allocation enforces the existing portable resource-byte policy at the adapter boundary. |
| `ss-xnr6` | `ss-pvu9`, `ss-0uj9`, `ss-6jp1`, `ss-b5l4`, `ss-u30p`, `ss-0tb1`, `ss-y82x` | Batch and locations need settled access precedence, core results, profiles, wire types, byte-identical serialization, and portable source anchors. |
| `ss-3o3w` | `ss-xnr6` | The positioned diagnostic implementation must exist before its source-index complexity can be hardened. |
| `ss-yn4e` | `ss-xnr6` | The batch discovery surface must exist before traversal can gain shared identity and resource budgets. |
| `ss-tge8` | `ss-pvxi`, `ss-o21w` | Standalone publication and consumer boundaries build on the conformance and frozen-artifact foundations. |
| `ss-o04h` | `ss-tge8`, `ss-g8m8` | Every standalone JSON boundary must exist before its Unicode/depth/node failures can be closed consistently. |
| `ss-j81s` | `ss-tge8`, `ss-o04h` | Operation-specific adapter validation closes the strict standalone boundary after its generic JSON defenses exist. |
| `ss-gr29` | `ss-j81s` | Explicit boolean rejection documents and locks down the settled operation-specific limit contract. |
| `ss-oyr4` | `ss-tge8` | Immutable Pages publication consumes the hostile-input-tested publication boundary. |
| `ss-6i6d` | `ss-0sgk`, `ss-dbkh`, `ss-l41u`, `ss-yxfm`, `ss-sbvh`, `ss-6jp1`, `ss-o21w`, `ss-b5l4`, `ss-xnr6`, `ss-0uj9`, `ss-wuva`, `ss-pvu9`, `ss-pvxi`, `ss-vn04`, `ss-k381`, `ss-1yt7`, `ss-u30p`, `ss-hwws`, `ss-2d33`, `ss-fbtq`, `ss-tge8`, `ss-oyr4`, `ss-o04h`, `ss-zknx`, `ss-3o3w`, `ss-qu2u`, `ss-dz2o`, `ss-yn4e`, `ss-23yg`, `ss-stbo`, `ss-4uki`, `ss-ej3x`, `ss-jfat`, `ss-ycm4`, `ss-6okz`, `ss-j81s`, `ss-tpr2`, `ss-dku3`, `ss-i32z`, `ss-kfnc`, `ss-n7m1`, `ss-1v5i`, `ss-3i41`, `ss-7ykr`, `ss-84vm`, `ss-clz0`, `ss-v2h3`, `ss-bcdi`, `ss-2upc`, `ss-9zsj` | Fill and package the public foundation only after every represented behavior and artifact boundary settles. |
| `ss-v6bv` | `ss-0sgk`, `ss-7eoa`, `ss-dbkh`, `ss-l41u`, `ss-yxfm`, `ss-sbvh`, `ss-6jp1`, `ss-1aa6`, `ss-bj47`, `ss-o21w`, `ss-b5l4`, `ss-3n2k`, `ss-xnr6`, `ss-0uj9`, `ss-wuva`, `ss-pvu9`, `ss-pvxi`, `ss-vn04`, `ss-slas`, `ss-srtz`, `ss-k381`, `ss-1yt7`, `ss-hwws`, `ss-2d33`, `ss-zknx`, `ss-qu2u`, `ss-dz2o`, `ss-yn4e`, `ss-23yg` | Final information architecture describes the exact settled candidate and labels unavailable live state explicitly. |
| `ss-66i9` | `ss-v6bv` | The activation claim follows the settled compatibility matrix and shared fixture shape. |
| `ss-azpv` | `ss-v6bv` | Research completion markers follow the implemented public documentation decisions. |
| `ss-bhz6` | `ss-b5l4`, `ss-v6bv` | The final TypeScript gate measures settled package source without counting transient integration copies as duplicate source files. |
| `ss-tpr2` | `ss-zknx` | Every remaining schema-file consumer must use the settled bounded-read boundary before the kit can close. |
| `ss-1v5i` | `ss-7eoa` | Wheel-first tests must select source or bundled resources from an explicit module identity rather than the ambient installation mode. |
| `ss-dku3` | `ss-yn4e` | Iterative glob evaluation closes the discovery surface after filesystem traversal limits settle. |
| `ss-7ykr` | `ss-vn04` | The bounded linear engine implements the already frozen portable-pattern language. |
| `ss-9zsj` | `ss-7ykr` | Retained-subset accounting closes the lazy-DFA memory boundary after engine semantics settle. |
| `ss-84vm` | `ss-hwws`, `ss-tpr2` | Final sidecar budgeting follows canonical hashing and the bounded reopen contract. |
| `ss-clz0` | `ss-xnr6`, `ss-tpr2` | Exact schema locations consume positioned diagnostics and identity-bound file reads. |
| `ss-v2h3` | `ss-dku3` | The bounded exact matcher hardens the already iterative glob surface. |
| `ss-bcdi` | `ss-96ih` | The frozen driver consumes only transfers already covered by descriptor-bound inventory verification. |
| `ss-xsp8` | `ss-bcdi`, `ss-96ih` | Remaining JSON and streaming-hash readers reuse the settled driver and inventory identity boundaries. |
| `ss-6crf` | `ss-96ih` | Windows 3.11 inventory identity reuses the settled exact regular-file boundary without trusting zero-valued directory-entry fields. |
| `ss-wepj` | `ss-o21w` | Deterministic Unicode subprocess output closes the cross-platform installed-artifact smoke boundary. |
| `ss-ap9s` | `ss-wepj` | Portable npm launcher resolution completes the Windows installed-artifact smoke path after deterministic decoding. |
| `ss-07xe` | `ss-wepj` | Exact CLI-output bytes complete the Windows installed schema round trip after deterministic decoding. |
| `ss-zlhf` | `ss-96ih` | Shared bounded readers apply the descriptor-snapshot rule already proven at the frozen candidate boundary. |
| `ss-j64g` | `ss-zlhf` | Platform-supported open flags complete the Node 22 Windows bounded-reader path. |
| `ss-b8lx` | `ss-zlhf` | A narrow compatibility gate isolates upstream legacy-libuv identity defects without weakening interface-local snapshots. |
| `ss-yodf` | `ss-xsp8` | The post-open limit regression follows the settled descriptor reader on every supported Python version. |
| `ss-ud65` | `ss-bcdi` | Release-review wording follows the exact-checkout trusted-verifier design. |
| `ss-2upc` | `ss-bj47` | Bounded inspection hardens the settled non-clobbering installer transaction. |
| `ss-i32z` | `ss-l41u` | Incremental CST construction enforces the settled portable-YAML node and depth budgets before allocation. |
| `ss-kfnc` | `ss-vn04`, `ss-ycm4` | Every parity-visible schema traversal reuses the settled portable-pattern and canonical Unicode ordering. |
| `ss-n7m1` | `ss-xnr6`, `ss-23yg` | Multiline flow-pair spans extend the positioned diagnostic and implicit-null source contracts. |
| `ss-8dt9` | — | The protected GitHub release environment is an external live-state prerequisite rather than a code dependency. |
| `ss-0rqn` | `ss-o21w`, `ss-v6bv`, `ss-6i6d`, `ss-8dt9` | Live authorization and a real preflight require the complete candidate and protected GitHub release environment but are external to the code-side artifact boundary. |
| `ss-g8m8` | `ss-o21w` | The code-side release state machines extend the already hardened frozen-artifact boundary without requiring live credentials. |
| `ss-prjf` | `ss-g8m8` | Retry success must require the provenance postcondition owned by the release state machine. |
| `ss-jfat` | `ss-l41u` | Final YAML differential cases extend the settled portable value boundary. |
| `ss-ycm4` | `ss-u30p`, `ss-hwws` | Canonical schema set ordering uses the same Unicode scalar order as serialization and hashing. |
| `ss-ihzl` | `ss-zknx` | Metadata schema confinement must precede the bounded file read. |
| `ss-stbo` | `ss-tge8` | Exact archive tree ownership tightens the standalone consumer boundary. |
| `ss-6okz` | `ss-stbo` | Declared byte budgets apply after the exact inventory contract exists. |
| `ss-4uki` | `ss-oyr4` | Monotonic promotion extends the immutable Pages gate. |
| `ss-ej3x` | `ss-4uki` | Complete namespace hydration preserves every previously promoted path. |
| `ss-a43v` | `ss-g8m8` | Exact certificate identity is a release provenance postcondition. |
| `ss-x6iq` | `ss-g8m8`, `ss-1aa6` | Candidate coordinates and published bootstrap discovery have different state owners. |
| `ss-ap6l` | `ss-g8m8` | Durable recovery extends the frozen draft-asset state machine. |
| `ss-3x0g` | `ss-ap6l` | The durable recovery bootstrap must bind to the exact workflow commit before execution. |
| `ss-qezc` | `ss-ap6l` | Recovery extraction budgets extend the durable archive boundary before filesystem writes. |
| `ss-1mf4` | `ss-ap6l` | Recovery checksum contents must be authenticated before a parser consumes them. |
| `ss-pykr` | `ss-g8m8` | Final publication must re-evaluate immutable-release policy immediately before mutation. |
| `ss-23vm` | `ss-g8m8` | Latest-channel verification is a final GitHub state-machine postcondition. |
| `ss-2t5m` | `ss-g8m8` | Manifest byte budgets bound every release-state read and download. |
| `ss-1157` | `ss-prjf` | Retry postconditions also require a finite bounded delay. |
| `ss-lp5a` | `ss-o21w` | The downloaded-candidate verifier extends the frozen artifact boundary and must not mutate the inventory it authenticates. |
| `ss-96ih` | `ss-lp5a` | Exact transferred-candidate verification must classify every node and bind every read to an authenticated regular-file path. |
| `ss-c8ix` | `ss-tge8`, `ss-g8m8` | Release-manifest schema limits must match the standalone boundary and release state machine before publication. |
| `ss-j2ps` | `ss-v6bv`, `ss-xnr6` | The final compatibility wording follows the settled documentation and diagnostic-output behavior. |
| `ss-3i41` | `ss-l41u`, `ss-xnr6` | YAML property-token locations build on the portable parser and positioned diagnostic contract. |
| `ss-trn7` | `ss-o21w`, `ss-v6bv`, `ss-6i6d`, `ss-0rqn`, `ss-g8m8`, `ss-prjf`, `ss-a43v`, `ss-x6iq`, `ss-ap6l`, `ss-23vm`, `ss-2t5m`, `ss-1157`, `ss-3x0g`, `ss-pykr`, `ss-qezc`, `ss-1mf4`, `ss-8dt9`, `ss-bhz6`, `ss-lp5a`, `ss-c8ix`, `ss-96ih`, `ss-xsp8`, `ss-ud65`, `ss-6crf`, `ss-wepj`, `ss-yodf`, `ss-ap9s`, `ss-07xe`, `ss-zlhf`, `ss-j64g`, `ss-b8lx`, `ss-rpq0` | Publish only after artifacts, public docs, conformance metadata, live authorization, idempotent orchestration, every final release-boundary closure, and the complete TypeScript gate are ready. |
| `ss-1mdr` | `ss-qq77`, `ss-trn7`, `ss-nsto`, `ss-9tx6`, `ss-uywa`, `ss-22gw`, `ss-2n7g`, `ss-ode8`, `ss-ihzl`, `ss-6a90`, `ss-vnul`, `ss-yaii`, `ss-75lu`, `ss-fj2k`, `ss-j81s`, `ss-j2ps`, `ss-66i9` | Close tracking only after release verification, final adapter validation, every documentation correction, and historical cleanup. |
| `ss-22fi` | `ss-1mdr` | The epic cannot become ready until its post-release closeout child is complete. |

`ss-pvxi`, `ss-7eoa`, `ss-slas`, `ss-srtz`, and `ss-qq77` may begin in parallel.
`ss-dbkh` and `ss-o21w` start as soon as the result/release foundation is frozen;
bootstrap and installer work starts when the agent matrix is verified, and bootstrap
also consumes the doctor-result foundation.
The schema/network work should be one vertical release slice even though it closes two
beads.

## Testing Strategy

### Red-Green Workflow

For every specified cross-runtime behavior:

1. Add one minimal shared failing fixture or conformance case.
2. Add only the per-runtime unit tests needed for properties the CLI corpus cannot
   observe, such as zero network calls or resource lookup precedence.
3. Implement Python, run its focused test and corpus.
4. Port the same semantics to TypeScript, run Node and Bun.
5. Run the direct cross-implementation comparison.
6. Refactor only after all paths are green.

Do not update a golden merely to make a failure disappear.
Review every changed output as a behavioral contract.

### Required Coverage

- Schema failures: malformed syntax, invalid root, invalid keyword, dialect, reference,
  regex, format annotation, resource `$id` mismatch/collision, relative reference bases,
  boolean supplied resources, and no-network interception.
- YAML domain: both artifact profiles, duplicate/non-string keys, timestamps, tags,
  aliases, merge keys, cycles, non-finite and boundary numbers, every negative-zero
  spelling, Unicode, CRLF/BOM, every default/overridden resource limit, and parse spans
  captured before materialization.
- Patterns: accepted grammar/shared-engine cases plus Python/ECMA-262 differences for
  syntax, matching, Unicode, anchors, escapes, classes, lookarounds, backreferences,
  flags, and warning-free rejection.
- Canonicalization: nullable positive/negative cases, every supported applicator,
  boolean subschemas, composed objects, strictness opt-outs, `enforcement_unsupported`,
  portable-domain raw/canonical equivalence, and hash equality.
- Identity: valid/invalid IDs at metadata, API, registry, CLI, and compiler entrypoints;
  schema URI validation; no write on failure.
- Resources/skills: clean wheel/tarball, adversarial cwd collisions, source drift,
  agent/destination/scope matrix, canonical-path and worktree/submodule cases,
  ownership/prior-digest matrix, concurrent installers, dry-run non-mutation, permission
  failure, recoverable rollback, injected process-kill residue, and idempotent repair.
- CLI: Python/Node/Bun help and exit parity, both profiles, batch ordering, JSONL,
  readable parse failures, mixed missing/unreadable paths, partial failures, legacy JSON
  wire stability, diagnostic-v1 JSON/JSONL, SARIF, pipes/EPIPE, Node/Bun model modules,
  and Windows paths.
- Conformance: every manifest path and digest, every schema metaschema-valid,
  deterministic archive bytes, and a consumer that uses only public kit files.
- Docs: links, footers, shell snippets, stale-version/pin and public-claims matrices,
  paired model compile equality, bundled-topic coverage, migration notes, README
  quickstart from an empty directory, primary-source research citations, agent
  compatibility/discovery records, and skill mirrors/validation.
- Release: frozen installs, dependency audit, logical/build metadata schemas, exact
  tag/version mapping, SPDX SBOMs, GitHub attestations, manifest hashes, workflow dry
  run, each registry state/recovery branch, provenance verification, and post-publish
  zero-install smoke tests on the supported OS/runtime matrix.

### Full Gates

```bash
uv run python devtools/lint.py --check
uv run pytest
uv build

cd packages/typescript
bun install --frozen-lockfile
bun run check
bun run build
bun run publint
bun audit --audit-level=moderate

cd ../..
SOFTSCHEMA_IMPL=py bash tests/golden/run.sh
SOFTSCHEMA_IMPL=ts bash tests/golden/run.sh
SOFTSCHEMA_IMPL=ts-bun bash tests/golden/run.sh
bash tests/golden/cross-impl-diff.sh
```

Add the conformance-kit runner, package-install smoke runner, skill validator, docs
snippet runner, and publish dry-run to this gate as they land.

## Rollout Plan

- The separate 0.2.x patch proposed in the first draft was not cut before Phase-2 work
  landed. Do not reconstruct it from mixed commits or claim that it shipped.
  Deliver the security fixes in the consolidated 0.3.0 candidate, disclose the affected
  0.2.2 boundaries, and keep publication blocked until the protected publisher dry run
  and risk review pass.
- Phase 2 is the behavioral boundary for 0.3.0. Update the spec and compatibility table
  first, land one compiler/hash rebaseline, and freeze the core semantics.
  It is not yet a release candidate.
- Phase 3 completes before the 0.3.0 public release.
  A fully independent additive item may move only through an explicit reviewed epic/spec
  update with its own tracked compatibility and release gate; do not silently drop work
  from this epic. Freeze the release candidate only after all Phase-3 implementation/docs
  checks pass.
- The release preflight builds immutable wheel, sdist, npm tarball, and conformance
  archive artifacts once.
  Registry jobs publish those exact bytes.
- If one registry succeeds and the other fails, preserve the successful release and
  rerun only the missing publish after verifying the existing digest.
  Never unpublish or replace a released artifact.
- After both registries publish, validate the documented pinned `uvx`, `npx --yes`, and
  `bunx --bun` paths from neutral directories, verify package/kit digests and
  provenance, and only then mark the plan Implemented and close the epic.

## Bead Map

| Bead | Priority | Scope |
| --- | --- | --- |
| `ss-22fi` | P1 | Parent remediation epic |
| `ss-pwkr` | P1 | Write and maintain this plan |
| `ss-pvxi` | P1 | Bootstrap draft conformance schemas and shared runner |
| `ss-dbkh` | P1 | Structured malformed-schema failures |
| `ss-pvu9` | P1 | Structured artifact parse/access failures and exit precedence |
| `ss-0sgk` | P1 | No implicit remote reference retrieval |
| `ss-7eoa` | P1 | Trusted packaged resource lookup |
| `ss-slas` | P1 | Verified major coding-agent discovery/installer matrix |
| `ss-1aa6` | P1 | Reproducible, standards-conformant skill bootstrap |
| `ss-bj47` | P1 | Explicit-scope, non-clobbering skill install |
| `ss-o21w` | P1 | Hardened CI and pre-publish artifact boundary |
| `ss-l41u` | P1 | Bounded portable YAML value semantics |
| `ss-vn04` | P1 | Portable JSON Schema regular-expression semantics |
| `ss-k381` | P2 | Annotation-only JSON Schema format semantics |
| `ss-sbvh` | P1 | Semantics-preserving canonicalization/enforcement |
| `ss-yxfm` | P2 | Contract-ID and schema-ID boundaries |
| `ss-wuva` | P2 | Closed artifact metadata and extension namespaces |
| `ss-rpq0` | P1 | Single authored version string and one metadata grammar |
| `ss-3n2k` | P2 | SchemaView and artifact edge cases |
| `ss-0uj9` | P2 | Portable core/runtime/CLI separation |
| `ss-6jp1` | P2 | Pure-YAML CLI profile |
| `ss-b5l4` | P2 | TypeScript runtime contracts, model policy, exits, wire types |
| `ss-1yt7` | P1 | Nested JSON Schema resource identity and collision handling |
| `ss-u30p` | P1 | Byte-identical deterministic JSON serialization |
| `ss-hwws` | P1 | Portable numeric normalization for compiler hashes |
| `ss-2d33` | P1 | Reserved root compiler metadata and profile validity |
| `ss-fbtq` | P1 | Cross-runtime field-annotation authoring validation |
| `ss-0tb1` | P1 | Portable literal YAML separator and source-position policy |
| `ss-y82x` | P2 | Offending-key source anchors for extra-property diagnostics |
| `ss-qu2u` | P1 | Coded YAML exception and Node filesystem-error classification |
| `ss-dz2o` | P1 | Portable compact-flow YAML policy |
| `ss-23yg` | P1 | Empty-null source anchors |
| `ss-zknx` | P1 | Bounded artifact and schema file reads |
| `ss-3o3w` | P1 | Scalable TypeScript source indexing |
| `ss-yn4e` | P1 | Iterative, identity-aware, bounded recursive discovery |
| `ss-xnr6` | P2 | Batch validation, locations, and SARIF |
| `ss-tge8` | P2 | Hostile conformance publication and consumer boundaries |
| `ss-o04h` | P1 | Strict Unicode-safe standalone JSON boundaries |
| `ss-j81s` | P1 | Operation-specific standalone adapter request validation |
| `ss-gr29` | P1 | Explicit cross-runtime rejection of boolean conformance limits |
| `ss-oyr4` | P1 | Immutable, release-capable Pages namespace |
| `ss-6i6d` | P2 | Versioned conformance kit, vocabulary, bundles, evolution |
| `ss-srtz` | P2 | Related-effort research and strategic positioning |
| `ss-v6bv` | P2 | Documentation and agent surfaces |
| `ss-66i9` | P3 | Accurate activation-fixture coverage wording |
| `ss-azpv` | P3 | Completed research follow-up markers |
| `ss-bhz6` | P1 | Stable package-source TypeScript coverage gate |
| `ss-lp5a` | P1 | Non-mutating transferred-candidate checksum verification |
| `ss-tpr2` | P1 | Bounded SchemaView and compile-drift file reads |
| `ss-1v5i` | P1 | Installation-independent source-resource trust test |
| `ss-dku3` | P1 | Iterative portable glob matching |
| `ss-7ykr` | P1 | Bounded linear portable-regex engines |
| `ss-9zsj` | P1 | Bounded retained lazy-DFA subset membership |
| `ss-84vm` | P1 | Final compiled-sidecar budget and byte invariants |
| `ss-clz0` | P2 | Exact validated-schema source maps in diagnostics |
| `ss-v2h3` | P2 | Bounded linear wildcard segment matching |
| `ss-bcdi` | P1 | Bounded frozen-driver reads and pre-execution verification |
| `ss-xsp8` | P1 | Descriptor-bound release-state JSON and streaming-hash reads |
| `ss-ud65` | P2 | Accurate exact-checkout release-review wording |
| `ss-2upc` | P2 | Bounded skill-installer target and residue inspection |
| `ss-i32z` | P2 | Incremental TypeScript YAML construction budgets |
| `ss-kfnc` | P2 | Complete Unicode-scalar traversal ordering |
| `ss-n7m1` | P2 | Multiline flow-mapping source-span parity |
| `ss-c8ix` | P2 | Release-manifest/runtime size-policy agreement |
| `ss-j2ps` | P3 | Qualified legacy single-file JSON compatibility |
| `ss-96ih` | P1 | Descriptor-bound exact frozen-candidate inventory |
| `ss-6crf` | P1 | Fresh Windows 3.11 candidate inventory identity |
| `ss-wepj` | P1 | UTF-8 installed-artifact smoke subprocesses |
| `ss-ap9s` | P1 | Portable Windows npm launcher resolution |
| `ss-07xe` | P1 | Exact Windows artifact-smoke CLI bytes |
| `ss-zlhf` | P1 | Windows-safe bounded-reader descriptor snapshots |
| `ss-j64g` | P1 | Node 22 Windows-supported bounded-reader open flags |
| `ss-b8lx` | P1 | Legacy libuv Windows stat-identity compatibility |
| `ss-yodf` | P2 | Cross-version post-open byte-limit regression |
| `ss-3i41` | P2 | YAML property-token diagnostic locations |
| `ss-qq77` | P2 | Tracker and completed-spec reconciliation |
| `ss-8dt9` | P1 | Protected live `github-release` environment |
| `ss-0rqn` | P1 | Live publisher authorization, protected PR, and preflight evidence |
| `ss-g8m8` | P1 | Idempotent release state machines and draft-asset DAG |
| `ss-prjf` | P1 | Release retry provenance postconditions |
| `ss-trn7` | P1 | Idempotent dual-registry publication and verification |
| `ss-1mdr` | P2 | Post-release plan and epic closeout |
| `ss-c305` | P1 | Regenerate native agent instruction adapters |
| `ss-nsto` | P1 | Location-correct generated Copilot links |
| `ss-9tx6` | P1 | Evidence-calibrated trusted-publisher documentation |
| `ss-a43v` | P1 | Exact npm X.509 source identity |
| `ss-stbo` | P2 | Exact bounded extracted-kit tree inventory |
| `ss-uywa` | P2 | Intentional skill-brief golden rebaseline |
| `ss-22gw` | P2 | Accurate golden coverage and exit-code docs |
| `ss-2n7g` | P1 | Extracted-archive consumer instructions |
| `ss-ode8` | P2 | Complete plan/bead reconciliation |
| `ss-ihzl` | P1 | Metadata-schema symlink confinement |
| `ss-4uki` | P1 | Monotonic Pages promotion marker |
| `ss-ej3x` | P2 | Complete append-only Pages namespace |
| `ss-6a90` | P2 | Idiomatic host-library parity explanations |
| `ss-vnul` | P2 | Shell-safe publishing commands |
| `ss-ap6l` | P1 | Durable attested release recovery |
| `ss-3x0g` | P1 | Exact-commit recovery bootstrap verification |
| `ss-pykr` | P1 | Immediate pre-publication immutable-release recheck |
| `ss-qezc` | P1 | Pre-write recovery depth and implied-directory budgets |
| `ss-1mf4` | P1 | Pre-parse recovery checksum authentication |
| `ss-yaii` | P2 | Registry README versions versus source pins |
| `ss-x6iq` | P1 | Candidate versions versus verified bootstrap pins |
| `ss-23vm` | P2 | GitHub latest-release postconditions |
| `ss-75lu` | P1 | Correct TypeScript result-wrapper documentation |
| `ss-jfat` | P1 | Final portable YAML differential parity |
| `ss-ycm4` | P1 | Unicode-scalar canonical set ordering |
| `ss-6okz` | P1 | Extracted-kit declared-byte budgets |
| `ss-2t5m` | P1 | Release subject and aggregate byte budgets |
| `ss-1157` | P2 | Finite bounded release retry delays |
| `ss-fj2k` | P1 | Final red-team review reconciliation |

## Remaining Live Gates and Settled Decisions

No product-design question blocks the code candidate.
The portable regular-expression, format, identity, YAML, serialization, diagnostics, and
release-state decisions are settled in the normative spec and executable vectors.

Four external-state gates keep this plan In Progress as of 2026-07-09:

- the repository immutable-release setting is disabled, so `publish.yml` will fail
  before its first GitHub release mutation;
- the GitHub Pages API returns 404 for this repository, so no controlled live schema
  namespace has been observed;
- the workflow names a `github-release` environment that is absent from the live
  repository inventory, so its documented reviewer approval is not yet a verified
  protection gate; and
- protected-environment/trusted-publisher authorization plus a real dual-registry
  release have not been executed.

The same read-only audit confirmed active `main` and `v*` rulesets with no `main`
bypass, required CI contexts, required full-SHA Actions pinning, and `pypi`/`npm`
environments restricted to `v*` tags with reviewer gates; it found no corresponding
`github-release` environment.
These controls are necessary but do not substitute for registry-side trusted-publisher
verification or a protected-tag run.

Enabling repository settings, merging, publishing Pages, creating a release tag, and
uploading registry artifacts are administrator or release-authority actions.
They remain in `ss-6i6d`, `ss-8dt9`, `ss-0rqn`, `ss-trn7`, and `ss-1mdr`; no code-side
success is recorded as evidence for those live gates.

The following choices are settled by this draft but should be called out explicitly in
review because they affect v0.3 behavior:

- The JSON Schema `format` keyword is annotation-only by default; portable format
  assertions are deferred until a versioned assertion vocabulary has shared vectors.
- The portable YAML domain rejects aliases/merge keys initially rather than accepting
  parser-dependent expansion.
- New compilation does not derive `$id` from a logical contract ID; callers provide an
  explicit absolute schema URI when needed.
- Authored artifacts carry no metadata-format discriminator; the contract ID is their
  only authored version string.
- Direct `.ts` model loading is Bun-only; the published Node path requires built
  `.js`/`.mjs`.
- Agent Skills frontmatter omits `allowed-tools`; the portable bootstrap requires more
  than one universally valid minimal grant.
- The current single-file result serializer remains exact.
  Location-bearing outputs use the separately versioned diagnostic-v1 schema.
- The proposed immutable schema namespace must be verified as controlled and
  dereferenceable before it is published; changing the host before publication does not
  change the contract.
- Full LSP/editor integration and a hosted registry remain follow-up products built on
  positioned diagnostics and the standalone conformance kit.

## References

- [softschema Spec](../../../softschema-spec.md)
- [softschema Guide](../../../softschema-guide.md)
- [Parity development process](../../../development.md#keeping-python-and-typescript-in-parity)
- [July remediation epic](../../../../.tbd/)
- [June engineering review](../../reviews/review-2026-06-10-softschema-full-eng-review.md)
- [Adjacent schema and document systems research](../../research/research-2026-07-09-adjacent-schema-document-systems.md)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [JSON Schema Core and vocabularies](https://json-schema.org/draft/2020-12/json-schema-core)
- [Agent Skills specification](https://agentskills.io/specification)
- [Common documentation guidelines](https://github.com/jlevy/practical-prose/blob/main/docs/common-doc-guidelines.md)
- [CLI and agent-skill patterns](https://github.com/jlevy/tbd/blob/main/packages/tbd/docs/guidelines/cli-agent-skill-patterns.md)
- [tbd engineering guidelines](https://github.com/jlevy/tbd/tree/main/packages/tbd/docs/guidelines)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [npm lifecycle scripts](https://docs.npmjs.com/cli/v11/using-npm/scripts/)
- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/)
- [Supply-chain hardening](https://github.com/jlevy/supply-chain-hardening)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
