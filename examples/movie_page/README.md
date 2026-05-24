# Movie Page Example

This example is deliberately small and complete:

- [model.py](model.py) contains the Pydantic model.
- [spirited-away.md](spirited-away.md) contains the Markdown artifact.
- `movie-page.schema.yaml` is generated from the model.

The Markdown body reads like a compact movie page on a website. It repeats the title,
description, details table, and Rotten Tomatoes critics/audience ratings in a friendly
format, but the YAML frontmatter is the authoritative structure.

Validate it with:

```bash
uv run softschema validate examples/movie_page/spirited-away.md \
  --model examples.movie_page.model:MoviePage \
  --schema examples/movie_page/movie-page.schema.yaml
```

The command reads `softschema.contract`, `softschema.status`, and the `movie` envelope
from the artifact. Override flags are available for callers that need them.

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
