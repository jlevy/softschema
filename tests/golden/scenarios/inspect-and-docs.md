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

  agents             Repo-level agent instructions.
  development        Local development workflow.
  example            Copyable example overview.
  example-artifact   Copyable Markdown/YAML artifact.
  example-host       Host registry and validation helper.
  example-model      Pydantic model used by the example.
  guide              Concepts, mental model, and adoption path.
  installation       Installing uv and Python.
  publishing         Release and PyPI workflow.
  python-design      Python package design decisions.
  readme             Short first-visitor overview.
  skill              Portable agent skill instructions.
  spec               Language-neutral artifact format.
  typescript-design  TypeScript package design decisions.

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

# Test: docs --list --json emits structured topic metadata

```console
$ softschema docs --list --json
{
  "copyable_examples": [
    "example",
    "example-artifact",
    "example-model",
    "example-host"
  ],
  "scaffolding": false,
  "topics": [
    {
      "name": "agents",
      "path": "AGENTS.md",
      "summary": "Repo-level agent instructions.",
      "title": "Agent Instructions"
    },
    {
      "name": "development",
      "path": "docs/development.md",
      "summary": "Local development workflow.",
      "title": "Development"
    },
    {
      "name": "example",
      "path": "examples/movie_page/README.md",
      "summary": "Copyable example overview.",
      "title": "Movie Page Example"
    },
    {
      "name": "example-artifact",
      "path": "examples/movie_page/spirited-away.md",
      "summary": "Copyable Markdown/YAML artifact.",
      "title": "Movie Page Artifact"
    },
    {
      "name": "example-host",
      "path": "examples/movie_page/host_integration.py",
      "summary": "Host registry and validation helper.",
      "title": "Movie Page Host Integration"
    },
    {
      "name": "example-model",
      "path": "examples/movie_page/model.py",
      "summary": "Pydantic model used by the example.",
      "title": "Movie Page Model"
    },
    {
      "name": "guide",
      "path": "docs/softschema-guide.md",
      "summary": "Concepts, mental model, and adoption path.",
      "title": "Softschema Guide"
    },
    {
      "name": "installation",
      "path": "docs/installation.md",
      "summary": "Installing uv and Python.",
      "title": "Installation"
    },
    {
      "name": "publishing",
      "path": "docs/publishing.md",
      "summary": "Release and PyPI workflow.",
      "title": "Publishing"
    },
    {
      "name": "python-design",
      "path": "docs/softschema-python-design.md",
      "summary": "Python package design decisions.",
      "title": "Python Package Design"
    },
    {
      "name": "readme",
      "path": "README.md",
      "summary": "Short first-visitor overview.",
      "title": "README"
    },
    {
      "name": "skill",
      "path": "skills/softschema/SKILL.md",
      "summary": "Portable agent skill instructions.",
      "title": "Softschema Skill"
    },
    {
      "name": "spec",
      "path": "docs/softschema-spec.md",
      "summary": "Language-neutral artifact format.",
      "title": "Softschema Spec"
    },
    {
      "name": "typescript-design",
      "path": "docs/softschema-typescript-design.md",
      "summary": "TypeScript package design decisions.",
      "title": "TypeScript Package Design"
    }
  ]
}
? 0
```

# Test: docs <topic> prints the bundled document (both CLIs, from bundled resources)

```console
$ softschema docs spec
# Softschema Spec
...
? 0
```
