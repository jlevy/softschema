# Development

First-time setup of `uv` and Python is covered in [Installation](installation.md).
Release workflow and PyPI steps are covered in [Publishing](publishing.md).
The full validation pass—the automated sweep and artifact smoke rerun locally plus the
manual docs and registry checks CI cannot run—is codified in the
[end-to-end testing runbook](e2e-testing.runbook.md).

Set up the repo (Python deps, Node tooling for hooks, and the git hooks themselves):

```bash
make install        # uv sync --all-extras + npm install (lefthook)
make hooks-install  # install the lefthook pre-commit hooks
```

`make install` performs the reviewed two-step Python install: it syncs locked
dependencies without building the project, then installs the editable package with the
already installed, pinned build backend.
`make hooks-install` additionally wires up the pre-commit hooks described below.

CI uses a stricter wheel-first boundary.
The build job first creates the local wheel with hash-locked build dependencies.
It then runs the following boundary in a fresh package cache:

1. `UV_NO_BUILD=1 uv sync --frozen --no-cache --no-install-project ...` installs only
   locked third-party wheels and fails if any dependency requires an sdist build.
2. `UV_NO_BUILD=1 uv pip install --no-build --no-deps <local-wheel>` installs the
   already built project wheel.
3. `verify_installed_wheel.py` checks its `direct_url.json`, active-environment import
   path, and every file digest and size in the wheel’s `RECORD` before tests run with
   `uv run --no-sync`.

The no-cache requirement matters: uv may reuse a locally cached wheel under
`--no-build`, which would hide a source-only dependency on a warm runner.
The release preflight scopes the same no-build/no-cache rule to third-party dependency
sync, then uses the reviewed checkout for its pre-identity test install; the exact
release wheel is built only after build metadata exists and is verified again in the
candidate smoke job.

The skill validator is an exact `skills-ref==0.1.1` wheel dependency.
Its validator source matches agentskills commit
`38a2ff82958afee88dadf4831509e6f7e9d8ef4e` (reviewed 2026-07-09); the published wheel
adds explicit UTF-8 reads and the corrected package version.
`uv.lock` records its wheel URL, size, upload time, and SHA-256 digest, so CI does not
execute a Git dependency’s build backend.

Common workflows:

```bash
make lint
make lint-check
make test
make build
```

Direct commands:

```bash
uv sync --all-extras --no-install-project
uv pip install --no-build-isolation --no-deps --editable .
uv run python devtools/lint.py --check
uv run pytest
uv run softschema docs --list
uv run softschema docs --list --json
uv run softschema skill --brief
uv build --build-constraint build-constraints.txt --require-hashes
uv run python conformance/run.py --check-only
uv run python devtools/public_claims.py --check
uv run python devtools/sync_agent_instructions.py --check
```

The Python package is built from `packages/python/src/softschema`.

### Git Hooks (This Repo)

