# Installation

softschema ships two interchangeable implementations with the same CLI and library
surface: Python/Pydantic on PyPI and TypeScript/Zod on npm.
Pick the runtime you already have; both validate against the same canonical schema.

## Two Ways to Consume It

|  | Install as a dependency | Zero-install (`uvx` / `npx`) |
| --- | --- | --- |
| **For** | Projects, CI gates, library use | One-off checks, agent bootstrap |
| **Reproducible** | Yes—the version is locked in `uv.lock` / `package-lock.json` | No—`@latest` resolves at invocation time |
| **Fast / offline** | Yes—the binary is already on disk | Cold-start fetch; needs the network |
| **Library import** | Yes—the only way | No |

The rule of thumb: **if softschema runs more than once, or in CI, or you import it—add
it as a project dependency and commit the lockfile.
For a quick one-off or an agent bootstrapping with nothing installed, use a zero-install
runner**.

## Install as a Dependency

Python (a dev dependency, or a persistent user tool):

```bash
uv add --dev softschema             # project dev dependency; run via `uv run softschema`
uv tool install softschema          # persistent CLI on your PATH
```

Node (>= 22.12):

```bash
npm install -D softschema@latest    # or: pnpm add -D / bun add -d
npx softschema --help               # resolves the local pinned copy
```

## Zero-Install

```bash
uvx softschema@latest --help       # Python implementation, ephemeral
npx -y softschema@latest --help    # Node implementation, ephemeral
```

These commands resolve the latest published release.
Use the project-dependency path above when a workflow must be repeatable.

## Quick Start for Agents

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@latest --help` (for the Python implementation) or
> `npx -y softschema@latest --help` (for the Node implementation) and follow the
> instructions to set up softschema for this repo as a skill.

The help output points to the explicit project install:

```bash
softschema skill --install --scope project --agent portable --agent claude
```

This writes `.agents/skills/softschema/SKILL.md` and
`.claude/skills/softschema/SKILL.md` from the repository root.
Use one `--agent` when only one mirror is wanted; use `--dry-run` to preview.

## Installing uv

softschema’s Python implementation is easiest to run with
[uv](https://docs.astral.sh/uv/). Install it on macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with Homebrew:

```bash
brew install uv
```

## Supply-chain Cool-off

Zero-install commands use `@latest` for low-friction one-off checks and agent bootstrap.
They are intentionally not reproducible.
Projects and CI should install softschema as a dependency, commit the normal lockfile,
and apply a release-age cool-off when updating it.
See [supply-chain-hardening](https://github.com/jlevy/supply-chain-hardening) for the
rationale.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
