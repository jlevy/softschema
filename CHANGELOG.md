# Changelog

This changelog records user-visible package, artifact-format, skill, and documentation
changes. Versions before 0.3 predate this file; their Git tags remain the complete
history.

## 0.3.0 (Unreleased)

### Features

- **Portable artifact boundary:** Adds bounded JSON-compatible YAML semantics, explicit
  `frontmatter-md` and `pure-yaml` profiles, format 1 metadata and extensions, portable
  regex behavior, and annotation-only JSON Schema formats.
- **Offline schema validation:** Resolves fragments and explicitly supplied in-memory
  resources without implicit HTTP, file, or relative-path retrieval.
- **Batch diagnostics:** Adds deterministic multi-path and recursive validation,
  diagnostic-v1 JSON and JSONL, source positions, SARIF 2.1.0, and partial-result exit
  precedence while preserving single-file legacy JSON.
- **Portable APIs:** Separates runtime-neutral core APIs from Python and Node/Bun
  adapters; adds TypeScript contract descriptors, bound Zod runtime contracts, and named
  wire/result types.
- **Conformance kit:** Adds a language-neutral draft kit with schemas, vectors, offline
  bundles, digests, and independent consumer examples.
  Stable HTTPS identifiers remain unavailable until exact published bytes pass namespace
  verification.

### Fixes

- **Trust boundaries:** Prevents implicit schema retrieval, consumer-directory resource
  shadowing, unsafe artifact representations, and broad or clobbering skill writes.
- **Cross-runtime parity:** Makes canonicalization, strictness overlays, identity,
  numeric handling, Unicode ordering, JSON serialization, and error mapping explicit and
  shared across Python, Node, and Bun.
- **YAML edge parity:** Rejects ambiguous compact flow mappings, normalizes coded parser
  exceptions as syntax failures, and aligns implicit-null source anchors at CRLF, flow
  delimiters, comments, and EOF.
- **Failure results:** Returns stable parse, input, and schema-invalid records instead
  of engine tracebacks or inconsistent usage exits.
- **Bounded inputs:** Reads artifact and schema files incrementally up to the configured
  byte limit, bounds recursive discovery by depth and entry count, and rejects directory
  revisits without returning partial operand results.
- **Release recovery and identity:** Requires exact npm X.509 source identities,
  manifest-bounded artifacts, durable frozen-candidate recovery, monotonic Pages
  promotion, and explicit GitHub latest-release postconditions.
- **Resolvable bootstrap:** Separates candidate artifact versions from the last
  dual-registry-verified source/agent pins; PyPI and npm package READMEs describe their
  candidate artifact while root quickstarts remain usable after a failed or partial
  release.

### Skills and Agent Content

- **Portable routing skill:** Uses standard `name` and trigger-rich `description`
  frontmatter, capability-aware pinned fallback runners, progressive disclosure, and a
  self-contained brief.
- **Safe installation:** Adds explicit project/personal scope, nine documented native
  agent targets, dry-run, ownership checks, deterministic locking, atomic replacement,
  rollback, and interrupted-install repair.
- **Instruction discovery:** Keeps `AGENTS.md` authoritative, adds deterministic Claude,
  Gemini, and Copilot review adapters, and documents Aider’s explicit-read recipe.

### Documentation

- **Public information architecture:** Keeps the README short, moves adoption guidance
  to the guide, exact behavior to the spec, API use to the API reference, runtime
  internals to design references, and upgrade history to the migration guide.
- **Paired example:** Adds equivalent Pydantic and Zod models plus host integrations for
  the same artifact and compiled schema.
- **Claims checks:** Validates version, runtime, profile, result, policy, exit, and
  agent destination snippets against release metadata and the conformance manifest.

See [Migrating to 0.3](docs/migration-0.3.md) for compatibility details.

## 0.2.2 (2026-06-15)

0.2.2 is the last published 0.2 release.
It introduced the synchronized Python and TypeScript package surface available at that
tag. It does not contain the 0.3 trust, portable-YAML, conformance, batch-diagnostic, or
installer guarantees.

Before processing an untrusted artifact or schema with 0.2.2, read the
[published boundary limitations](SECURITY.md#published-022-boundary-limitations).
There is no 0.2.3 release; the fixes are consolidated into 0.3.0 to avoid backporting
mixed semantic changes after the fact.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
