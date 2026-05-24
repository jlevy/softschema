# Publishing

The package uses dynamic Git versioning. Create a GitHub release with a tag such as
`v0.1.0` to publish through the `publish.yml` workflow after PyPI trusted publishing is
configured for this repository.

Before a release:

```bash
uv run python devtools/lint.py --check
uv run pytest
uv build
```

Configure PyPI trusted publishing with:

- project name: `softschema`
- owner/repo: `jlevy/softschema`
- workflow: `publish.yml`

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
