# Development

First-time setup of `uv` and Python is covered in [Installation](installation.md).
Release workflow and PyPI steps are covered in
[Publishing](https://github.com/jlevy/softschema/blob/main/docs/publishing.md).
The full validation pass — the automated sweep run locally plus the manual
clean-environment checks CI cannot run — is codified in the
[end-to-end testing runbook](e2e-testing.runbook.md).

Set up the repo (Python deps, Node tooling for hooks, and the git hooks themselves):

```bash
make install        # uv sync --all-extras + npm install (lefthook)
make hooks-install  # install the lefthook pre-commit hooks
```

`make install` alone (or `uv sync --all-extras`) is enough to run tests and builds;
`make hooks-install` additionally wires up the pre-commit hooks described below.

Common workflows:

```bash
make lint
make lint-check
make test
make build
```

Direct commands:

```bash
uv run python devtools/lint.py --check
uv run pytest
uv run softschema docs --list
uv run softschema docs --list --json
uv run softschema skill --brief
uv build
```

The Python package is built from `packages/python/src/softschema`.

### Git hooks (this repo)

Hooks are managed by [lefthook](https://lefthook.dev) (`lefthook.yml`), installed with
`make hooks-install`. The `pre-commit` hook formats staged changes so commits stay
clean:

- **Markdown:** delegates to `make format` (pinned `flowmark-rs` and
  `softschema generate`); the single source of truth, the same command you run locally.
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
one version number**; see
[Publishing](https://github.com/jlevy/softschema/blob/main/docs/publishing.md).

Documentation changes should follow `common-doc-guidelines.md`
(github.com/jlevy/practical-prose).
Keep the README short, keep conceptual guidance in `docs/softschema-guide.md`, and keep
exact format rules in `docs/softschema-spec.md`.

## Continuous Integration

Two softschema checks belong in CI for any project that depends on the package.

### Compiled schema drift

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

### Generated-section drift

If any Markdown file contains `softschema:generated` markers (see the guide’s “Keep
Schema Tables In Sync With Generated Sections” playbook), run the re-renderer in
`--check` mode so CI fails when the committed section lags behind the schema:

```bash
uv run softschema generate examples/movie_page/README.md --check
```

Fix on drift: re-run without `--check` and commit the regenerated section.

### Artifact validation

Run `softschema validate` against every artifact under version control whose contract is
fully defined:

```bash
uv run softschema validate examples/movie_page/spirited-away.md \
  --model examples.movie_page.model:MoviePage \
  --schema examples/movie_page/movie-page.schema.yaml
```

`validate` reads `softschema.contract`, `softschema.status`, and the single top-level
envelope key from the artifact by default.
`--contract`, `--status`, and `--envelope` are override flags.

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
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v8
      - run: uv sync --all-extras
      - name: Compiled schema drift check
        run: |
          uv run softschema compile examples.movie_page.model:MoviePage \
            --contract example.movies:MoviePage/v1 \
            --out examples/movie_page/movie-page.schema.yaml --check
      - name: Validate example artifact
        run: |
          uv run softschema validate examples/movie_page/spirited-away.md \
            --model examples.movie_page.model:MoviePage \
            --schema examples/movie_page/movie-page.schema.yaml
```

### Pre-commit hook

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

softschema ships two implementations, Python/Pydantic (`softschema`) and TypeScript/Zod
(`softschema`, `softschema-ts`), held to **exact behavioral parity**: equivalent CLI
inputs/outputs/flags and library APIs, the same canonical compiled JSON Schema
(content-identical, equal `schema_sha256`), and the same engine-neutral validation
results. Only idiomatic surface differs (snake_case ↔ camelCase, Pydantic ↔ Zod).

When you change any behavior, follow this loop so the two never drift:

1. **Golden first.** Write or update the shared scenario in `tests/golden/scenarios/`
   (neutral, runs on both) or `tests/golden/scenarios-{py,ts}/` (per-language
   invocation, identical output) **before** touching code.
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
| Bundled docs/skill resolve from the package | the standalone test (`packages/typescript/test/standalone.test.ts`) |
| Skill mirrors never go stale | the mirror drift test (`tests/test_skill_mirror_drift.py`) |

Semantic invariants that JSON Schema cannot express (Pydantic validators ↔ Zod
refinements) are implementation-specific by design and tested per-language, not in the
shared corpus.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
