---
name: e2e-testing
description: >-
  The codified end-to-end validation path for softschema: the full automated
  sweep run locally (mirroring CI), plus the manual-only checks CI cannot run —
  clean-environment installs of the built wheel and npm tarball, the
  docs-as-written quickstart from an empty directory, the agent skill
  bootstrap, and post-publish registry smoke tests. Use before tagging a
  release, after toolchain or packaging changes, or whenever the published
  artifacts must be proven rather than just the repo.
---
# End-to-End Testing Runbook

CI proves the repository; this runbook proves the **product**: the packaged artifacts a
user actually installs, the docs they actually follow, and the registries they actually
fetch from. It is the codified manual path for everything not already covered by
automated testing, plus the order in which to run the automated sweep locally so the
whole system is validated in one pass.
Every command below has been run end to end and works as written.

Run the full runbook before tagging a release.
Run Phases 1–4 after any change to packaging (`pyproject.toml`, `package.json`, bundled
resources), the CLI surface, or the docs quickstarts.

## What CI Already Covers

The automated half of the story runs on every push and PR
([`ci.yml`](../.github/workflows/ci.yml)), so the manual effort goes to the gaps:

| Check | Where automated |
| --- | --- |
| codespell, ruff, basedpyright, doc footers | `build` job (`devtools/lint.py --check`) |
| Python unit tests (pytest, 3.11–3.14) | `build` job |
| Python build (`uv build`) | `build` job |
| TS typecheck, biome, unit tests + coverage gate | `typescript` job |
| TS build + publint (publishable layout) | `typescript` job |
| Golden corpus on py, ts (Node), ts-bun | `golden` + `typescript` jobs |
| Python-vs-TypeScript byte parity | `cross-impl` job |
| Tag ↔ `package.json` version match | `publish.yml` guard |

**Not** covered by CI—the reason this runbook exists:

- Installing the built wheel and npm tarball into clean environments and running them
  (entry points, bin shebang, bundled docs/skill resources).
- The README quickstart exactly as written, from an empty directory.
- The agent skill bootstrap (`skill --install`) into a scratch repo.
- The published registries after a release (PyPI and npm smoke tests).
- Markdown formatting drift (`make format-check` runs in the pre-commit hook, not in
  CI).

## Phase 1: Full Automated Sweep, Locally

Mirror CI from the repo root, in this order (later phases depend on the builds):

```bash
make install        # uv sync + npm install (lefthook) + bun install
make lint-check     # codespell, ruff, basedpyright, doc footers
uv run pytest       # Python unit tests
uv build            # wheel + sdist into dist/ (used by Phase 2)

cd packages/typescript
bun run check       # biome + tsc + bun test with coverage gate
bun run build       # copy-resources + bunup → dist/ (required by the ts golden runs)
bun run publint
cd ../..

SOFTSCHEMA_IMPL=py     bash tests/golden/run.sh
SOFTSCHEMA_IMPL=ts     bash tests/golden/run.sh   # 44
SOFTSCHEMA_IMPL=ts-bun bash tests/golden/run.sh   # 46
bash tests/golden/cross-impl-diff.sh              # "cross-impl parity OK"

make format-check   # flowmark drift; requires a Markdown-clean working tree
```

Success is every command exiting 0. The test and scenario counts are reference floors
that grow over time; a *drop* is the signal to investigate (a per-impl scenario
directory silently vanishing, a skipped suite).
The corpus layout and update procedure are in
[tests/golden/README.md](../tests/golden/README.md); the parity invariants are in
[development.md](development.md).

## Phase 2: Clean-Environment Install Smoke Tests

Unit tests and goldens exercise the source tree.
This phase proves the **packaged artifacts** from a real install with no repo on disk:
the console entry points resolve, the bin shebang runs under plain Node, and the bundled
docs/skill resources load from inside the installed package.

### Python Wheel in a Fresh Venv

```bash
uv build
tmp=$(mktemp -d)
uv venv "$tmp/venv"
uv pip install --python "$tmp/venv/bin/python" dist/softschema-*.whl
"$tmp/venv/bin/softschema" --help
"$tmp/venv/bin/softschema" docs --list
"$tmp/venv/bin/softschema" skill --brief
cd "$tmp"
venv/bin/softschema docs example-artifact > spirited-away.md
venv/bin/softschema docs example-schema   > movie-page.schema.yaml
venv/bin/softschema validate spirited-away.md   # exit 0, structural ok, zero flags
cd - && rm -rf "$tmp"
```

### npm Tarball under Plain Node

`npm pack` runs `prepublishOnly` (build and publint), so the tarball is freshly rebuilt
from source—the same artifact `npm publish` would upload.
Run it under `node` (>= 22.12), the runtime npm users get, not under bun:

