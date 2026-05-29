# Movie Page Example

This example is deliberately small and complete:

- [model.py](model.py) contains the Pydantic model.
- [host_integration.py](host_integration.py) shows how a host application registers the
  complete binding and validates an artifact at a file boundary.
- [spirited-away.md](spirited-away.md) contains the Markdown artifact.
- `movie-page.schema.yaml` is generated from the model.

The Markdown body reads like a compact movie page: a short synopsis, a details table, the
lead cast, and a ratings summary. It overlaps with the YAML frontmatter without mirroring
it field for field — the prose adds the film’s Academy Award, which no structured field
carries — and the YAML frontmatter stays the authoritative source a consumer reads.

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
`uv run softschema generate examples/movie_page/README.md`. CI runs the same command
with `--check` and fails on drift.

<!-- softschema:generated kind="enum_table" contract="movie-page.schema.yaml" -->
| Field | Allowed values |
| --- | --- |
| `mpaa_rating` | G, PG, PG-13, R, NC-17, NR |
<!-- /softschema:generated -->

The example is meant to be copied from the files in this directory or printed through
the docs CLI:

```bash
uv run softschema docs example
uv run softschema docs example-artifact
uv run softschema docs example-model
uv run softschema docs example-host
```

Validate it with:

```bash
uv run softschema validate examples/movie_page/spirited-away.md \
  --model examples.movie_page.model:MoviePage \
  --schema examples/movie_page/movie-page.schema.yaml
```

The command reads `softschema.contract`, `softschema.status`, and the `movie` envelope
from the artifact. Override flags are available for callers that need them.

A host application usually builds a registry once, then validates files by contract ID:

```python
from pathlib import Path

from examples.movie_page.host_integration import validate_movie_page

result = validate_movie_page(Path("examples/movie_page/spirited-away.md"))
assert result.ok
```

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
