# Movie Page Example

This example is deliberately small and complete:

- [model.py](model.py) contains the Pydantic model.
- [host_integration.py](host_integration.py) shows how a host application registers the
  complete binding and validates an artifact at a file boundary.
- [spirited-away.md](spirited-away.md) contains the Markdown artifact.
- `movie-page.schema.yaml` is generated from the model.

The Markdown body reads like a compact movie page on a website.
It repeats the title, description, details table, and Rotten Tomatoes critics/audience
ratings in a friendly format, but the YAML frontmatter is the authoritative structure.

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

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
