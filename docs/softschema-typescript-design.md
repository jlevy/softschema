# softschema TypeScript Design

The soft schema practice is language-neutral (see
[softschema Guide](softschema-guide.md) and [softschema Spec](softschema-spec.md)). This
document covers the TypeScript package, `softschema`, which implements the same
Markdown/YAML validation slice as the [Python package](softschema-python-design.md)
using Zod instead of Pydantic.

The two implementations share CLI behavior, canonical compiled JSON Schema
(content-identical, equal `schema_sha256` over canonical JSON), portable validation
semantics, and engine-neutral wire results.
The YAML serialization bytes may differ, and `--check` drift compares parsed canonical
content. Their library APIs remain idiomatic to each host: TypeScript exposes
descriptors, bindings, and Node/Bun adapters rather than translating every Pydantic
method. Shared behavior is enforced by the golden corpus and cross-implementation
conformance tests; see the parity development process in
[development.md](development.md).

## Modules

| Module | Purpose |
| --- | --- |
| `core` | Published runtime-neutral entrypoint for values, identities, metadata, schema-profile logic, and normalized results |
| `node` | Published Node.js/Bun adapter for YAML, filesystems, Zod, resources, and path-based operations |
| `models` | Portable `ContractDescriptor`, deprecated `Contract` alias, status/profile unions, metadata, and wire shapes |
| `runtime-contract` | `RuntimeContract`/`bindContract`: synchronized Node.js/Bun descriptor and Zod binding |
| `model-loader` | Trusted local model-module policy, path-to-file-URL resolution, and Zod export loading |
| `registry` | `Contracts`: resolve contracts by id |
| `canonicalize` | The shared canonical JSON Schema profile (same rules as Python) |
| `compile` | `compileSchema`: Zod → canonical JSON Schema YAML file and `schema_sha256` |
| `errors` | Engine-neutral structural error records and ajv normalization |
| `validate` | `validateArtifact`, `validateValues`, `validateStructural`, `validateSemantic` |
| `yaml-value-domain` | Bounded portable-YAML parsing, materialized-value normalization, and `ValidationLimits` |
| `portable-pattern` | Bounded `portable-regex-v1` parsing, Thompson-NFA compilation, normalized classes, lazy DFA state/transition/membership budgets, Ajv regex-engine integration, and schema-position traversal |
| `core/diagnostics` | Pure diagnostic-v1, JSONL, and SARIF projection |
| `core/source-map` | Runtime-neutral source positions and JSON-path anchors |
| `artifact-discovery` | Deterministic path/glob discovery and file identity |
| `schemaView` | `SchemaView`/`FieldInfo`: read-only navigation over a compiled schema |
| `softField` | `softField()`: per-field `x-softschema` annotations via Zod `.meta()` |
| `generate` | `parseSections`/`regenerate`: deterministic generated Markdown sections |
| `cli` | `commander` program: validation, compilation, inspection, docs, diagnostics, doctor, and skill commands |

## Architecture Boundaries

The package publishes separate contract and adapter surfaces:

```ts
import {
  canonicalizeJsonSchema,
  defineContractDescriptor,
  normalizePortableValue,
  parseSchemaMetadata,
} from "softschema/core";
import { bindContract, compileSchema, validateArtifact } from "softschema/node";
```

`softschema/core` accepts already materialized JSON-compatible values.
Its transitive module graph contains no `node:` builtin, YAML parser, Zod model,
filesystem, dynamic-import, packaged-resource, or CLI dependency.
`softschema/node` owns those Node.js and Bun adapters.
`softschema/cli` remains a separate executable adapter over the same runtime and core
behavior.

The package root, `softschema`, remains a compatibility facade for the v0.2 Node.js and
Bun library surface.
It exposes exactly the same names as `softschema/node`; no other adapter may leak
through it. New code should select `softschema/core` or `softschema/node` explicitly.
Keeping the facade for at least the v0.3 line avoids breaking established imports while
giving browser, worker, and third-implementation authors a runtime-neutral target.

Architecture tests walk the core source graph, reject forbidden runtime dependencies and
dynamic imports, import the built core under Node, compare the root and Node export
sets, and verify the package subpath declarations.
This makes the compatibility exception explicit without weakening the pure-core
boundary.

## Portable Descriptors and Runtime Bindings

`ContractDescriptor` is the portable contract shape.
It contains exactly six JSON-serializable fields: `id`, `model`, `envelopeKey`,
`status`, `profile`, and `schemaPath`. `defineContractDescriptor()` validates those
fields, removes unknown properties, and returns a frozen descriptor.
A model value is only a stable label or module specifier; executable Zod state never
enters `softschema/core`.

`RuntimeContract` belongs to `softschema/node`. Construct it with `bindContract()`:

```ts
import { defineContractDescriptor } from "softschema/core";
import { bindContract, validateArtifact } from "softschema/node";
import { MoviePage } from "./movie-page.model.js";

const descriptor = defineContractDescriptor({
  id: "example.movies:MoviePage/v1",
  model: "./movie-page.model.js:MoviePage",
  envelopeKey: "movie",
  status: "permissive",
  profile: "frontmatter-md",
  schemaPath: "movie-page.schema.yaml",
});

const contract = bindContract(descriptor, MoviePage);
const result = validateArtifact("movie.md", contract);
```

Binding rejects both inconsistent states: a descriptor that names a model without a Zod
schema and a descriptor with no model name but an unexpected Zod schema.
This removes the former requirement to synchronize `contract.model` and a separate
`semanticModel` option.

