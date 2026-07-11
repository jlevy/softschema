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

# Test: skill --brief prints the agent operating rules

````console
$ softschema skill --brief
# softschema Skill Brief

## Qualify a Runner

Derive required capabilities first: schema-only, pure YAML, Python/Pydantic, built
JavaScript/Zod, or Bun source TypeScript/Zod.
Try candidates in this order:

```bash
softschema doctor --json
uvx --from 'softschema==0.2.2' softschema doctor --json
npx --yes softschema@0.2.2 doctor --json
bunx --bun softschema@0.2.2 doctor --json
```

Accept a candidate only when protocol `1` reports the needed operation, runtime, and
model loader. For `pure-yaml`, also require `validate --help` to list the profile.
Reuse the complete qualifying command prefix.
If none qualifies, report the missing capability and runtime and say that softschema
must be installed or upgraded to a release that advertises it.
Do not improvise another runner.

## Route the Task

- **Author a contract or artifact:** read `softschema docs guide`, then
  `softschema docs spec` for exact rules and `softschema docs example` for copyable
  paired sources.
- **Validate one or many files:** run `softschema validate --help`; select the profile
  explicitly. Legacy JSON applies when discovery classifies one single explicit path as a
  regular file, including when a later read fails, and for the narrow missing-path or
  broken-symlink `not_found` exception; other discovery failures and batch work use
  diagnostic JSON/JSONL/SARIF.
- **Consume values in application code:** read `softschema docs api` when available;
  otherwise use `softschema docs guide` and the runtime design topic.
  Validate at the boundary and inspect structured result fields, not message prose.
- **Change softschema itself:** read the repository `AGENTS.md` and
  `softschema docs development`; update shared vectors first and keep Python, Node, and
  Bun green.

Validate a self-describing Markdown artifact with:

```bash
softschema validate doc.md
```

## Operating Rules

- Treat YAML/frontmatter as authoritative.
  Never parse Markdown body prose or tables for structured fields.
- Use `softschema.contract` for the logical payload contract; it is not a schema path,
  model import, or JSON Schema `$id`.
- Select `frontmatter-md` or `pure-yaml` explicitly.
  A filename suffix never selects a profile.
- Promote a value into YAML only when a downstream consumer needs it.
  Keep analysis, uncertainty, and judgment-heavy context as prose.
- Preserve unknown extension values as portable data.
  Extensions never authorize imports, retrieval, plugins, or validation behavior.
- Prefer a reviewed compiled schema for untrusted artifacts.
  Model loading imports and executes trusted local Pydantic or Zod code.
- Expect validation to remain offline.
  Only fragments and already-loaded explicit resources are available; never fetch a
  schema because a reference names a URI.
- Keep examples copyable.
  Do not scaffold, install, or mutate a project unless the user requested that action.

Use `softschema docs --list --json` to discover the installed topic set rather than
guessing a resource name.
? 0
````

# Test: docs --list --json emits structured topic metadata

```console
$ softschema docs --list --json
{
  "copyable_examples": [
    "example",
    "example-artifact",
    "example-pure-yaml",
    "example-model",
    "example-model-ts",
    "example-host",
    "example-host-ts",
    "example-schema"
  ],
  "scaffolding": false,
  "topics": [
    {
      "name": "agent-compatibility",
      "path": "docs/agent-compatibility.md",
      "summary": "Discovery and instruction paths for major coding agents.",
      "title": "Coding Agent Compatibility"
    },
    {
      "name": "api",
      "path": "docs/api.md",
      "summary": "Stable library and command-line surfaces.",
      "title": "API Reference"
    },
    {
      "name": "changelog",
      "path": "CHANGELOG.md",
      "summary": "Release history and user-visible changes.",
      "title": "Changelog"
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
      "name": "example-host-ts",
      "path": "examples/movie_page/host_integration.ts",
      "summary": "TypeScript host registry and validation helper.",
      "title": "Movie Page TypeScript Host Integration"
    },
    {
      "name": "example-model",
      "path": "examples/movie_page/model.py",
      "summary": "Pydantic model used by the example.",
      "title": "Movie Page Model"
    },
    {
      "name": "example-model-ts",
      "path": "examples/movie_page/model.ts",
      "summary": "Zod model used by the paired example.",
      "title": "Movie Page TypeScript Model"
    },
    {
      "name": "example-pure-yaml",
      "path": "examples/movie_page/spirited-away.yaml",
      "summary": "Copyable pure YAML artifact.",
      "title": "Movie Page Pure YAML Artifact"
    },
    {
      "name": "example-schema",
      "path": "examples/movie_page/movie-page.schema.yaml",
      "summary": "Compiled JSON Schema for the example.",
      "title": "Movie Page Compiled Schema"
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
      "name": "migration-0.3",
      "path": "docs/migration-0.3.md",
      "summary": "Compatibility and migration guidance for 0.3.",
      "title": "Migration to 0.3"
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
      "name": "security",
      "path": "SECURITY.md",
      "summary": "Supported versions, trust boundaries, and vulnerability reporting.",
      "title": "Security Policy"
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
