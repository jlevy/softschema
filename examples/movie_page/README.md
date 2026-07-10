# Movie Page Example

This example is deliberately small, complete, and paired across both official runtimes:

- [model.py](model.py) and [model.ts](model.ts) contain equivalent Pydantic and Zod
  models.
- [host_integration.py](host_integration.py) and
  [host_integration.ts](host_integration.ts) show idiomatic host-owned bindings and
  file-boundary validation.
- [spirited-away.md](spirited-away.md) contains the Markdown artifact.
- [spirited-away.yaml](spirited-away.yaml) contains the same payload as a pure YAML
  artifact with no Markdown body.
- `movie-page.schema.yaml` is the shared compiled schema.
  Both models compile to the same canonical content and `schema_sha256`.

The Markdown body reads like a compact movie page: a short synopsis, a details table,
the lead cast, and a ratings summary.
It overlaps with the YAML frontmatter without mirroring it field for field (the prose
adds the film’s Academy Award, which no structured field carries), and the YAML
frontmatter stays the authoritative source a consumer reads.
The pure YAML variant keeps the `softschema` metadata at the root and places the payload
beside it. Because it has no envelope, every root key except `softschema` belongs to the
payload.

The example deliberately exercises a representative mix of YAML shapes:

- Strings (`title`, `synopsis`).
- Constrained integers (`release_year` at least 1888, `runtime_minutes` positive).
- An enum (`mpaa_rating`: one of `G`, `PG`, `PG-13`, `R`, `NC-17`, `NR`).
- Lists of strings (`directors`, `genres`).
- A list of structured records (`cast`, each `{actor, character}`).
- Nested objects with their own typed fields (`ratings.rotten_tomatoes`, `ratings.imdb`,
  which carries a 0-10 float score).
- Optional fields (`mpaa_rating`, `tagline`, and either rating source may be omitted).

## Schema Enums

The block below is regenerated from `movie-page.schema.yaml` by
`softschema generate examples/movie_page/README.md`. CI runs the same command with
`--check` and fails on drift.

<!-- softschema:generated kind="enum_table" schema="movie-page.schema.yaml" -->
| Field | Allowed values |
| --- | --- |
| `mpaa_rating` | G, PG, PG-13, R, NC-17, NR |
<!-- /softschema:generated -->

Compile either trusted model and check the same committed schema:

```bash
# Python/Pydantic
softschema-py compile examples.movie_page.model:MoviePage \
  --contract example.movies:MoviePage/v1 \
  --out examples/movie_page/movie-page.schema.yaml --check

# TypeScript/Zod under Bun (from a project with softschema and Zod installed)
bunx --bun softschema compile examples/movie_page/model.ts:MoviePage \
  --contract example.movies:MoviePage/v1 \
  --out examples/movie_page/movie-page.schema.yaml --check
```

Node users compile `model.ts` to `.js` or `.mjs` first.
Model loading executes local code; use these commands only with a trusted model.
Repository development checks the copyable TypeScript model and host through
`bun test test/movie-page-example.test.ts` from `packages/typescript`.

The files are copyable directly or through the docs CLI:

```bash
softschema docs example
softschema docs example-artifact
softschema docs example-pure-yaml
softschema docs example-model
softschema docs example-host
```

Validate it with zero flags (from a repo checkout):

```bash
softschema validate examples/movie_page/spirited-away.md
softschema validate examples/movie_page/spirited-away.yaml --profile pure-yaml
```

The artifact carries format 1 and the descriptive fields (`contract`, `schema`,
`envelope`, `status`) in its `softschema:` block, so `softschema validate` resolves the
compiled schema and envelope automatically with no flags.
The pure YAML artifact carries the same contract, schema, and status but deliberately
omits `envelope`; `--profile pure-yaml` makes the remaining root mapping the payload.
The CLI never selects this profile from the `.yaml` extension.

Override flags are still available when a caller needs to override a binding:

```bash
softschema validate examples/movie_page/spirited-away.md \
  --schema examples/movie_page/movie-page.schema.yaml \
  --envelope movie
```

A Python host usually builds a registry once, then validates files by contract ID:

```python
from pathlib import Path

from examples.movie_page.host_integration import validate_movie_page

result = validate_movie_page(Path("examples/movie_page/spirited-away.md"))
assert result.ok
```

The import above assumes a repo checkout; see [host_integration.py](host_integration.py)
for the full source.

A TypeScript host binds the serializable descriptor to its Zod model once:

```ts
import { validateMoviePage } from "./host_integration.js";

const result = validateMoviePage("spirited-away.md");
if (!result.ok) throw new Error(JSON.stringify(result.output));
```

See [host_integration.ts](host_integration.ts) for the descriptor, bound runtime
contract, portable path resolution, and full return type.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
