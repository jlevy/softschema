# Changelog

All notable changes to softschema are documented here.
Both the Python (PyPI) and TypeScript (npm) packages release together under the same
version number.

## Unreleased

### Features

- **Portable YAML timestamp strings**: Bare dates and timestamps now decode to their
  string content in both implementations instead of being rejected.
  Existing quoted values remain unchanged, and no artifact rewrite is required when
  upgrading. Validation results retain strings; date validity remains the responsibility
  of a semantic model or explicit structural assertion.
- **Canonical date-schema parity**: Pydantic and Zod ISO date fields now compile to the
  same format-only schema and digest.
  JSON Schema `format` remains annotation-only; explicitly authored patterns remain
  structural assertions.

### Guidelines and Content

- **Agent timestamp guidance**: The bundled skill now tells agents that date-shaped YAML
  values are portable strings and that calendar validation belongs in the bound contract
  or model.

### Documentation

- **Date migration guidance**: The guide, spec, and language design references now
  distinguish portable string decoding from Pydantic, Zod, and JSON Schema date
  validation, including the annotation-only format policy.

## v0.3.0—2026-07-12

### Features

- **Paired portable-value boundary**: Python and TypeScript now share bounded UTF-8 and
  YAML input rules, safe-number limits, canonical schema digests, and structurally
  comparable validation results.
- **Contract and schema identity**: Compilers require a logical contract ID, keep an
  optional JSON Schema resource ID separate, and produce matching canonical compiled
  schemas and `schema_sha256` values.
- **Explicit skill installation**: `softschema skill --install` now requires a scope and
  agent target, supports dry-run previews, and protects unmanaged files.

### Fixes

- **Portable validation parity**: Aligned frontmatter delimiters, YAML structure limits,
  schema and pattern failures, strict-extra handling, error records, and compiler drift
  checks across both runtimes.
- **Bounded document resources**: Document-declared schemas and installed package
  resources now resolve within their intended trust boundaries.

### Guidelines and Content

- **Installed agent resources**: The source skill and generated portable Agent Skills
  and Claude mirrors now use one managed, drift-checked installation flow.

### Documentation

- **Hardening documentation**: Updated the guide, spec, language design references, and
  development workflow to describe the paired runtime and release boundary accurately.

**Full commit history**:
[v0.2.2 … v0.3.0](https://github.com/jlevy/softschema/compare/v0.2.2...v0.3.0)

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
