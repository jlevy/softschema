# Installation

## Quick Start for Agents

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@latest --help` (for the Python implementation) or
> `npx softschema@latest --help` (for the Node implementation) and follow the
> instructions to set up softschema for this repo as a skill.

The help output points the agent to `skill --install`, which writes
`.agents/skills/softschema/SKILL.md` and `.claude/skills/softschema/SKILL.md` from the
repository root.

softschema ships two interchangeable implementations with the same CLI and library
surface. Pick the runtime you already have; both validate against the same canonical
schema.

## TypeScript / Node

Run without installing:

```bash
npx softschema@latest --help
```

Add to a project (Node >= 22.12):

```bash
npm install softschema     # or: pnpm add softschema / bun add softschema
```

## Python

softschema uses [uv](https://docs.astral.sh/uv/) for Python and dependencies.

Install uv on macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with Homebrew:

```bash
brew install uv
```

Run without installing, or install as a persistent tool:

```bash
uvx softschema@latest --help    # ephemeral
uv tool install softschema      # persistent CLI
```

To work in this repo, install Python with uv:

```bash
uv python install 3.13
```

## Supply-chain cool-off

`@latest` is the recommended form, including under a release-age cool-off.
A gate such as npm’s `--before` / `NPM_CONFIG_BEFORE`, pnpm’s `minimumReleaseAge`, or
uv’s `--exclude-newer` resolves `@latest` to the newest release old enough to pass, so
you get the freshest vetted version without pinning.
A just-published version installs only once it ages past the cutoff.
See [supply-chain-hardening](https://github.com/jlevy/supply-chain-hardening) for the
rationale.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
