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

- YAML is authoritative for any consumed value.
  In `frontmatter-md`, the Markdown body is reader-facing.
  Do not parse Markdown body prose or tables for structured fields.
- Choose the artifact profile independently of the contract status: `frontmatter-md`
  when the payload benefits from a Markdown body, `pure-yaml` when the whole artifact is
  structured data.
- The `softschema:` block names the contract (`contract`, the payload contract ID), the
  compiled schema (`schema`, a path relative to the document), the payload key
  (`envelope`), and the maturity (`status`: `soft`, `permissive`, or `enforced`). An
  artifact with all four validates with `$SS validate <artifact>` and no flags.
- Treat status as boundary maturity.
  A bound schema or model checks the payload under every status; `enforced` additionally
  rejects fields the schema does not declare.
  Add a field to the contract when a consumer relies on it, and leave uncertain fields
  outside it until they stabilize.
- After writing an artifact, run `$SS repair <file>`. It quotes a plain value YAML would
  read as structure (an unquoted `: `), escapes a raw control or line-separator
  character inside a value (`"\N"`, `"\x01"`), and quotes a scalar such as `1850` where
  the contract wants a string; then it writes the file and validates.
  It reports what it cannot fix and never guesses at it.
- At a boundary, run `$SS validate <file>`. It never writes.
  Add `--require structural` (or `semantic`, repeatable) when the handoff needs a check
  that actually ran: without it, an artifact with no schema bound can still be `valid`.
- Judge each check by `execution` as well as `ok`: `completed` means the validator ran
  and `ok` is its verdict; `not_run` and `errored` establish nothing.
  Declared status is no evidence that a validator ran, and a record without `execution`
  has unknown execution.
- Write YAML both engines read the same way: core-form numbers (`1000`, not `1_000`),
  printable text with escapes for control characters, spaces rather than tabs, no
  anchors, tags, or `%YAML 1.1`. The refusal message names the line and the fix.
- Date- and timestamp-shaped scalars are strings.
  JSON Schema `format` is annotation-only; use a semantic model or an explicit pattern
  when date validity matters.
- `--model` imports and runs local code; use it only with trusted models.
  `--schema` with a compiled schema executes nothing.
- Read `$SS docs guide` for the mental model and `$SS docs spec` for the exact rules.
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
