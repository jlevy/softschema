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
| `validate_artifact` | `validateArtifact` | same result JSON, `kind`s, warnings, `metadataMode` |
| `validate_values` | `validateValues` | combined structural and semantic on a values mapping |
| `validate_structural` | `validateStructural` | jsonschema ↔ ajv; identical error records |
| `validate_semantic` | `validateSemantic` | Pydantic ↔ Zod; errors impl-specific |
| `compile_model` | `compileSchema` | content-identical canonical compiled schema, equal `schema_sha256` |
| `Contracts` | `Contracts` | `register`/`resolve`/`all`; dup-id error |
| `SchemaView` / `FieldInfo` | `SchemaView` / `FieldInfo` | same navigation and filters |
| `SoftField` | `softField` | same emitted `x-softschema` block and omit-empty rules |
| `parse_schema_metadata` | `parseSchemaMetadata` | same accepted shapes and errors |
| `regenerate` | `regenerate` | byte-identical marker bodies |
| `WarningCode` (`document-*`) | `WarningCode` union | same codes |

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
Dependencies: `zod`, `yaml`, `commander`, `ajv` (`ajv/dist/2020`) and `ajv-formats`,
`atomically` (the CLI emits only JSON, so no color dependency).
The shared `tests/golden/` corpus runs against this CLI via `SOFTSCHEMA_IMPL=ts`.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
