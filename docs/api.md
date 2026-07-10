# Library API

softschema exposes the same validation concepts in Python/Pydantic and TypeScript/Zod.
The names are idiomatic to each language; JSON-compatible values, contract semantics,
compiled schemas, and wire results are shared.

Use this reference for application integration.
See the [Guide](softschema-guide.md) for adoption and the [Spec](softschema-spec.md) for
exact language-neutral behavior.
Runtime internals belong in the [Python](softschema-python-design.md) and
[TypeScript](softschema-typescript-design.md) design references.

## Choose the Smallest Boundary

| Need | Python | TypeScript |
| --- | --- | --- |
| Validate an artifact path | `softschema.runtime.validate_artifact` | `softschema/node` `validateArtifact` |
| Validate already-extracted values | `softschema.runtime.validate_values` | `softschema/node` `validateValues` |
| Normalize or inspect portable data | `softschema.core` | `softschema/core` |
| Compile a trusted source model | `softschema.runtime.compile_model` | `softschema/node` `compileSchema` |
| Preserve existing imports | package root `softschema` | package root `softschema` |

The package roots remain compatibility facades in 0.3. New integrations should import
the explicit core or runtime adapter so filesystem, YAML, Pydantic/Zod, and dynamic-code
dependencies remain visible.

## Validate an Artifact

The library API requires a host-owned contract.
CLI-only binding inference from artifact metadata does not replace the host contract in
library code.

### Python

```python
from pathlib import Path

from softschema import Contract, Contracts, SchemaStatus
from softschema.runtime import validate_artifact

registry = Contracts()
registry.register(
    Contract(
        id="example.movies:MoviePage/v1",
        model=MoviePage,
        envelope_key="movie",
        status=SchemaStatus.enforced,
        schema_path=Path("movie-page.schema.yaml"),
    )
)

result = validate_artifact(
    Path("spirited-away.md"),
    contract_id="example.movies:MoviePage/v1",
    registry=registry,
)
if not result.ok:
    handle_validation_failure(result)
```

`Contract` may carry a Pydantic model, a compiled-schema path, or both.
Host bindings outrank document-declared schema and envelope values.
A contract with an unset binding may use the corresponding document metadata as a
fallback.

### TypeScript

```ts
import { defineContractDescriptor } from "softschema/core";
import { bindContract, validateArtifact } from "softschema/node";

const descriptor = defineContractDescriptor({
  id: "example.movies:MoviePage/v1",
  model: "./model.js:MoviePage",
  envelopeKey: "movie",
  status: "enforced",
  profile: "frontmatter-md",
  schemaPath: "movie-page.schema.yaml",
});
const contract = bindContract(descriptor, MoviePage);

const result = validateArtifact("spirited-away.md", contract);
if (!result.ok) handleValidationFailure(result.output);
const wire = result.output;
```

`ContractDescriptor` is serializable.
`bindContract` combines it with the executable Zod model exactly once and returns a
`RuntimeContract`. This prevents a descriptor’s model label from drifting from the
validator supplied at runtime.

The older `Contract` alias and `validateArtifact(..., { semanticModel })` overload
remain compatibility surfaces during 0.3. New code should use a bound runtime contract.

## Validate Pre-Extracted Values

Use the values API when another trusted adapter already parsed the artifact, or when the
source is not a native softschema file.
The input must still fit the portable value domain.

```python
from softschema.runtime import validate_values

result = validate_values(
    values,
    model=MoviePage,
    schema=Path("movie-page.schema.yaml"),
)
```

```ts
import { validateValues } from "softschema/node";

const result = validateValues(values, {
  model: MoviePage,
  schema: compiledSchema,
});
```

Both return separate structural and semantic reports.
Supplying neither a model nor a schema is an API error.

## Supply Offline Schema Resources

The root compiled schema may use fragments.
Any other referenced resource must be already loaded and supplied by canonical absolute
URI. Neither library retrieves it.

```python
result = validate_values(
    values,
    schema=Path("root.schema.yaml"),
    resources={
        "https://example.com/schemas/address/v1": address_schema,
    },
)
```

```ts
const result = validateValues(values, {
  schema: rootSchema,
  resources: {
    "https://example.com/schemas/address/v1": addressSchema,
  },
});
```

Every supplied resource passes the same dialect, metaschema, identity, pattern, value,
and resource-limit checks as the root.
A mapping key is authoritative; a resource `$id` must be absent or canonically equal to
it.

## Use the Portable Core

Core APIs accept JSON-compatible values and perform no YAML parsing, filesystem access,
network access, model import, or terminal I/O.

```python
from softschema.core import normalize_portable_value, validate_contract_id

contract_id = validate_contract_id("example.movies:MoviePage/v1")
values, encoded_size = normalize_portable_value(raw_values)
```

```ts
import {
  defineContractDescriptor,
  normalizePortableValue,
  validateContractId,
} from "softschema/core";
```

The core also exposes metadata, schema identity, portable pattern, canonicalization,
normalized result, source-map, and diagnostic projection types.
Prefer the named public exports over importing implementation files.

## Validation Limits

CLIs always use the conformance defaults.
Trusted library callers may supply explicit limits when a larger artifact is
intentional:

```python
from softschema import ValidationLimits

limits = ValidationLimits(max_resource_bytes=16 * 1024 * 1024)
result = validate_values(values, schema=path, limits=limits)
```

```ts
const result = validateValues(values, {
  schema,
  validationLimits: { maxResourceBytes: 16 * 1024 * 1024 },
});
```

Raising limits changes resource exposure.
Keep the defaults for untrusted CLI and repository input.

## Compile Trusted Models

Compilation executes the source model and therefore belongs on a trusted build path.
It separates logical contract identity from optional JSON Schema resource identity.

```python
from softschema.runtime import compile_model

compile_model(
    MoviePage,
    Path("movie-page.schema.yaml"),
    contract_id="example.movies:MoviePage/v1",
    schema_id="https://example.com/schemas/movie-page/v1",
)
```

```ts
import { compileSchema } from "softschema/node";

compileSchema(MoviePage, "movie-page.schema.yaml", {
  contractId: "example.movies:MoviePage/v1",
  schemaId: "https://example.com/schemas/movie-page/v1",
});
```

The compiled schema carries the contract ID in `x-softschema.contract`. `$id` appears
only when the caller supplies the separate schema identity.
The root `x-softschema` block is compiler-owned.
A model that supplies one is rejected before output is written; use per-field
`SoftField`/`softField` annotations for authoring metadata instead.

## Results and Exceptions

Validation failures are data.
In Python, inspect `ok`, `structural`, `semantic`, `warnings`, and the discriminated
input/parse/schema error records on the result model.
TypeScript `validateArtifact` returns `{ ok, output }`; inspect `result.ok` for the
aggregate outcome and `result.output.structural`, `.semantic`, and `.warnings` for the
shared legacy wire. Do not parse message prose.
`validateValues` returns its structural and semantic reports directly in both languages.

Programming errors still raise exceptions: invalid API argument combinations, invalid
contract descriptors, unsupported object values supplied directly by trusted code, and
I/O failures outside an artifact-validation result boundary.
The CLI translates its documented boundaries to stable output and exit codes; library
callers retain normal language exceptions for misuse.

TypeScript exports named wire and error types from `softschema/core` and
`softschema/node`. Python exports typed models from `softschema.core` and runtime result
models from `softschema.runtime` and the compatibility root.

## Complete Example

The [Movie Page Example](../examples/movie_page/README.md) contains equivalent
`model.py`/`model.ts` and `host_integration.py`/`host_integration.ts` sources that
target the same artifact and compiled schema.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