For v0.2 compatibility, `Contract` remains a deprecated alias of `ContractDescriptor`,
`defineContract()` remains an alias of `defineContractDescriptor()`, and the legacy
`validateArtifact(path, contract, { semanticModel })` overload preserves its existing
behavior and serialized bytes.
New integrations should bind once and use the `RuntimeContract` overload.
These names remain available through the v0.3 compatibility line; any later removal
requires a documented pre-1.0 migration.

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
File loads resolve one canonical regular-file target, bind the open descriptor to the
inspected device/inode/size/mtime/ctime, fail closed when no stable inode is available,
read through the limit plus one byte, and decode strict UTF-8. Document-declared schema
containment passes that canonical identity into the reader, which repeats canonical-path
checks around the descriptor open and rejects a different identity or mutation-sensitive
metadata rather than claiming descriptor-relative parent traversal on Node.
A second descriptor pass compares bytes on platforms where timestamp behavior may not
expose a same-size rewrite.
This detects ordinary replacement and in-place mutation; it is not an atomic snapshot
against a hostile writer able to coordinate both reads or restore every observable
timestamp. The constructor accepts an already normalized JSON-compatible mapping and
takes a deep snapshot without running the boundary again.
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
| `validate_artifact` | `validateArtifact` | TypeScript wraps the shared legacy wire as `{ok, output}`; `output` has the same result JSON, `kind`s, warnings, and `metadataMode` semantics |
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

`validateArtifact` returns `ArtifactValidationResult { ok, output }`. `ok` is the
aggregate success flag; `output` is the typed legacy single-artifact wire (`contract`,
`contract_id`, `document_metadata`, `path`, `profile`, `semantic`, `status`,
`structural`, `values`, `warnings`). Callers must retain and inspect `output` on failure
instead of assuming failed validation throws.
When discovery classifies one single explicit path as a regular file, JSON emits those
legacy `output` bytes, including when a later read fails.
A single explicit `not_found` result is the narrow legacy exception; every other
discovery-input result uses a diagnostic-v1 aggregate.
Structural errors are engine-neutral discriminated records with softschema-owned
messages and deterministic ordering; semantic Zod issue detail remains
implementation-specific.

Multi-path and directory requests project those same typed results into diagnostic-v1.
Aggregate JSON adds limits, summary, per-input outcomes, and positioned diagnostics.
JSONL emits one independently self-describing record per result and no summary record.
SARIF 2.1.0 is a deterministic projection with stable rules, percent-encoded artifact
URIs, and Unicode-code-point columns.
Input errors continue alongside readable files; exit precedence is 2 for any input
error, otherwise 1 for any readable failure, otherwise 0.

The explicit portable serializer does not delegate key ordering to `JSON.stringify`. It
orders keys by Unicode scalar value, handles integer-like keys without JavaScript’s
property reordering, emits the Python-compatible binary64 spelling, validates dense
plain data without invoking getters, rejects cycles and unsupported runtime values, and
owns compact hashes, pretty CLI JSON, and JSONL framing.
Mathematically integral values outside the safe-integer interval fail the shared value
boundary before serialization.

`ValidationResultLegacyWire`, diagnostic aggregate/record types, structural unions,
semantic issue types, contract/metadata wires, and SARIF projection inputs mirror the
versioned conformance schemas rather than exposing opaque `Record<string, unknown>`
results. `normalizeAjvError()` reads Ajv’s verbose schema and data values and collapses
per-key `additionalProperties` records so they match Python’s normalized result.

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

For batch work, the filesystem adapter applies the shared portable glob grammar,
display-path sorting, file-identity deduplication, explicit/discovered symlink rules,
static invocation caps, and shared candidate-code-point match fuel.
Static glob-budget failures precede filesystem access; dynamic exhaustion is
`discovery_limit`. The YAML adapter retains source spans until diagnostic projection.
Parser and discovery mechanics stay outside `softschema/core`; diagnostic construction
itself is pure core logic and shares vectors with Python.

## Trusted Model Modules

The CLI executes a model module as local code.
Only load models from a trusted source.
The supported source forms are deliberate:

| Runtime | Supported model paths | Guidance |
| --- | --- | --- |
| Node.js | Built `.js` or `.mjs` | Compile TypeScript first. ESM is the portable published-package path. |
| Bun | `.js`, `.mjs`, or direct `.ts` | Direct `.ts` is a Bun convenience, not a promise to honor tsconfig aliases or non-erasable TypeScript syntax. |

Other extensions, including `.cjs`, `.mts`, and `.tsx`, are rejected before import.
When Node receives `.ts`, the diagnostic tells the caller to compile to `.js`/`.mjs` or
run the supported Bun path.
The loader splits `path:export` at the final colon so a Windows drive letter is not
mistaken for the separator.
It resolves the local path and imports `pathToFileURL(resolve(...)).href`; spaces, `#`,
`%`, UNC paths, and Windows drive paths therefore use file-URL semantics instead of
string interpolation.

Commander help and version exits remain 0. Every nonzero Commander parse or usage
failure is normalized to exit 2, matching Python argparse.
Exceptions that indicate a programmer fault (`TypeError`, `RangeError`, or
`ReferenceError`) still propagate with a stack trace; user-originated model and path
errors remain clean exit-2 diagnostics.

## Packaging

`bunup` builds four entrypoints: `src/core/index.ts` (runtime-neutral contract core),
`src/node.ts` (Node.js/Bun adapters), `src/index.ts` (compatibility facade), and
`src/cli.ts` (executable).
The following packaging decisions keep every public entrypoint importable; they are
guarded by `test/library-entrypoint.test.ts` and `test/architecture-boundary.test.ts`:

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
- **Encoded local model imports.** Model paths are converted with `pathToFileURL` after
  platform-correct resolution.
  Do not replace this with `import(resolve(path))`: raw absolute paths are not portable
  module specifiers and mis-handle URL-significant characters and Windows drive letters.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
