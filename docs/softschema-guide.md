# Softschema Guide

Soft schemas are a practice for adding structure gradually to artifacts that mix human
context and machine-readable values.

This is the standalone reference to hand to a human or coding agent that needs to
understand the pattern. For the exact file format, metadata keys, and validation rules,
see [Softschema Spec](softschema-spec.md). For the Python implementation, see the root
README and package docs.

The practice is programming-language agnostic. A softschema artifact is a Markdown/YAML
file with a payload contract. This repository demonstrates the pattern with a Python
package, but another project could map the same artifacts to TypeScript, Zod, JSON
Schema, database records, or custom validators.

## Problem

LLMs and agents make it easy to automate work that still looks like human reasoning:
mixed prose, judgment calls, partial structure, and implicit context. That work may be
automated, but not exact enough or structured enough for downstream tools.

Soft schemas solve this by letting teams promote only the values that are consumed,
while keeping the rest of the artifact readable.

## Core Idea

Automation, exactness, and structure are separate axes.

| Axis | Low End | High End | Softschema Role |
| --- | --- | --- | --- |
| Automation | human-performed | harness-driven | Artifacts are files that humans, agents, and code can all edit |
| Exactness | judgment-heavy | deterministic | Add validation where a boundary needs it |
| Structure | prose | typed records | Promote consumed values without discarding narrative context |

The usual path is:

```text
prose
  -> expected sections and vocabulary
  -> YAML/frontmatter values for consumed fields
  -> schema validation at boundaries
  -> pure data or deterministic code when the shape is stable
```

Projects do not need to move all the way to pure data. Many useful artifacts remain part
prose and part structured data.

## Default Artifact Pattern

Use Markdown with YAML frontmatter:

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  ratings:
    rotten_tomatoes:
      critics:
        label: Tomatometer
        score_percent: 96
        total_reviews: 225
      audience:
        label: Popcornmeter
        score_percent: 96
        total_ratings: 250000
        total_ratings_display: 250,000+
---
# Spirited Away (2001)

Rotten Tomatoes shows a 96% Tomatometer based on 225 critic reviews and a 96%
Popcornmeter based on 250,000+ audience ratings.
```

The YAML payload is authoritative. The Markdown body is a friendly projection for
readers. It can include prose, headings, summaries, and tables, but structured consumers
should not parse the body.

## Contract IDs

Contract IDs name artifact payload contracts.

Recommended form:

```text
namespace:UpperCamelCaseName/version
```

Examples:

- `example.movies:MoviePage/v1`
- `example.docs:IncidentReview/v1`
- `com.acme.docs:IncidentReview/1.0`

The name can resemble a class or type name, but it is not required to resolve to a class
in any language. The same contract may map to Pydantic, Zod, JSON Schema, a database
record, or a hand-authored validator.

## Authoring Rules

- Put structured values in YAML frontmatter, declared data sidecars, or pure data files.
- Treat Markdown body prose and tables as reader-facing projections.
- Never parse structured fields from the Markdown body.
- Use one top-level envelope key for normal document payloads.
- Use `softschema.contract` to identify the payload contract.
- Keep resolver details, schema sidecar paths, implementation language, and migration
  state out of authored artifacts unless a project has a specific reason to expose them.
- Distinguish data sidecars from schema sidecars. Data sidecars hold payload values;
  schema sidecars describe validation contracts.

The first Python package validates the default frontmatter shape, pure YAML artifacts,
and JSON Schema sidecars. It does not implement a generic data-sidecar loader. A host
project can still define a data-sidecar convention when payloads become too large for
frontmatter, but that convention should be explicit and documented by the host.

## Adoption Path

1. Pick one artifact that humans or agents already write.
2. Identify the values downstream consumers actually need.
3. Add those values to YAML frontmatter under one envelope key.
4. Add `softschema.contract`.
5. Keep the body readable.
6. Add a source model or JSON Schema sidecar when a boundary needs validation.
7. Tighten the model only when repeated failures show the structure needs to be more
   exact.

## How Agents Should Use This Repo

An agent can use this repository in three layers:

1. Read this guide to understand the mental model and adoption pattern.
2. Read [Softschema Spec](softschema-spec.md) for the exact artifact format.
3. Inspect [examples/movie_page](../examples/movie_page/README.md) and the Python
   package when it needs working code.

If the Python CLI is installed, the same material is available without knowing the file
layout:

```bash
softschema skill --brief
softschema docs --list --json
softschema docs guide
softschema docs spec
softschema docs example
softschema docs example-artifact
```

The example commands print copyable reference files. They do not scaffold or mutate a
target project.

When adding soft schemas to another project, first look for Markdown or YAML artifacts
whose values are already consumed by code, QA, review, or aggregation. Promote those
values into YAML. Leave the body readable.

## Relationship to the Python Package

The Python package is a convenience implementation:

- `SoftschemaBinding` maps a contract ID to a Pydantic model and optional JSON Schema
  sidecar
- `validate_artifact` validates an artifact
- `compile_model` emits JSON Schema sidecars from Pydantic models
- `softschema validate` reads `softschema.contract`, `softschema.status`, and a single
  payload envelope from the artifact by default

The concepts do not require Python.

## Host Integration Pattern

A host application owns the mapping from contract IDs to implementation schemas. In
Python, that usually means registering complete `SoftschemaBinding` objects during startup
or command setup, then validating artifacts at file boundaries:

```python
from pathlib import Path

from examples.movie_page.host_integration import build_movie_page_registry
from softschema import validate_artifact

registry = build_movie_page_registry()
result = validate_artifact(
    Path("examples/movie_page/spirited-away.md"),
    contract_id="example.movies:MoviePage/v1",
    registry=registry,
)
assert result.ok
```

The artifact still declares `softschema.contract` for portability and review. The host
registry decides what that contract means in the running application: a Pydantic model,
a JSON Schema sidecar, a future Zod schema, or another validator.

## Sidecars

There are two different sidecar ideas:

- Schema sidecars describe validation contracts, usually generated JSON Schema written
  as YAML.
- Data sidecars hold artifact payload values outside the Markdown frontmatter.

The Python package supports schema sidecars through `SoftschemaBinding.schema_path` and the
`softschema compile` command. It depends on `frontmatter-format` for frontmatter and
YAML mechanics, but `frontmatter-format` is not treated as a softschema data-sidecar
runtime.

Use frontmatter for small consumed payloads. Consider a data sidecar only when the
structured payload is large, machine-generated, or distracting to readers. When a host
project uses data sidecars, keep routing fields such as `softschema.contract` and a
short summary in frontmatter, and document exactly how consumers find and validate the
sidecar.

## Documentation Shape

The root README is a short subset of this guide. It should help a new visitor decide
what the repo is and run the example. This guide carries the durable concept and
adoption model. The spec carries exact artifact rules.

When changing the pattern, update the docs in this order:

1. Update this guide if the mental model or adoption advice changes.
2. Update [Softschema Spec](softschema-spec.md) if the artifact format changes.
3. Trim the README back to a short subset of the guide.

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
