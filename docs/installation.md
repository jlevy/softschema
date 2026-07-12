# Installation

softschema ships two interchangeable implementations with the same CLI and library
surface: Python/Pydantic on PyPI and TypeScript/Zod on npm.
Pick the runtime you already have; both validate against the same canonical schema.

## Two Ways to Consume It

|  | Pin as a dependency | Zero-install (`uvx` / `npx`) |
| --- | --- | --- |
| **For** | Projects, CI gates, library use | One-off checks, agent bootstrap |
| **Reproducible** | Yes—the version is locked in `uv.lock` / `package-lock.json` | Only if you pin the runner (`uvx softschema@0.2.2`) |
| **Fast / offline** | Yes—the binary is already on disk | Cold-start fetch; needs the network |
| **Library import** | Yes—the only way | No |

The rule of thumb: **if softschema runs more than once, or in CI, or you import it—pin
it as a dependency.
For a quick one-off or an agent bootstrapping with nothing installed,
use a zero-install runner**, pinned where the result must be repeatable.

## Pin as a Dependency

Python (a dev dependency, or a persistent user tool):

```bash
uv add --dev softschema==0.2.2      # project dev dependency; run via `uv run softschema`
uv tool install softschema          # persistent CLI on your PATH
```

Node (>= 22.12):

```bash
npm install -D softschema@0.2.2     # or: pnpm add -D / bun add -d
npx softschema --help               # resolves the local pinned copy
```

## Zero-Install

```bash
uvx softschema@0.2.2 --help        # Python implementation, ephemeral
npx -y softschema@0.2.2 --help     # Node implementation, ephemeral
```

The exact version is the last verified zero-install release.
Update the pin deliberately after verifying a newer release.

## Quick Start for Agents

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@0.2.2 --help` (for the Python implementation) or
> `npx -y softschema@0.2.2 --help` (for the Node implementation) and follow the
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

Zero-install commands use an exact version because consumer environments cannot be
assumed to enforce a release-age gate.
Projects should also pin their dependency in the normal lockfile.
When evaluating an upgrade, apply a release-age cool-off and review the lockfile or
resolved artifact before changing either pin.
See [supply-chain-hardening](https://github.com/jlevy/supply-chain-hardening) for the
rationale.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
