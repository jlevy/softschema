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
| `portable` | Bounded UTF-8 reading and portable YAML value decoding |
| `registry` | `Contracts`: resolve contracts by id |
| `canonicalize` | The shared canonical JSON Schema profile (same rules as Python) |
| `enforcement` | Checked enforced-profile analysis and offline schema-resource graph preparation |
| `compile` | `compileSchema`: Zod → canonical JSON Schema YAML file and `schema_sha256` |
| `errors` | Engine-neutral structural error records and ajv normalization |
| `validate` | `validateArtifact`, `validateValues`, `validateStructural`, `validateSemantic`, `clearValidatorCache`, and the `readFrontmatterDoc`/`readYamlDoc` decoders that produce a `document` root |
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

## Portable YAML Parsing

`parsePortableYaml` preflights the `yaml` syntax tree for limits and unsupported YAML
features, converts it to JavaScript values, and checks the result against the shared
portable domain. The configured parser already decodes implicit date- and
timestamp-shaped scalars as strings, so softschema does not apply a separate lexical
rejection or timestamp constructor.

Host-native JavaScript objects are outside the portable domain and are rejected when
programmatic field metadata is checked.
Arrays, plain objects, and null-prototype objects remain portable; values such as
`Date`, `Map`, `Set`, `RegExp`, `Error`, `URL`, and class instances do not silently
collapse to empty JSON objects.
For semantic validation of portable temporal strings, use `z.iso.date()`,
`z.iso.datetime()`, `z.iso.time()`, or `z.iso.duration()`. `z.date()` and
`z.coerce.date()` produce JavaScript `Date` values and cannot represent the package’s
portable artifact boundary or compile to its JSON Schema output.

These Zod schemas define their own accepted string spellings and are not semantic
equivalents of Pydantic’s temporal types.
Cross-runtime projects that need identical semantic acceptance must align and test model
validators in both implementations.

Zod emits intrinsic regex patterns when its ISO temporal schemas are converted to JSON
Schema, while Pydantic emits only a format annotation.
The compiler’s `toJSONSchema` override identifies `z.ZodISODate`, `z.ZodISODateTime`,
`z.ZodISOTime`, and `z.ZodISODuration` nodes through their public classic-schema
`def.pattern` and removes the intrinsic pattern before canonicalization.
An authored `z.string().regex(...)` pattern remains intact, including when its metadata
also declares a date format.

Zod ISO datetime options such as offset, local-time, and precision affect semantic
validation but are not represented in the canonical sidecar or `schema_sha256`. The
digest proves structural parity; it does not prove identical semantic accept sets.

Ajv runs with `validateFormats: false`, matching JSON Schema Draft 2020-12’s default
Format-Annotation vocabulary and the Python runtime.
Calendar-aware rejection belongs in the Zod semantic model; an explicit portable
`pattern` remains a structural assertion.
`validateValues` accepts already-extracted host data and does not parse or normalize it
as YAML.

## Checked Enforced Profile

When `status` is `enforced` and a structural schema is bound, Ajv applies the checked
undeclared-property policy described below.
Without a structural schema, `validateArtifact` preserves the semantic-only Zod path and
reports structural validation as skipped with `inferred_via_model`; `validateValues`
also runs the supplied Zod schema and leaves its unrequested structural result
successful. If neither schema nor model is bound, artifact validation is metadata-only
and reports `no_schema`. `status` does not synthesize JSON Schema or change whether a
Zod object strips, passes through, or rejects unknown keys.

Before Ajv compilation, `prepareSchemaGraph` checks the root and every supplied resource
as one offline graph.
It validates the Draft 2020-12 schemas and portable regular expressions, indexes URI
identities, resolves the supported static `$ref` forms, and rejects undeclared
properties at each object location where annotation flow makes the overlay safe.
A property is undeclared when no successful applicable schema evaluates its value at
that location. Reusable definitions and resources stay open; structured reference
application sites receive the rule independently.
Structured `items` and disjoint `prefixItems`/`items` also receive it independently,
while `contains` remains a matcher.
Sibling child evaluators and context-sensitive composition references are refused when
independently inserting that rejection rule could change authored semantics.
Caller-constructed graphs that reuse one object at several schema locations return
`schema_invalid/shared_subschema`. Unsupported topologies return a structured
`enforcement_unsupported` record rather than a document verdict produced by a partial
rewrite. The normative rules, reference boundary, and reason codes are in the spec’s
[support matrix](softschema-spec.md#support-matrix).

The overlay is validation-time only and does not affect the compiled schema or
`schema_sha256`. `validateStructural` accepts supplied `resources`, and `validateValues`
accepts both `status` and `resources`. Calls with resources bypass the
compiled-validator cache because the graph is neither cheap nor safe to identify by the
root schema alone. Before returning a cache hit for an enforced call, graph preparation
and the `shared_subschema` check run again: shared in-memory identity is not represented
by the content-addressed cache key.

## Library API Parity

Names are idiomatic per language; result meaning, verdicts for the checked profile,
error `kind`s, and warning codes are identical.
Native engines may emit different structural record sets only for deviations pinned
explicitly in the shared vectors.

| Python | TypeScript | Notes |
| --- | --- | --- |
| `validate_artifact` | `validateArtifact` | same result fields, `outcome`, error kinds, and warnings |
| `validate_values` | `validateValues` | combined structural and semantic on a values mapping; both accept `status` and offline `resources` |
| `validate_structural` | `validateStructural` | jsonschema ↔ Ajv; shared record shape and meaning, with pinned native-engine deviations |
| `clear_validator_cache` | `clearValidatorCache` | drop memoized compiled validators; both cache on schema content, keyed with the enforced overlay, and skip the cache when `resources` are supplied |
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
`{ kind, code, path, property?, validator, validator_value, value, message }`, sorted by
`(path, validator, property)`. `property` is present for missing and undeclared-field
records, with one record per affected field.
Library results use `valid` / `invalid` / `input_error`. The CLI reads once to infer
document binding: readable results map to exits `0` or `1`, while access and parse
failures use its one-line stderr and exit-`2` input boundary.
Cross-runtime tests compare JSON structurally; deterministic pretty printing is local
presentation, not a byte-level wire contract.

`normalizeAjvError()` reads `error.schema`/`error.data` (ajv runs with `verbose: true`),
the analogues of jsonschema’s `validator_value`/`instance`, and extracts Ajv’s affected
property detail into the shared `property` field.
It decodes each JSON Pointer against the validated instance so array positions in `path`
are numbers while numeric-looking object keys remain strings, matching Python.
Two ajv shapes are then normalized: `collapseUndeclaredProperties()` keeps one record
per object path and affected property for the `undeclared_property` code, and
`dropConditionalWrappers()` removes the `if` record Ajv adds alongside a failed
conditional’s real cause, which jsonschema never emits.
`code` is a pure function of `validator`, computed in the same shared layer as the
message table so the engines cannot drift.

The checked profile guarantees equal validation verdicts in Python and TypeScript.
It does not claim that arbitrary `jsonschema` and Ajv schemas produce the same native
error-record set. The few accepted record-set differences are exact, named entries in
`tests/vectors/hardening.yaml`’s `engine_deviations`; drift on either runtime still
fails. For field repair, the stable match surface is `{kind, code, path, property}`.
`validator`, `validator_value`, and `value` remain diagnostic details.

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
