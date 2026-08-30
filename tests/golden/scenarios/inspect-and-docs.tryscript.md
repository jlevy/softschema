---
cwd: ../../..
env:
  NO_COLOR: "1"
---

# Test: inspect reports envelope keys and softschema metadata

`profile` reports which artifact shape the file was read as, so a populated `metadata`
block beside `has_frontmatter: false` is explained rather than surprising.

```console
$ $SOFTSCHEMA inspect examples/movie_page/spirited-away.md
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
  "path": "examples/movie_page/spirited-away.md",
  "profile": "frontmatter-md"
}
? 0
```

# Test: docs --list shows the bundled documentation topics

```console
$ $SOFTSCHEMA docs --list
Available softschema docs:

  development        Local development workflow.
  example            Copyable example overview.
  example-artifact   Copyable Markdown/YAML artifact.
  example-host       Host registry and validation helper.
  example-model      Pydantic model used by the example.
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

```console
$ $SOFTSCHEMA skill --brief
# softschema Skill Brief

Use soft schemas when humans, agents, or software produce YAML records whose consumed
structure should stabilize over time.

- Choose the artifact profile independently of the contract status.
  Use the standard `frontmatter-md` profile when the YAML payload benefits from a
  Markdown body carrying context; use `pure-yaml` when the whole artifact is structured.
- YAML is authoritative for any consumed value.
  In `frontmatter-md`, the Markdown body is reader-facing.
  Do not parse Markdown body prose or tables for structured fields.
- Treat `soft`, `permissive`, and `enforced` as boundary maturity.
  Start with a named convention, validate the stable fields under authored rules, and
  enforce a bound structural schema when undeclared fields should fail.
- Evolve the schema as records and consumers reveal stable fields and constraints.
  Changing the schema or status does not require changing a Markdown body.
- Date- and timestamp-shaped YAML scalars are portable strings, quoted or unquoted.
  JSON Schema `format` is annotation-only; use a semantic model or an explicit
  structural assertion when date validity matters.
- The `softschema:` block is the self-description quartet: `contract` (the payload
  contract ID), `schema` (relative path to the compiled schema), `envelope` (the payload
  key), `status` (strictness).
  A fully self-describing artifact validates with `$SS validate <artifact>`, no flags.
- Add a field to the contract when a consumer relies on its name and meaning.
  Leave uncertain YAML extensions outside the contract until they stabilize.
- Use the optional Markdown body for provenance, reasoning, and caveats that do not fit
  fixed fields.
- Read `$SS docs guide` for the mental model.
- Read `$SS docs spec` for the exact artifact format.
- Inspect `$SS docs example` and `$SS docs example-artifact` for the copyable movie
  example; `$SS docs example-schema` prints its compiled schema.
- Validate at the boundary with `$SS validate`: no flags for a self-describing artifact;
  `--schema` to override with a compiled schema; `--model` for a Pydantic/Zod model
  (imports and runs local code; trusted models only; `--schema` is the safe path for
  untrusted input). Run `$SS validate --help` for exact syntax.
- **Check your own artifact before you finish, with `$SS repair`.** After writing a
  contract-bearing artifact, run it on that file.
  It fixes the two mistakes a model makes writing YAML by hand — an unquoted `: ` inside
  a value, and a scalar like `1850` that reads as a number where the contract wants a
  string — writes the file, and reports the verdict.
  Anything it does not fix, such as a missing field or a key that is a near-miss for the
  declared one, is yours to correct: it reports those and never guesses at them.
  A document it cannot read at all comes back as a record naming why, which is what a
  truncated write leaves behind.
  Add `--dry-run` to see what would change without writing, or `--check` to fail
  whenever anything would change, which is what a gate wants.
  `$SS validate` never writes; it is what a consumer runs, and it refuses an artifact it
  cannot read rather than reporting one.
- Keep examples copyable; do not scaffold or mutate a target project unless the user
  explicitly asks for that workflow.
? 0
```

# Test: docs --list --json emits structured topic metadata

```console
$ $SOFTSCHEMA docs --list --json
{
  "copyable_examples": [
    "example",
    "example-artifact",
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
$ $SOFTSCHEMA docs spec
# softschema Spec
...
? 0
```

# Test: inspect a document with frontmatter but no softschema block

A single non-`softschema` key is reported as the envelope; metadata is null.

```console
$ $SOFTSCHEMA inspect tests/golden/fixtures/plain-doc.md
{
  "envelope_keys": [
    "movie"
  ],
  "has_frontmatter": true,
  "metadata": null,
  "path": "tests/golden/fixtures/plain-doc.md",
  "profile": "frontmatter-md"
}
? 0
```

# Test: inspect a document with no frontmatter at all

```console
$ $SOFTSCHEMA inspect tests/golden/fixtures/no-frontmatter.md
{
  "envelope_keys": [],
  "has_frontmatter": false,
  "metadata": null,
  "path": "tests/golden/fixtures/no-frontmatter.md",
  "profile": "frontmatter-md"
}
? 0
```

# Test: skill prints the bundled SKILL.md (header asserted, fenced body elided)

The bare `skill` command prints the bundled `SKILL.md`. Its body contains fenced code
blocks, so the header is asserted and the remainder elided with `...`; the full text is
held byte-identical across packages by the skill-mirror drift unit test, and
`skill --brief` above is the un-elided bundled-resource check.

```console
$ $SOFTSCHEMA skill
---
name: softschema
...
? 0
```

# Test: inspect a pure-yaml artifact reads its root metadata block

`inspect` detects the profile the same way `validate` does, so the two never disagree
about what a file is. The root `softschema:` block is the metadata block and the
remaining root keys are the envelope candidates, while `has_frontmatter` stays literal:
a pure-yaml artifact has no frontmatter to report.

```console
$ $SOFTSCHEMA inspect tests/golden/fixtures/pure-yaml-report.yaml
{
  "envelope_keys": [
    "run_id",
    "summary"
  ],
  "has_frontmatter": false,
  "metadata": {
    "contract": "test.runs:BacktestReport/v1",
    "envelope": null,
    "schema": null,
    "status": null
  },
  "path": "tests/golden/fixtures/pure-yaml-report.yaml",
  "profile": "pure-yaml"
}
? 0
```