Hooks are managed by [lefthook](https://lefthook.dev) (`lefthook.yml`), installed with
`make hooks-install`. The `pre-commit` hook formats staged changes so commits stay
clean:

- **Markdown:** delegates to `make format` (pinned `flowmark-rs`, generated sections,
  skill mirrors, and native agent adapters); the single source of truth, the same
  command you run locally.
- **Python:** `ruff format` and `ruff check --fix` on staged `*.py`.
- **TypeScript:** `biome check --write` on staged files in `packages/typescript`.

Bypass for an emergency commit with `git commit --no-verify` (avoid in PRs).
flowmark runs across the whole tree (it honors `.flowmarkignore` only relative to its
target arg), so staging any `*.md` reformats all Markdown; this is fast and idempotent.

## TypeScript Package

The TypeScript/Zod package lives in `packages/typescript` and builds with bun (bunup and
biome). Set it up and run its checks:

```bash
cd packages/typescript
bun install --frozen-lockfile
bun run check       # biome lint, tsc --noEmit, bun test (+ coverage gate)
bun run build       # copy-resources + bunup → dist/
bun run publint     # lint the publishable package layout (run after build)
```

It publishes to npm as `softschema` (the same name as the PyPI package) and exposes the
CLI as both `softschema` and `softschema-ts`. The two packages **release together under
one version number**; see [Publishing](publishing.md).

Documentation changes should follow `common-doc-guidelines.md`
(github.com/jlevy/practical-prose).
Keep the README short, adoption guidance in `docs/softschema-guide.md`, exact behavior
in `docs/softschema-spec.md`, public integration in `docs/api.md`, runtime internals in
the two design references, and compatibility history in `docs/migration-0.3.md` and
`CHANGELOG.md`.

## Continuous Integration

Two softschema checks belong in CI for any project that depends on the package.

### Compiled Schema Drift

A committed `.schema.yaml` file is *generated, but committed*. Run
`softschema compile ... --check` to fail the build when the committed compiled schema
drifts from the source model:

```bash
uv run softschema compile examples.movie_page.model:MoviePage \
  --contract example.movies:MoviePage/v1 \
  --out examples/movie_page/movie-page.schema.yaml --check
```

Fix on drift: re-run the same command without `--check` and commit the regenerated
compiled schema.

### Generated-Section Drift

If any Markdown file contains `softschema:generated` markers (see the guide’s “Keep
Schema Tables in Sync with Generated Sections” playbook), run the re-renderer in
`--check` mode so CI fails when the committed section lags behind the schema:

```bash
uv run softschema generate examples/movie_page/README.md --check
```

Fix on drift: re-run without `--check` and commit the regenerated section.

### Artifact Validation

Run one deterministic batch against every artifact under version control whose contract
is fully defined:

```bash
uv run softschema validate examples/movie_page/spirited-away.md
uv run softschema validate docs/artifacts --recursive --profile frontmatter-md
```

The public movie artifact declares its contract, schema, envelope, and status.
Override flags remain available for a host-owned binding.
A directory or multi-path request uses diagnostic-v1 and returns exit 2 for any input
error, otherwise 1 for any readable failure, otherwise 0.

### GitHub Actions

A minimal job that runs both checks:

```yaml
name: softschema

on:
  pull_request:
  push:
    branches: [main]

jobs:
  softschema:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      - uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
      - run: |
          uv sync --all-extras --no-install-project
          uv pip install --no-build-isolation --no-deps --editable .
      - name: Compiled schema drift check
        run: |
          uv run softschema compile examples.movie_page.model:MoviePage \
            --contract example.movies:MoviePage/v1 \
            --out examples/movie_page/movie-page.schema.yaml --check
      - name: Validate example artifact
        run: uv run softschema validate examples/movie_page/spirited-away.md
```

### Pre-Commit Hook

For local runs before push, a `pre-commit` config that calls the same drift check:

```yaml
repos:
  - repo: local
    hooks:
      - id: softschema-compiled-schema-drift
        name: softschema compiled schema drift
        language: system
        entry: uv run softschema compile examples.movie_page.model:MoviePage --contract example.movies:MoviePage/v1 --out examples/movie_page/movie-page.schema.yaml --check
        pass_filenames: false
        files: ^(examples/movie_page/model\.py|examples/movie_page/movie-page\.schema\.yaml)$
```

Adapt the paths and the `--model` / `--contract` / `--out` arguments to each schema in
your repository.

## Keeping Python and TypeScript in Parity

Use the smallest test layer that proves a behavior:

- **Unit and integration tests** cover edge cases, failure boundaries, and internal
  invariants that cannot be observed through the CLI.
- **Golden tests** cover a small set of complete CLI flows.
  Do not repeat every vector combination or snapshot whole bundled documents when a
  resource-integrity test already protects those bytes.
- **Conformance cases and vectors** define portable behavior for Python, Node, Bun, and
  third-party implementations.
- **Artifact smokes** prove installed wheels and npm packages, not source behavior that
  lower layers already cover.

Give each behavior one primary home.
Repeat it at another layer only when that layer proves a distinct boundary, such as
installed-resource lookup or byte-exact CLI output.
Human-reviewed expectations and vectors use YAML. Keep JSON for JSON Schemas, literal
JSON wire behavior, vendored JSON standards, and generated integrity metadata.

softschema ships two implementations, Python/Pydantic (`softschema`) and TypeScript/Zod
(`softschema`, `softschema-ts`), held to **shared contract parity**: equivalent CLI
inputs, outputs, and flags; the same canonical compiled JSON Schema (content-identical,
equal `schema_sha256`); and the same engine-neutral validation results.
Library APIs are idiomatic host-language surfaces over those shared semantics, not
method-for-method translations (Pydantic ↔ Zod, snake_case ↔ camelCase, and
runtime-specific adapters).

When you change any behavior, follow this loop so the two never drift:

1. **Shared contract first.** Update an existing golden scenario when a complete CLI
   flow changes. Use a conformance case or shared YAML vector for combinatorial portable
   semantics, and a focused unit test for behavior that is not externally observable.
   Add a new golden scenario only when no existing end-to-end flow can expose the
   behavior clearly.
2. **Implement in Python**, then `uv run pytest` and
   `SOFTSCHEMA_IMPL=py bash tests/golden/run.sh`.
3. **Port to TypeScript**, then `bun test` (in `packages/typescript`) and
   `SOFTSCHEMA_IMPL=ts bash tests/golden/run.sh`.
4. **Both green and conformance.** Both golden runs and the cross-implementation
   conformance test (the Zod and Pydantic compilers produce an identical canonical
   compiled schema) pass in CI.

The parity invariants, and where each is enforced:

| Invariant | Enforced by |
| --- | --- |
| Canonical schema (equal `schema_sha256`) | `compile` and the KitchenSink conformance test (`packages/typescript/test/conformance.test.ts`) and `examples/parity/` |
| Engine-neutral structural errors | shared message templates (`errors`), the golden corpus |
| Byte-identical neutral CLI output | the shared golden corpus (run twice via `SOFTSCHEMA_IMPL`) |
| Equal flag/command surface | per-impl and neutral golden scenarios |
| Bundled docs/skill resolve from the package | package artifact smokes and doc-topic tests |
| Skill mirrors never go stale | `packages/python/tests/test_skill_mirror_drift.py` and bootstrap tests |
| Public claims and native instruction adapters stay current | `devtools/public_claims.py`, `devtools/sync_agent_instructions.py` |
| Paired public Pydantic/Zod model remains equal | `packages/typescript/test/movie-page-example.test.ts` |

Semantic invariants that JSON Schema cannot express (Pydantic validators ↔ Zod
refinements) are implementation-specific by design and tested per-language, not in the
shared corpus.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
