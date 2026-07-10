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
softschema-ts validate <doc.md> --schema <schema.yaml> [--model mod.mjs:Export] [--envelope key]
softschema-ts validate <doc.yaml> --profile pure-yaml
softschema-ts compile <mod.mjs:ZodSchema> --contract <id> --out <schema.yaml> [--check]
softschema-ts inspect <doc.md>
softschema-ts generate <doc.md> [--check]
softschema-ts docs --list [--json] | softschema-ts docs <topic>
softschema-ts skill --brief | softschema-ts skill --install
```

The default is `frontmatter-md`; `.yaml` and `.yml` never select `pure-yaml` implicitly.
Model modules execute trusted local code.
Node.js supports built `.js` and `.mjs` modules.
Bun additionally supports direct `.ts`; this path does not promise tsconfig aliases or
non-erasable TypeScript syntax.

## Library

```ts
import { z } from "zod";
import {
  defineContractDescriptor,
  normalizePortableValue,
  parseSchemaMetadata,
} from "softschema/core";
import {
  bindContract,
  compileSchema,
  SchemaView,
  softField,
  validateArtifact,
  validateValues,
} from "softschema/node";

const descriptor = defineContractDescriptor({
  id: "example.movies:MoviePage/v1",
  model: "./movie-page.model.js:MoviePage",
  envelopeKey: "movie",
  status: "permissive",
  profile: "frontmatter-md",
  schemaPath: "movie-page.schema.yaml",
});
const contract = bindContract(descriptor, z.object({ title: z.string() }));
const result = validateArtifact("movie.md", contract);
```

Use `softschema/core` for JSON-compatible contract behavior without Node.js, YAML, Zod,
filesystem, or CLI dependencies.
Use `softschema/node` for the Node.js and Bun runtime adapters.
The `softschema` root retains the v0.2 Node.js/Bun exports as a compatibility facade;
new integrations should select the explicit subpath.
`Contract` and the `validateArtifact(..., { semanticModel })` overload remain deprecated
v0.2 compatibility surfaces.
New code should keep portable configuration in `ContractDescriptor`, bind Zod once with
`bindContract`, and validate with the resulting `RuntimeContract`.

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
