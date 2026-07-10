# Changelog

All notable changes to softschema are documented here.
Both the Python (PyPI) and TypeScript (npm) packages release together under the same
version number.

## Unreleased

### Release Safety

- Release metadata now distinguishes logical, Python, and npm coordinates and embeds the
  same non-self-referential build identity in both packages.
- The publish workflow builds each artifact once in an unprivileged job, creates an
  external digest manifest and SPDX SBOM, installs the exact candidate bytes, and only
  then passes them to environment-scoped OIDC publisher jobs.
  Manual dispatches are dry runs and publisher jobs never check out or execute source.
- Python build dependencies are version- and hash-locked.
  Runtime dependencies use bounded compatible ranges, while development resolution is
  frozen by `uv.lock` and `bun.lock`. A dedicated, lock-backed `pip-audit` group fails
  on every known Python advisory, and pinned Bun fails on moderate-or-higher npm
  advisories.
- npm artifact smoke resolves one cold consumer under npm 11.16.0 and an exact 14-day
  `--before` cutoff. The transfer records the cutoff, resolver version, flags,
  package-lock digests, and exact local tarball integrity; downstream jobs use
  `npm ci --ignore-scripts` rather than resolving again.
- GitHub Actions use full commit SHAs.
  CI builds the wheel, sdist, and npm tarball once, recursively checksums the candidate,
  and runs those same bytes across Linux, macOS, and Windows instead of rebuilding per
  matrix job.

### 0.2.2 Safety Boundary

No 0.2.3 security patch was published.
Phase-2 compatibility work had already landed in the development history by the time the
broader boundary review was complete, so reconstructing a patch from mixed commits would
have created a second, weakly tested release line.
The fixes therefore ship together in 0.3.0, and documentation or metadata must not imply
that an interim patch existed.

Treat 0.2.2 as a trusted-input tool.
It does not provide all of the boundaries now required for untrusted artifacts, schemas,
repositories, or installation destinations:

- Python JSON Schema validation could retrieve an unresolved remote reference instead of
  using a deny-by-default, already-loaded resource registry.
- YAML representations and schema bundles did not share the final cross-runtime value
  domain or size, depth, node, and resource-count budgets.
  Duplicate or non-string keys, aliases, merge keys, non-finite numbers, unsafe
  integers, timestamp-looking scalars, negative zero, and related Python/JavaScript
  differences were not one portable boundary.
- Malformed schema syntax, dialects, keywords, references, regular expressions, and
  engine compilation failures did not all return the same stable `schema_invalid`
  result.
- Canonicalization and enforced-extra overlays were not limited to recognized schema
  positions and could change the meaning of annotations, nullable or composed schemas,
  boolean subschemas, or `unevaluatedProperties`.
- Installed commands could select colliding documentation or skill files from a consumer
  checkout instead of proving that bytes came from the installed package.
- Skill installation lacked the final scope, containment, ownership, locking,
  non-clobbering, rollback, and crash-repair guarantees.
- Release smoke rebuilt independently in parts of the matrix and resolved an ambient npm
  consumer, so it did not prove one closed candidate and dependency graph across every
  platform.

If 0.2.2 cannot yet be upgraded, use only trusted, size-bounded local input and schemas;
reject non-fragment external references before validation; do not load model code from
an untrusted checkout; run the process without network access and with filesystem
containment; install skills only into a reviewed empty or tool-owned destination; and
pin the package in the consumer lockfile.
These mitigations reduce exposure but do not backport the 0.3 guarantees.

### Migration

- Existing command names, public entrypoints, absent legacy metadata, and representable
  single-file JSON results remain supported through 0.3. New profiles, result formats,
  and conformance contracts are additive.
- Artifact metadata format and storage profile are independent.
  Existing Markdown/frontmatter remains the default; select whole-document YAML only
  with `--profile pure-yaml`. File extensions and metadata extensions never infer a
  profile.
- A logical contract ID no longer doubles as a JSON Schema `$id`. Recompile committed
  schemas once, pass an explicit canonical HTTPS or URN schema ID when resource identity
  is needed, and expect the compiled schema and digest to rebaseline.
- The portable schema profile is offline and deny-by-default.
  Fragment references continue to work; supply other trusted resources as already-loaded
  library values rather than paths or URLs.
  The narrow `legacy-0.2` profile exists only for compatible official legacy output.
- Draft 2020-12 `format` is annotation-only in both runtimes, and `pattern` follows the
  documented portable regular-expression subset.
  Use an explicit portable schema assertion or trusted Pydantic/Zod model when a format
  must reject a value.
- Both artifact profiles now enforce resource budgets before ordinary object
  materialization and reject duplicate or non-string keys, aliases, merge keys,
  non-finite values, and unsafe integers.
  YAML 1.2 date- and timestamp-looking scalars remain strings, and every negative-zero
  spelling normalizes to ordinary `0`; callers must not depend on implicit date objects
  or preservation of a negative-zero sign.
- Skill installation is an intentional safety break.
  Inside a non-home Git repository, omitted scope preserves the implicit project target;
  global, custom, or ambiguous destinations require explicit selection.
  Escaping, unmanaged, or modified targets fail instead of being overwritten.
- Python runtime requirements now declare both minimum and compatible upper bounds.
  npm retains semver-compatible caret ranges.
  Applications that deliberately need a newer incompatible major must upgrade softschema
  or override only after their own compatibility review.

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
