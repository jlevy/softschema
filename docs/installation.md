# Installation

softschema ships a Python/Pydantic package on PyPI and a TypeScript/Zod package on npm.
Choose the runtime already present in the host project.
Both implement the same artifact, CLI, compiled-schema, result, and conformance
contracts.

## Choose Persistent or Zero-Install Use

|  | Project dependency | Exact-pinned zero-install runner |
| --- | --- | --- |
| Best for | CI, repeated validation, library imports | One-off checks and agent bootstrap |
| Reproducibility | Lockfile plus exact dependency constraint | Exact package pin in every invocation |
| Offline use | Available after the project install | Requires a prior cache or network fetch |
| Library import | Yes | No stable project dependency |

If softschema runs repeatedly, is imported, or gates CI, add it to the project and
commit the lockfile.
Use zero-install for a temporary check or an agent in an ephemeral environment.

## Pin a Project Dependency

<!-- BEGIN SOFTSCHEMA CLAIM installation-python-pin -->
```bash
# Python/Pydantic
uv add --dev softschema==0.2.2
uv run softschema --help
```
<!-- END SOFTSCHEMA CLAIM installation-python-pin -->

<!-- BEGIN SOFTSCHEMA CLAIM installation-npm-pin -->
```bash
# Node/Zod
npm install --save-dev --save-exact softschema@0.2.2
npx softschema --help
```
<!-- END SOFTSCHEMA CLAIM installation-npm-pin -->

`bun add --dev --exact softschema@<pin>` and an exact pnpm dependency are equivalent
when those are the project’s package managers.
Do not resolve a second copy through `npx` after pinning; the unqualified
`npx softschema` command uses the local dependency.

## Run Without Adding a Dependency

```bash
# Python
uvx --from 'softschema==0.2.2' softschema --help

# Node
npx --yes softschema@0.2.2 --help

# Bun, including direct trusted .ts model loading
bunx --bun softschema@0.2.2 --help
```

The exact ecosystem pins come from `release-metadata.json`. Development checkouts keep
the last resolvable published pair; they never generate a fallback to an unpublished VCS
or prerelease version.
Update the pin and lockfile deliberately after reviewing a new release.

## Work From This Source Checkout

Repository development uses locked third-party dependencies without letting the build
backend resolve a second environment:

```bash
uv sync --all-extras --no-install-project
uv pip install --no-build-isolation --no-deps --editable .

cd packages/typescript
bun install --frozen-lockfile
```

These commands install development source, not a published security update.
The root `release-metadata.json` distinguishes development, candidate, and released
bytes.

## Set Up a Coding Agent

From a non-home Git repository, first inspect capabilities and preview every write:

```bash
softschema doctor --json
softschema skill --install --project --dry-run --text
softschema skill --install --project --text
```

With no selector, project mode writes the portable `.agents/skills` target and the
Claude `.claude/skills` mirror.
Explicit `--agent NAME` selectors replace that pair; `--all-agents` selects the nine
native targets in [Coding-Agent Compatibility](agent-compatibility.md).

Global installation is never inferred.
It requires `--global` plus explicit selectors or `--all-agents`, resolves each actual
personal base, and applies containment, ownership, and lock checks independently:

```bash
softschema skill --install --global --agent codex --dry-run --text
```

Project mode outside Git requires an explicit destination and acknowledgment:

```bash
softschema skill --install --project --no-repo-check --dir /absolute/project --dry-run --text
```

Project installation always refuses the filesystem root and actual home directory.
The installer never overwrites unmanaged, locally modified, unknown, or newer-format
content.

## Install uv

The Python commands require
[uv](https://docs.astral.sh/uv/getting-started/installation/). Use Astral’s documented
installer or a trusted system package manager, then verify the binary and version before
running a project command.

## Supply-Chain Policy

An exact pin makes the selected package deterministic; a release-age policy is a
separate defense. Consumers may apply uv `exclude-newer`, npm `--before`, or pnpm
`minimumReleaseAge` according to their own threat model.
An age policy does not make an unpinned runner reproducible, and a package cannot
guarantee the consumer’s ambient configuration.

See [Supply-Chain Security](../SUPPLY-CHAIN-SECURITY.md) for this repository’s build and
dependency controls and [Security](../SECURITY.md) before processing hostile input with
the published 0.2.2 release.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
