# softschema

The TypeScript/Zod implementation of [softschema](https://github.com/jlevy/softschema):
validate and structure Markdown/YAML artifacts with frontmatter contracts.
It is the idiomatic Zod counterpart to the Python/Pydantic package and is held to exact
behavioral parity with it: the same CLI inputs/outputs/flags, the same library surface,
and the same canonical JSON Schema sidecar (content-identical, equal `schema_sha256`
over its canonical JSON; YAML serialization bytes may differ).

```bash
npx softschema@latest --help            # zero-install
# or
bun add softschema
```

## CLI

`softschema-ts` exposes the same commands and flags as the Python `softschema`:

```bash
softschema-ts validate <doc.md> --schema <sidecar.yaml> [--model mod.ts:Export] [--envelope key]
softschema-ts compile <mod.ts:ZodSchema> --contract <id> --out <sidecar.yaml> [--check]
softschema-ts inspect <doc.md>
softschema-ts generate <doc.md> [--check]
softschema-ts docs --list [--json] | softschema-ts docs <topic>
softschema-ts skill --brief | softschema-ts skill --install
```

## Library

```ts
import { z } from "zod";
import { compileSchema, validateArtifact, validateValues, SchemaView, softField } from "softschema";
```

Source schemas are Zod (`z.strictObject(...)`); validation uses `safeParse`; per-field
authoring metadata uses `softField(schema, {...})`. See
[the TypeScript design doc](../../docs/softschema-typescript-design.md) for the module
layout and the Python↔TypeScript API parity table, and the
[Softschema Guide](../../docs/softschema-guide.md) /
[Spec](../../docs/softschema-spec.md) for the language-neutral concept and artifact
format.

## Development

bun + bunup + biome.
`bun run check` runs lint, types, and tests.
The shared golden corpus (`tests/golden/`) runs against this CLI via
`SOFTSCHEMA_IMPL=ts`; a cross-implementation conformance test asserts the Zod and
Pydantic compilers produce an identical canonical sidecar.
See the parity development process in [docs/development.md](../../docs/development.md).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
