---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: inspect reports the complete public document summary

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
    "envelope": "movie",
    "schema": "movie-page.schema.yaml",
    "status": "enforced"
  },
  "path": "examples/movie_page/spirited-away.md"
}
? 0
```

# Test: docs discovery exposes every bundled topic

```console
$ softschema docs --list
Available softschema docs:

  agent-compatibility  Discovery and instruction paths for major coding agents.
  api                  Stable library and command-line surfaces.
  changelog            Release history and user-visible changes.
  development          Local development workflow.
  example              Copyable example overview.
  example-artifact     Copyable Markdown/YAML artifact.
  example-host         Host registry and validation helper.
  example-host-ts      TypeScript host registry and validation helper.
  example-model        Pydantic model used by the example.
  example-model-ts     Zod model used by the paired example.
  example-pure-yaml    Copyable pure YAML artifact.
  example-schema       Compiled JSON Schema for the example.
  guide                Concepts, mental model, and adoption path.
  installation         Installing softschema for Node or Python.
  migration-0.3        Compatibility and migration guidance for 0.3.
  python-design        Python package design decisions.
  readme               Short first-visitor overview.
  security             Supported versions, trust boundaries, and vulnerability reporting.
  skill                Portable agent skill instructions.
  spec                 Language-neutral artifact format.
  typescript-design    TypeScript package design decisions.

Run `softschema docs <topic>` to print a document.
Copy examples from the printed docs or from the repository files; the CLI does not scaffold or mutate projects.
? 0
```

# Test: docs reads a bundled topic

```console
$ softschema docs spec
# softschema Spec
...
? 0
```
