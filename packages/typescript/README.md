# softschema

The TypeScript/Zod implementation of [softschema](https://github.com/jlevy/softschema):
validate and structure Markdown/YAML artifacts with typed YAML contracts.
It is the idiomatic Zod counterpart to the Python/Pydantic package and is held to exact
behavioral parity with it: the same CLI inputs/outputs/flags, the same library surface,
and the same canonical compiled JSON Schema (content-identical, equal `schema_sha256`
over its canonical JSON; YAML serialization bytes may differ).

```bash
npx --yes softschema@0.2.2 --help       # zero-install, exact pin
# or
bun add softschema
```

## CLI

`softschema-ts` exposes the same commands and flags as the Python `softschema`:

```bash
softschema-ts validate <doc.md> --schema <schema.yaml> [--model mod.ts:Export] [--envelope key]
softschema-ts validate <doc.yaml> --profile pure-yaml
softschema-ts compile <mod.ts:ZodSchema> --contract <id> --out <schema.yaml> [--check]
softschema-ts inspect <doc.md>
softschema-ts generate <doc.md> [--check]
softschema-ts docs --list [--json] | softschema-ts docs <topic>
softschema-ts skill --brief | softschema-ts skill --install
```

The default is `frontmatter-md`; `.yaml` and `.yml` never select `pure-yaml` implicitly.

## Library

```ts
import { z } from "zod";
import { normalizePortableValue, parseSchemaMetadata } from "softschema/core";
import {
  compileSchema,
  SchemaView,
  softField,
  validateArtifact,
  validateValues,
} from "softschema/node";
```

Use `softschema/core` for JSON-compatible contract behavior without Node.js, YAML, Zod,
filesystem, or CLI dependencies.
Use `softschema/node` for the Node.js and Bun runtime adapters.
The `softschema` root retains the v0.2 Node.js/Bun exports as a compatibility facade;
new integrations should select the explicit subpath.

Source schemas are Zod (`z.strictObject(...)`); validation uses `safeParse`; per-field
authoring metadata uses `softField(schema, {...})`. See
[the TypeScript design doc](../../docs/softschema-typescript-design.md) for the module
layout and the Python↔TypeScript API parity table, and the
[softschema Guide](../../docs/softschema-guide.md) /
[Spec](../../docs/softschema-spec.md) for the language-neutral concept and artifact
format.

## Development

bun + bunup + biome.
`bun run check` runs lint, types, and tests.
The shared golden corpus (`tests/golden/`) runs against this CLI via
`SOFTSCHEMA_IMPL=ts`; a cross-implementation conformance test asserts the Zod and
Pydantic compilers produce an identical canonical compiled schema.
See the parity development process in [docs/development.md](../../docs/development.md).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
