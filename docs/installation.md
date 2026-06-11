# Installation

softschema ships two interchangeable implementations with the same CLI and library
surface: Python/Pydantic on PyPI and TypeScript/Zod on npm.
Pick the runtime you already have; both validate against the same canonical schema.

## Two Ways to Consume It

|  | Pin as a dependency | Zero-install (`uvx` / `npx`) |
| --- | --- | --- |
| **For** | Projects, CI gates, library use | One-off checks, agent bootstrap |
| **Reproducible** | Yes — the version is locked in `uv.lock` / `package-lock.json` | Only if you pin the runner (`uvx softschema@0.2.0`) |
| **Fast / offline** | Yes — the binary is already on disk | Cold-start fetch; needs the network |
| **Library import** | Yes — the only way | No |

The rule of thumb: **if softschema runs more than once, or in CI, or you import it — pin
it as a dependency.
For a quick one-off or an agent bootstrapping with nothing installed,
use a zero-install runner**, pinned where the result must be repeatable.

## Pin as a Dependency

Python (a dev dependency, or a persistent user tool):

```bash
uv add --dev softschema==0.2.0      # project dev dependency; run via `uv run softschema`
uv tool install softschema          # persistent CLI on your PATH
```

Node (>= 22.12):

```bash
npm install -D softschema@0.2.0     # or: pnpm add -D / bun add -d
npx softschema --help               # resolves the local pinned copy
```

## Zero-Install

```bash
uvx softschema@latest --help        # Python implementation, ephemeral
npx softschema@latest --help        # Node implementation, ephemeral
```

Use `uvx softschema@0.2.0` / `npx -y softschema@0.2.0` when a repeated ad-hoc run must
resolve the same version every time.

## Quick Start for Agents

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@latest --help` (for the Python implementation) or
> `npx softschema@latest --help` (for the Node implementation) and follow the
> instructions to set up softschema for this repo as a skill.

The help output points the agent to `skill --install`, which writes
`.agents/skills/softschema/SKILL.md` and `.claude/skills/softschema/SKILL.md` from the
repository root.

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

`@latest` is the recommended form for the agent-bootstrap path, including under a
release-age cool-off.
A gate such as npm’s `--before` / `NPM_CONFIG_BEFORE`, pnpm’s `minimumReleaseAge`, or
uv’s `--exclude-newer` resolves `@latest` to the newest release old enough to pass, so
you get the freshest vetted version without pinning.
A just-published version installs only once it ages past the cutoff.
Consumer projects should still pin their own dependency — a project’s reproducibility is
the project’s responsibility, not the publisher’s cool-off.
See [supply-chain-hardening](https://github.com/jlevy/supply-chain-hardening) for the
rationale.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
