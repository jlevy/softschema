# Development

Set up the repo:

```bash
uv sync --all-extras
```

Common workflows:

```bash
make lint
make lint-check
make test
make build
```

Direct commands:

```bash
uv run python devtools/lint.py --check
uv run pytest
uv run softschema docs --list
uv run softschema docs --list --json
uv run softschema skill --brief
uv build
```

The Python package is built from `packages/python/src/softschema`.

Documentation changes should follow `common-doc-guidelines.md`
(github.com/jlevy/practical-prose).
Keep the README short, keep conceptual guidance in `docs/softschema-guide.md`, and keep
exact format rules in `docs/softschema-spec.md`.

## Continuous Integration

Two softschema checks belong in CI for any project that depends on the package.

### Schema sidecar drift

A committed `.schema.yaml` file is *generated, but committed*. Run
`softschema compile ... --check` to fail the build when the committed sidecar drifts
from the source model:

```bash
uv run softschema compile examples.movie_page.model:MoviePage \
  --contract example.movies:MoviePage/v1 \
  --out examples/movie_page/movie-page.schema.yaml --check
```

Fix on drift: re-run the same command without `--check` and commit the regenerated
sidecar.

### Generated-section drift

If any Markdown file contains `softschema:generated` markers (see the guide’s “Keep
Schema Tables In Sync With Generated Sections” playbook), run the re-renderer in
`--check` mode so CI fails when the committed section lags behind the schema:

```bash
uv run softschema generate examples/movie_page/README.md --check
```

Fix on drift: re-run without `--check` and commit the regenerated section.

### Artifact validation

Run `softschema validate` against every artifact under version control whose contract is
fully defined:

```bash
uv run softschema validate examples/movie_page/spirited-away.md \
  --model examples.movie_page.model:MoviePage \
  --schema examples/movie_page/movie-page.schema.yaml
```

`validate` reads `softschema.contract`, `softschema.status`, and the single top-level
envelope key from the artifact by default.
`--contract`, `--status`, and `--envelope` are override flags.

### GitHub Actions

A minimal job that runs both checks:

```yaml
name: softschema

on:
  pull_request:
  push:
    branches: [main]

jobs:
  softschema:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --all-extras
      - name: Sidecar drift check
        run: |
          uv run softschema compile examples.movie_page.model:MoviePage \
            --contract example.movies:MoviePage/v1 \
            --out examples/movie_page/movie-page.schema.yaml --check
      - name: Validate example artifact
        run: |
          uv run softschema validate examples/movie_page/spirited-away.md \
            --model examples.movie_page.model:MoviePage \
            --schema examples/movie_page/movie-page.schema.yaml
```

### Pre-commit hook

For local runs before push, a `pre-commit` config that calls the same drift check:

```yaml
repos:
  - repo: local
    hooks:
      - id: softschema-sidecar-drift
        name: softschema sidecar drift
        language: system
        entry: uv run softschema compile examples.movie_page.model:MoviePage --contract example.movies:MoviePage/v1 --out examples/movie_page/movie-page.schema.yaml --check
        pass_filenames: false
        files: ^(examples/movie_page/model\.py|examples/movie_page/movie-page\.schema\.yaml)$
```

Adapt the paths and the `--model` / `--contract` / `--out` arguments to each schema in
your repository.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
