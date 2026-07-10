# softschema TypeScript Design

The soft schema practice is language-neutral (see
[softschema Guide](softschema-guide.md) and [softschema Spec](softschema-spec.md)). This
document covers the TypeScript package, `softschema`, which implements the same
Markdown/YAML validation slice as the [Python package](softschema-python-design.md)
using Zod instead of Pydantic.

The two implementations are held to **exact behavioral parity**: equivalent CLI
inputs/outputs/flags and equivalent library APIs, the same canonical compiled JSON
Schema (content-identical, equal `schema_sha256` over its canonical JSON; the YAML
serialization bytes may differ, and `--check` drift compares parsed canonical content),
and the same engine-neutral validation results.
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
| `yaml-value-domain` | Bounded portable-YAML parsing, materialized-value normalization, and `ValidationLimits` |
| `portable-pattern` | `portable-regex-v1` parsing, matching, and schema-position traversal |
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

## Schema View

`SchemaView.load()` parses YAML or JSON through the bounded portable-value boundary and
accepts a trusted validation-limit override with the same defaults as validation.
The constructor accepts an already normalized JSON-compatible mapping and takes a deep
snapshot without running the boundary again.
The `raw` getter returns a new deep copy; mutating constructor input, `raw`, root
metadata, or field metadata never changes later navigation.

Local `$ref` resolution preserves annotation siblings such as `description`,
`x-softschema`, `format`, `contentEncoding`, and `contentMediaType`. A direct reference
with an assertion sibling remains unresolved because a shallow merge would misrepresent
the assertions’ conjunctive semantics.
The reader unwraps only a two-branch `anyOf` or `oneOf` whose outer siblings are
annotations and whose branches are one annotation-only local reference and one exact
null schema, and only when the referenced target provably excludes null.
Exact nullable type and string-enum shapes remain convenient scalar metadata.
For every genuine union, `jsonType` and `enum` remain `null`, and the reader does not
select or traverse an arbitrary first branch.

`field()` throws `Error` when its pointer is absent.
`load()` preserves filesystem and UTF-8 exceptions, throws the portable YAML exception
types for syntax or value-domain failures, and throws `Error` for a non-mapping root.

Artifact envelope inference follows the same boundary ownership: the portable parser or
materialized-value normalizer rejects non-string keys first, and `inferEnvelopeKey()`
consumes the resulting string keys without coercion or another normalization pass.

## Library API Parity

Names are idiomatic per language; shapes, semantics, error `kind`s, and warning codes
are identical.

| Python | TypeScript | Notes |
| --- | --- | --- |
| `validate_artifact` | `validateArtifact` | same result JSON, `kind`s, warnings, `metadataMode` |
| `validate_values` | `validateValues` | combined structural and semantic on a values mapping |
| `validate_structural` | `validateStructural` | jsonschema ↔ ajv; identical error records |
| `validate_semantic` | `validateSemantic` | Pydantic ↔ Zod; errors impl-specific |
| `compile_model` | `compileSchema` | content-identical canonical compiled schema, equal `schema_sha256` |
| `Contracts` | `Contracts` | `register`/`resolve`/`all`; dup-id error |
| `SchemaView` / `FieldInfo` | `SchemaView` / `FieldInfo` | same navigation and filters |
| `SoftField` | `softField` | same emitted `x-softschema` block and omit-empty rules |
| `parse_schema_metadata` | `parseSchemaMetadata` | same accepted shapes and errors |
| `SchemaMetadata` | `SchemaMetadata` | legacy serialization stays `{contract, envelope, schema, status}`; format 1 adds the quoted `format` and optional namespaced `extensions` mapping |
| `_resolve_metadata_schema` | `resolveMetadataSchema` | bounded relative-path resolution from document directory + cwd |
| `regenerate` | `regenerate` | byte-identical marker bodies |
| `GeneratedSection` | `GeneratedSection` | parsed marker with `kind`, `schema`, `pointer` |
| `SOFTSCHEMA_FORMAT_VERSION` | `SOFTSCHEMA_FORMAT_VERSION` | exported from `index.ts` / `__init__.py` |
| `ARTIFACT_FORMAT_VERSION` | `ARTIFACT_FORMAT_VERSION` | current metadata grammar (`"1"`), independent of package and compiled-schema versions |
| `WarningCode` (`document-*`) | `WarningCode` union | same codes |
| `ValidationLimits` | `ValidationLimits` | same default budgets; Python uses snake case and TypeScript uses camel case |

## Result Shape and CLI Output

`validateArtifact` returns a result whose serialized form is byte-identical to Python’s
(`contract`, `contract_id`, `document_metadata`, `path`, `profile`, `semantic`,
`status`, `structural`, `values`, `warnings`). Structural errors are engine-neutral
records (`{ kind, path, validator, validator_value, value, message }`) with
softschema-synthesized messages, sorted by `(path, validator)`. CLI JSON uses a
`stableStringify` that matches Python’s
`json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False)`; exit codes are `0` ok /
`1` validation failure or drift / `2` usage error.

`normalizeAjvError()` reads `error.schema`/`error.data` (ajv runs with `verbose: true`),
the analogues of jsonschema’s `validator_value`/`instance`, so records match Python for
every keyword; ajv’s per-key `additionalProperties` errors are collapsed to one.

One known divergence remains (`ss-wbnm`): JS collapses a whole-number float (`2.0`, the
schema bound `10.0`) to `2`/`10` at parse, while Python preserves the float from the
YAML source token (`repr(2.0) == "2.0"`), so such a value renders without its `.0` in a
TypeScript `value`/`validator_value`/message.
A schema-type-aware fix cannot match Python (Python’s rendering follows the parsed
value’s runtime type, not the declared type), so an exact fix requires preserving source
tokens through parse → serialize → ajv; that is disproportionate for an edge case where
all other golden CLI output and error rendering is byte-identical.
(Compiled schema YAML files are content-identical rather than byte-identical; see
above.) The golden corpus keeps error-case values integer or non-whole-float so it stays
byte-identical on both engines (see `tests/golden/README.md`). Full analysis in the
parity plan (epic `ss-jgkf`).

## Toolchain

bun (runtime and package manager), `bunup` (build), `bun test` (unit), `biome` (lint and
format), `tsc --noEmit` (types).
Dependencies: `zod`, `yaml`, `commander`, `ajv` (`ajv/dist/2020`), and `atomically` (the
CLI emits only JSON, so no color dependency).
Ajv runs with `validateFormats: false`; Draft 2020-12 formats are annotations, and the
package deliberately has no `ajv-formats` dependency that could turn them into
runtime-specific assertions.
The shared `tests/golden/` corpus runs against this CLI via `SOFTSCHEMA_IMPL=ts`.

Artifact parsing uses the same discriminated records as Python.
Readable frontmatter, syntax, root, and value-domain failures are `parse_error` records
and exit 1; missing, unreadable, and unexpanded-directory paths are `input_error`
records and exit 2. The CLI accepts an explicit `--profile frontmatter-md|pure-yaml`,
defaults to `frontmatter-md`, and never infers the profile from an extension.

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
