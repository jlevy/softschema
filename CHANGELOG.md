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
  GitHub Actions use full commit SHAs, and CI installs and runs the wheel and npm
  tarball across Linux, macOS, and Windows.

### Migration

- The 0.2.x package format and CLI output remain supported.
  Development metadata marks the draft conformance kit unavailable until its executable
  corpus is complete; this avoids advertising an incomplete portability contract.
  Consumers should keep using the documented `legacy-0.2` format until a later release
  explicitly promotes the portable profile.
- The forthcoming 0.3 portable profile treats Draft 2020-12 `format` values as
  annotations in both runtimes.
  TypeScript no longer rejects values through `ajv-formats`; use a portable JSON Schema
  assertion or the trusted Pydantic/Zod model when a formatted value must be enforced.

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
