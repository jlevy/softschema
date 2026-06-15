# Changelog

All notable changes to softschema are documented here.
Both the Python (PyPI) and TypeScript (npm) packages release together under the same
version number.

## Unreleased (v0.2.2)

### Features

- **`softschema prime` command**: New command for project priming
- **Whole-number-float render parity**: Consistent rendering of whole-number floats
  across Python and TypeScript

### Fixes

- **CLIError and exit-code hierarchy**: Structured error hierarchy with correct exit
  codes
- **Narrowed CLI error handling**: More precise error handling in the CLI

### Refactoring

- **Cleanups**: Minor code and structural cleanups

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
