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
    "envelope": "movie",
    "schema": "movie-page.schema.yaml",
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

  development        Local development workflow.
  example            Copyable example overview.
  example-artifact   Copyable Markdown/YAML artifact.
  example-host       Host registry and validation helper.
  example-model      Pydantic model used by the example.
  guide              Concepts, mental model, and adoption path.
  installation       Installing softschema for Node or Python.
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
# softschema Skill Brief

Use soft schemas when humans or agents write Markdown/YAML artifacts and tools need to
consume some values reliably.

- YAML/frontmatter is authoritative for any consumed value.
  Do not parse Markdown body prose or tables for structured fields.
- Use `softschema.contract` (not `schema`) to name the payload contract.
- Promote a value into YAML only when something consumes it; leave exploratory or
  judgment-heavy content as prose.
- Read `$SS docs guide` for the mental model.
- Read `$SS docs spec` for the exact artifact format.
- Inspect `$SS docs example` and `$SS docs example-artifact` for the copyable movie
  example.
- Validate at the boundary with `$SS validate`: `--model` for a Pydantic/Zod model,
  `--schema` for a compiled schema.
  Run `$SS validate --help` for exact syntax.
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
      "title": "softschema Guide"
    },
    {
      "name": "installation",
      "path": "docs/installation.md",
      "summary": "Installing softschema for Node or Python.",
      "title": "Installation"
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
      "title": "softschema Skill"
    },
    {
      "name": "spec",
      "path": "docs/softschema-spec.md",
      "summary": "Language-neutral artifact format.",
      "title": "softschema Spec"
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
# softschema Spec
...
? 0
```

# Test: inspect a document with frontmatter but no softschema block

A single non-`softschema` key is reported as the envelope; metadata is null.

```console
$ softschema inspect tests/golden/fixtures/plain-doc.md
{
  "envelope_keys": [
    "movie"
  ],
  "has_frontmatter": true,
  "metadata": null,
  "path": "tests/golden/fixtures/plain-doc.md"
}
? 0
```

# Test: inspect a document with no frontmatter at all

```console
$ softschema inspect tests/golden/fixtures/no-frontmatter.md
{
  "envelope_keys": [],
  "has_frontmatter": false,
  "metadata": null,
  "path": "tests/golden/fixtures/no-frontmatter.md"
}
? 0
```

# Test: skill prints the bundled SKILL.md (header asserted, fenced body elided)

The bare `skill` command prints the bundled `SKILL.md`. Its body contains fenced code
blocks, so the header is asserted and the remainder elided with `...`; the full text is
held byte-identical across packages by the skill-mirror drift unit test, and
`skill --brief` above is the un-elided bundled-resource check.

```console
$ softschema skill
---
name: softschema
...
? 0
```
