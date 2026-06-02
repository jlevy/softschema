---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: inspect reports envelope keys and softschema metadata

```console
$ softschema inspect examples/movie_page/spirited-away.md
{
  "envelope_keys": [
    "title",
    "movie"
  ],
  "has_frontmatter": true,
  "metadata": {
    "contract": "example.movies:MoviePage/v1",
    "status": "enforced"
  },
  "path": "examples/movie_page/spirited-away.md"
}
? 0
```

# Test: docs --list shows the bundled documentation topics

```console
$ softschema docs --list
Available softschema docs:

  agents            Repo-level agent instructions.
  development       Local development workflow.
  example           Copyable example overview.
  example-artifact  Copyable Markdown/YAML artifact.
  example-host      Host registry and validation helper.
  example-model     Pydantic model used by the example.
  guide             Concepts, mental model, and adoption path.
  installation      Installing uv and Python.
  publishing        Release and PyPI workflow.
  python-design     Python package design decisions.
  readme            Short first-visitor overview.
  skill             Portable agent skill instructions.
  spec              Language-neutral artifact format.

Run `softschema docs <topic>` to print a document.
Copy examples from the printed docs or from the repository files; the CLI does not scaffold or mutate projects.
? 0
```

# Test: skill --brief prints the agent operating rules

```console
$ softschema skill --brief
# Softschema Skill Brief

Use soft schemas when humans or agents write Markdown/YAML artifacts and tools need to
consume some values reliably.

- Read `softschema docs guide` for the mental model.
- Read `softschema docs spec` for the exact artifact format.
- Inspect `softschema docs example` and `softschema docs example-artifact` for the
  copyable movie example.
- Treat YAML/frontmatter as authoritative.
- Do not parse Markdown body prose or tables for consumed values.
- Use `softschema.contract` to name the payload contract.
- Keep examples copyable; do not scaffold or mutate a target project unless the user
  explicitly asks for that workflow.
? 0
```
