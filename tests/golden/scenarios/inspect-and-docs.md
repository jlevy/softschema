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
    "format": "1",
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
  example-pure-yaml  Copyable pure YAML artifact.
  example-schema     Compiled JSON Schema for the example.
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

````console
$ softschema skill --brief
# softschema Skill Brief

## Select a Capable Command

Derive the required capabilities before running an operation:

- Schema-only validation needs the operation, `json-schema`, and the artifact format.
- Pure YAML validation also needs the `pure-yaml` storage profile.
- A `.py` model needs the `python` runtime and `pydantic` model loader.
- A built `.js` or `.mjs` model needs `node` or `bun` and the `zod` model loader.
- A direct `.ts` model needs `bun` and the `zod` model loader.

Try these discovery commands in order, skipping a fallback whose ecosystem cannot load
the requested model:

```bash
softschema doctor --json
uvx --from 'softschema==0.2.2' softschema doctor --json
npx --yes softschema@0.2.2 doctor --json
bunx --bun softschema@0.2.2 doctor --json
```

An executable name or version string is not enough.
Accept a candidate only when its JSON reports protocol `1`, the required operation, a
supported artifact format, and the required runtime and model loader.
Protocol `1` does not report storage profiles yet.
For a pure YAML task, also run that candidate prefix with `validate --help` and accept
it only when the help advertises both `--profile` and `pure-yaml`; otherwise continue to
the next fallback. If none qualifies, stop and report that the `pure-yaml` profile is
unavailable and that softschema must be installed or upgraded to a release whose
`validate --help` lists it.
Reuse that candidate’s entire command prefix by replacing the trailing `doctor --json`
arguments. If none qualifies, stop and report the missing capability plus the exact
runtime (uv/Python, Node, or Bun) the user can install.

After qualification, validate a self-describing file with:

```bash
softschema validate doc.md
```

## Operating Rules

- Treat YAML/frontmatter as authoritative for every consumed value.
  Never parse Markdown body prose or tables for structured fields.
- Select the storage profile explicitly.
  `frontmatter-md` is the default; pass `--profile pure-yaml` for a YAML artifact with
  no Markdown body. Never infer a profile from `.yaml` or `.yml`.
- In `pure-yaml`, treat the root `softschema` block as metadata.
  Without a declared or overridden envelope, the remaining root mapping is the payload.
- Use `softschema.contract` for the payload contract ID. When authoring a new artifact,
  use a mapping and include the exact quoted `softschema.format: "1"` discriminator.
  An absent format is the legacy grammar, not the package or contract version.
  The block can also declare `schema`, `envelope`, and `status`.
- Put extension metadata only in the format-1 `softschema.extensions` mapping.
  Use a canonical lowercase reverse-DNS or HTTPS namespace for each key.
  Preserve unknown portable values without interpreting them; extensions never authorize
  loading code or changing core validation.
- Promote a value into YAML only when a downstream consumer needs it.
  Keep exploratory or judgment-heavy content as prose.
- Validate self-describing artifacts without override flags.
  Use `--schema` only for an explicit compiled-schema override.
  Use `--model` only with trusted local Pydantic or Zod code because model loading
  executes code.
- Read the bundled `guide` for the mental model, `spec` for exact format rules, and
  `example-artifact`, `example-pure-yaml`, and `example-schema` for copyable inputs.
  Run the qualifying prefix with `docs --list` to discover every topic.
- Keep examples copyable; do not scaffold, install, or mutate a project unless the user
  explicitly requests that workflow.
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
    "example-host",
    "example-schema"
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
