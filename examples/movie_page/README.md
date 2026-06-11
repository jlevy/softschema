# Movie Page Example

This example is deliberately small and complete:

- [model.py](model.py) contains the Pydantic model.
- [host_integration.py](host_integration.py) shows how a host application registers the
  complete contract and validates an artifact at a file boundary.
- [spirited-away.md](spirited-away.md) contains the Markdown artifact.
- `movie-page.schema.yaml` is generated from the model.

The Markdown body reads like a compact movie page: a short synopsis, a details table,
the lead cast, and a ratings summary.
It overlaps with the YAML frontmatter without mirroring it field for field (the prose
adds the film’s Academy Award, which no structured field carries), and the YAML
frontmatter stays the authoritative source a consumer reads.

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

The example is meant to be copied from the files in this directory or printed through
the docs CLI:

```bash
softschema docs example
softschema docs example-artifact
softschema docs example-model
softschema docs example-host
```

Validate it with zero flags (from a repo checkout):

```bash
softschema validate examples/movie_page/spirited-away.md
```

The artifact carries the full self-description quartet (`contract`, `schema`,
`envelope`, `status`) in its `softschema:` block, so `softschema validate` resolves the
compiled schema and envelope automatically with no flags.

Override flags are still available when a caller needs to override a binding:

```bash
softschema validate examples/movie_page/spirited-away.md \
  --schema examples/movie_page/movie-page.schema.yaml \
  --envelope movie
```

A host application usually builds a registry once, then validates files by contract ID:

```python
from pathlib import Path

from examples.movie_page.host_integration import validate_movie_page

result = validate_movie_page(Path("examples/movie_page/spirited-away.md"))
assert result.ok
```

The import above assumes a repo checkout; see [host_integration.py](host_integration.py)
for the full source.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
