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

### Faster YAML Parsing in Python

The Python implementation reads YAML with ruamel.yaml, which can use an optional C
extension, `ruamel.yaml.clib`: a Cython wrapper around a lightly patched libyaml 0.1.7,
with prebuilt wheels for CPython 3.9–3.14 on Linux, macOS, and Windows.
ruamel.yaml 0.18 depended on it on CPython below a Python-version cap (below 3.13 for
0.18.0–0.18.10, below 3.14 for 0.18.11–0.18.16, and below 3.15 for 0.18.17), so most
0.18 releases install without it on Python 3.13 and 3.14. ruamel.yaml 0.19.0 depended on
`ruamel.yaml.clibz` instead, and since 0.19.1 the C extension is opt-in (the
`oldlibyaml` extra).
The newer `ruamel.yaml.clibz` is the same libyaml, compiled with Zig at install time and
published only as source; ruamel’s `YAML()` API does not use it, so it gives no speedup
here.

libyaml parses YAML 1.1 and pure ruamel YAML 1.2, so they disagree on some texts.
softschema gives libyaml only the texts on which the two were shown to agree, and reads
the rest, and anything libyaml rejects, with pure ruamel.
It uses libyaml only for clib’s libyaml 0.1.7 on ruamel.yaml 0.18–0.19, so results are
the same either way; only speed changes, several times faster on large documents (see
[Performance](softschema-guide.md#performance) in the guide).

To get the speedup, install `ruamel.yaml.clib` (`uv add ruamel.yaml.clib`, or
`--with ruamel.yaml.clib` for `uv tool install` and `uvx`), not `ruamel.yaml[libyaml]`:

```bash
uv add ruamel.yaml.clib                               # in a project
uv tool install softschema --with ruamel.yaml.clib    # persistent CLI
uvx --with ruamel.yaml.clib softschema@latest doctor  # zero-install
```

A bare `uvx softschema@latest` runs the pure parser.
`softschema.yaml_parser_mode()` returns `"c-first"` when libyaml is in use and `"pure"`
otherwise, `softschema doctor` reports the same with the reason (not installed, another
build or release, or turned off), and `SOFTSCHEMA_PURE_YAML=1` forces the pure parser.

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
