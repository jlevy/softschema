# softschema (TypeScript/Zod)

The TypeScript implementation of [softschema](https://github.com/jlevy/softschema)
validates Markdown/frontmatter and pure YAML artifacts against portable JSON Schema and
optional trusted Zod models.
The PyPI Python/Pydantic package implements the same artifact, CLI, compiled-schema, and
result contracts with idiomatic Python APIs.

This package README follows the artifact version packed for npm.
Repository-wide quickstarts and agent bootstrap stay on the last dual-registry-verified
release instead.

## Install

<!-- BEGIN SOFTSCHEMA CLAIM npm-version -->
```bash
npm install --save-dev --save-exact softschema@0.2.2
# or: bun add --dev --exact softschema@0.2.2
```
<!-- END SOFTSCHEMA CLAIM npm-version -->

Node 22.12 or later runs built `.js` and `.mjs` model modules.
Bun 1.3.11 or later may also load direct `.ts`; that path does not promise tsconfig
aliases or non-erasable TypeScript syntax.

## CLI

```bash
softschema-ts validate doc.md
softschema-ts validate doc.yaml --profile pure-yaml
softschema-ts validate docs --recursive --format jsonl
softschema-ts compile model.mjs:Model --contract example.docs:Report/v1 \
  --schema-id https://example.com/schemas/report/v1 --out report.schema.yaml
softschema-ts doctor --json
softschema-ts docs --list --json
```

`frontmatter-md` is the default; a filename suffix never selects `pure-yaml`. Model
modules execute trusted local code.
Compiled-schema validation is offline and performs no implicit HTTP, file, or
relative-resource retrieval.

## Library

```ts
import { z } from "zod";
import { defineContractDescriptor } from "softschema/core";
import { bindContract, validateArtifact } from "softschema/node";

const MoviePage = z.strictObject({ title: z.string() });
const descriptor = defineContractDescriptor({
  id: "example.movies:MoviePage/v1",
  model: "./model.js:MoviePage",
  envelopeKey: "movie",
  status: "enforced",
  profile: "frontmatter-md",
  schemaPath: "movie-page.schema.yaml",
});
const result = validateArtifact("movie.md", bindContract(descriptor, MoviePage));
```

Use `softschema/core` for JSON-compatible metadata, identity, value, schema, result, and
diagnostic behavior without Node, YAML, filesystem, Zod, or CLI dependencies.
Use `softschema/node` for Node/Bun adapters.
The package root remains a 0.3 compatibility facade; new code should select the explicit
subpath.

The older `Contract` alias and `validateArtifact(..., { semanticModel })` overload are
deprecated compatibility surfaces.
Bind the serializable descriptor and Zod model once for new integrations.

## Documentation

- [Guide](https://github.com/jlevy/softschema/blob/main/docs/softschema-guide.md):
  adoption and workflows
- [Spec](https://github.com/jlevy/softschema/blob/main/docs/softschema-spec.md): exact
  language-neutral behavior
- [Library API](https://github.com/jlevy/softschema/blob/main/docs/api.md): paired
  Python and TypeScript entrypoints
- [TypeScript Design](https://github.com/jlevy/softschema/blob/main/docs/softschema-typescript-design.md):
  module and loader decisions
- [0.3 Migration](https://github.com/jlevy/softschema/blob/main/docs/migration-0.3.md):
  compatibility changes

The installed CLI exposes bundled public topics through `softschema docs --list`.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