```bash
cd packages/typescript
tgz=$(npm pack | tail -1); abs="$PWD/$tgz"
tmp=$(mktemp -d)
cd "$tmp" && npm init -y && npm install "$abs"
node ./node_modules/softschema/dist/cli.js --help   # or: ./node_modules/.bin/softschema --help
node ./node_modules/softschema/dist/cli.js docs example-artifact > spirited-away.md
node ./node_modules/softschema/dist/cli.js docs example-schema   > movie-page.schema.yaml
node ./node_modules/softschema/dist/cli.js validate spirited-away.md   # exit 0
cd - && rm -rf "$tmp" "$abs"
```

If a local supply-chain cool-off blocks the `npm install` of dependencies, add
`--before=2030-01-01` to that install; it affects only this smoke test, never a publish
(see [publishing-npm.md](publishing-npm.md)).

## Phase 3: The Quickstart, As Written

The README Quick Start is the contract with a first-time user; run it verbatim from an
**empty directory** on both implementations.
Before a release, substitute the local builds for the exact zero-install version shown
in the README (the published forms are verified in Phase 5):

```bash
repo=$(pwd)   # the softschema checkout
cd "$(mktemp -d)"

# Python implementation
"$repo/.venv/bin/softschema-py" docs example-artifact > spirited-away.md
"$repo/.venv/bin/softschema-py" docs example-schema   > movie-page.schema.yaml
"$repo/.venv/bin/softschema-py" validate spirited-away.md   # exit 0, zero flags

# TypeScript implementation, same commands
node "$repo/packages/typescript/dist/cli.js" docs example-artifact > ts-artifact.md
node "$repo/packages/typescript/dist/cli.js" docs example-schema   > ts-schema.yaml
node "$repo/packages/typescript/dist/cli.js" validate ts-artifact.md   # exit 0

diff spirited-away.md ts-artifact.md          # byte-identical
diff movie-page.schema.yaml ts-schema.yaml    # byte-identical
```

One trap to know about: the artifact names its own schema
(`schema: movie-page.schema.yaml`), so the schema **must** be saved under that exact
filename next to the artifact.
Redirecting it anywhere else makes `validate` fail with `schema_missing`—correct
resolution behavior, broken quickstart.
If the README quickstart ever changes, re-verify the new text the same way before
merging it.

## Phase 4: Agent Skill Bootstrap

The installation docs tell agents to run `--help` and follow the instructions to
`skill --install`. Prove that path in a scratch repo, using any of the installed CLIs
from Phase 2 or 3:

```bash
cd "$(mktemp -d)" && git init -q .
softschema skill --install --scope project --agent portable --agent claude
ls .agents/skills/softschema/SKILL.md .claude/skills/softschema/SKILL.md
```

Expect a JSON report listing both `SKILL.md` mirrors as `created`, and both files
present on disk.

## Phase 5: Post-Publish Registry Verification (Per Release)

The tagging and release mechanics live in [publishing.md](publishing.md); this phase is
what to run **after** `publish.yml` reports success for both registries.

A just-published version sits inside the 14-day supply-chain cool-off, so the Python
smoke test must override the cutoff.
Three details make the difference between a real check and a false “no version” failure:

- **Override the cutoff to *now*, not midnight.** `--exclude-newer-package` excludes
  releases newer than the given instant.
  A date-only value (`$(date +%F)`) is midnight UTC, which is *before* a version
  published later the same day—so it excludes the very release you are verifying.
  Use a full timestamp at the current moment (`$(date -u +%Y-%m-%dT%H:%M:%SZ)`); “now”
  is always after the publish.
- **Run from outside the repo.** From the project tree, uv reads its `[tool.uv]`
  settings and applies the project’s own cool-off; a neutral directory (`cd /tmp`)
  avoids that.
- **`--refresh`** bypasses uv’s cached package index, which may not yet list a release
  published seconds ago.

```bash
cd /tmp
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
uvx --refresh --exclude-newer-package "softschema=$ts" softschema@X.Y.Z --version
npx -y softschema@X.Y.Z --version
```

Then run the quickstart literally against the published artifacts:

```bash
cd "$(mktemp -d)"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
uvx() { command uvx --refresh --exclude-newer-package "softschema=$ts" "$@"; }
uvx softschema@X.Y.Z docs example-artifact > spirited-away.md
uvx softschema@X.Y.Z docs example-schema   > movie-page.schema.yaml
uvx softschema@X.Y.Z validate spirited-away.md
```

After verification, update the exact last-verified version used by the README, bundled
skill, CLI help, and installation guide in the release-preparation PR.

## Recording Results

For a release-sized change, record the sweep outcome (test and golden counts, parity
status, and which manual phases were run) in the release’s review doc under
`docs/project/reviews/`, so the next release has a known-good baseline to compare
against.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
