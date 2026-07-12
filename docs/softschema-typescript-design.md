# softschema TypeScript Design

The soft schema practice is language-neutral (see
[softschema Guide](softschema-guide.md) and [softschema Spec](softschema-spec.md)). This
document covers the TypeScript package, `softschema`, which implements the same
Markdown/YAML validation slice as the [Python package](softschema-python-design.md)
using Zod instead of Pydantic.

The two implementations share the same commands, exit classes, structured result
meaning, and canonical compiled JSON Schema (content-identical with equal
`schema_sha256`; YAML presentation bytes may differ).
Only idiomatic surface details differ (snake_case ↔ camelCase, Pydantic ↔ Zod).
Parity is enforced by the shared golden corpus and a cross-implementation conformance
test; see the parity development process in [development.md](development.md).

## Modules

| Module | Purpose |
| --- | --- |
| `models` | `Contract`, status/profile unions, `SchemaMetadata`, `WarningCode`, `parseSchemaMetadata` |
| `registry` | `Contracts`: resolve contracts by id |
| `canonicalize` | The shared canonical JSON Schema profile (same rules as Python) |
| `compile` | `compileSchema`: Zod → canonical JSON Schema YAML file and `schema_sha256` |
| `errors` | Engine-neutral structural error records and ajv normalization |
| `validate` | `validateArtifact`, `validateValues`, `validateStructural`, `validateSemantic` |
| `schemaView` | `SchemaView`/`FieldInfo`: read-only navigation over a compiled schema |
| `softField` | `softField()`: per-field `x-softschema` annotations via Zod `.meta()` |
| `generate` | `parseSections`/`regenerate`: deterministic generated Markdown sections |
| `cli` | `commander` program: `validate`, `compile`, `inspect`, `docs`, `generate`, `skill` |

## Idiomatic Zod Choices

- Source schemas are Zod; `z.strictObject()` ↔ Pydantic `extra="forbid"`.
- Validation uses `safeParse` (never throws on validation failure).
- Per-field annotations use `softField(schema, {...})`, attaching an `x-softschema`
  block via Zod `.meta()`, the same emitted block as Python’s `SoftField`.
- The compiled schema is produced with
  `z.toJSONSchema({ target: "draft-2020-12", io: "input", reused: "inline" })`; nested
  objects carry `.meta({ id })` so `$defs` keys match the Pydantic class names.
  The shared `canonicalizeJsonSchema` then normalizes the rest.
- Resources (docs/skill) are bundled into the package (`resources/`, copied at build)
  and served from there (never read from the working directory), mirroring the Python
  wheel.

## Library API Parity

Names are idiomatic per language; shapes, semantics, error `kind`s, and warning codes
are identical.

| Python | TypeScript | Notes |
| --- | --- | --- |
| `validate_artifact` | `validateArtifact` | same result fields, `outcome`, error kinds, and warnings |
| `validate_values` | `validateValues` | combined structural and semantic on a values mapping |
| `validate_structural` | `validateStructural` | jsonschema ↔ ajv; identical error records |
| `validate_semantic` | `validateSemantic` | Pydantic ↔ Zod; errors impl-specific |
| `compile_model` | `compileSchema` | content-identical canonical compiled schema, equal `schema_sha256` |
| `Contracts` | `Contracts` | `register`/`resolve`/`all`; dup-id error |
| `SchemaView` / `FieldInfo` | `SchemaView` / `FieldInfo` | same navigation and filters |
| `SoftField` | `softField` | same emitted `x-softschema` block and omit-empty rules |
| `parse_schema_metadata` | `parseSchemaMetadata` | same accepted shapes and errors |
| `SchemaMetadata` | `SchemaMetadata` | quartet: `contract_id`/`schema_ref`/`envelope`/`status` (Python); `contractId`/`schema`/`envelope`/`status` (TS); serialized as `{contract, envelope, schema, status}` |
| `_resolve_metadata_schema` | `resolveMetadataSchema` | bounded relative-path resolution from document directory + cwd |
| `regenerate` | `regenerate` | byte-identical marker bodies |
| `GeneratedSection` | `GeneratedSection` | parsed marker with `kind`, `schema`, `pointer` |
| `WarningCode` (`document-*`) | `WarningCode` union | same codes |

## Result Shape and CLI Output

`validateArtifact` returns the portable fields `contract`, `contract_id`,
`document_metadata`, `outcome`, `path`, `profile`, `semantic`, `status`, `structural`,
`values`, and `warnings`. Structural errors use engine-neutral records
`{ kind, path, validator, validator_value, value, message }`, sorted by
`(path, validator)`. Library results use `valid` / `invalid` / `input_error`. The CLI
reads once to infer document binding: readable results map to exits `0` or `1`, while
access and parse failures use its one-line stderr and exit-`2` input boundary.
Cross-runtime tests compare JSON structurally; deterministic pretty printing is local
presentation, not a byte-level wire contract.

`normalizeAjvError()` reads `error.schema`/`error.data` (ajv runs with `verbose: true`),
the analogues of jsonschema’s `validator_value`/`instance`, so records match Python for
every keyword; ajv’s per-key `additionalProperties` errors are collapsed to one.

Values are restricted to the shared portable domain.
JSON object key order and runtime-native number spelling are not semantic; canonical
byte encoding is reserved for the compiled-schema digest.

## Toolchain

bun (runtime and package manager), `bunup` (build), `bun test` (unit), `biome` (lint and
format), `tsc --noEmit` (types).
Dependencies: `zod`, `yaml`, `commander`, `ajv` (`ajv/dist/2020`), and `atomically`. The
shared `tests/golden/` corpus runs against this CLI via `SOFTSCHEMA_IMPL=ts`.

## Packaging

`bunup` builds two entrypoints from `src/index.ts` (the library barrel) and `src/cli.ts`
(the executable). Two packaging decisions keep the library importable; both are guarded
by `test/library-entrypoint.test.ts`:

- **No `"sideEffects": false`.** On a pure re-export barrel, that hint makes Bun’s
  bundler tree-shake the re-exported implementations out of `dist/index.js` while
  leaving the `export { ... }` names, so `import { validateArtifact } from "softschema"`
  throws `SyntaxError: Export 'X' is not defined`. Without the hint, `index.js` and
  `cli.js` share one chunk and every public symbol resolves.
  Do not re-add the flag.
- **ESM-safe entrypoint check.** `cli.ts` runs the CLI only when it is the process
  entrypoint, detected by comparing `pathToFileURL(realpathSync(process.argv[1])).href`
  with `import.meta.url`. `import.meta.main` is a Bun-only global that the bundler
  lowers to an always-true CommonJS check, which would run the CLI on a plain `import`.
  `realpathSync` resolves the symlink that npm/npx install for the bin.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
