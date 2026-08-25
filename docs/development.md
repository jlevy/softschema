# Development

First-time setup of `uv` and Python is covered in [Installation](installation.md).
Release workflow and PyPI steps are covered in [Publishing](publishing.md).
The full validation pass—the automated sweep run locally plus the manual
clean-environment checks CI cannot run—is codified in the
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

### Git Hooks (This Repo)

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

**Format Markdown with `make format`, never by calling flowmark yourself.** The target
is three steps, and flowmark is only the first: it also regenerates the
`softschema:generated` sections and reinstalls the skill mirrors.
A bare `flowmark-rs --auto .` reflows the generated block in
`examples/movie_page/README.md` without regenerating it, which fails
`test_movie_example_marker_is_in_sync_with_committed_schema` — a confusing failure to
land in, because the file it names is one you never meant to edit.

Remote Claude Code sessions install the hooks automatically:
`.claude/scripts/ensure-dev-env.sh` runs `make hooks-install` on SessionStart, so an
agent working in a fresh container gets the same pre-commit contract a developer has.
Without it the hook directory is empty and the formatting rules are advisory at best.

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
Keep the README short, keep conceptual guidance in `docs/softschema-guide.md`, and keep
exact format rules in `docs/softschema-spec.md`.

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

softschema ships two implementations, Python/Pydantic (`softschema`) and TypeScript/Zod
(`softschema`, `softschema-ts`), with the same commands, exit classes, structured result
meaning, canonical compiled JSON Schema, and `schema_sha256`. Only idiomatic surface
details differ (snake_case ↔ camelCase, Pydantic ↔ Zod), and cross-runtime JSON output
is compared structurally rather than as presentation bytes.

When you change any behavior, follow this loop so the two never drift:

1. **Choose one primary owner first.** Use a shared YAML vector for a portable library
   rule, especially raw-versus-enforced schema semantics; an adapter unit test for
   runtime-specific integration; or a golden journey for public CLI output and exit
   behavior. Do not add the same case at every layer.
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
| Equal checked-profile verdicts | shared semantic vectors in `tests/vectors/hardening.yaml`, including root/resource and raw/enforced pairs |
| Engine-neutral structural error meaning | shared message templates (`errors`), shared vectors, and the golden corpus |
| Structurally equal JSON and exact stable human output | the shared golden corpus (run twice via `SOFTSCHEMA_IMPL`) |
| Equal flag/command surface | per-impl and neutral golden scenarios |
| Bundled docs/skill resolve from the package | the standalone test (`packages/typescript/test/standalone.test.ts`) |
| Skill mirrors never go stale | the mirror drift test (`tests/test_skill_mirror_drift.py`) |

Semantic invariants that JSON Schema cannot express (Pydantic validators ↔ Zod
refinements) are implementation-specific by design and tested per-language, not in the
shared corpus.

### Documented deviations

Across the golden corpus and ordinary shared vectors, cross-implementation output is
identical. A native-engine record-set deviation is allowed only when it is explicitly
checked in as a documented vector.
**The Python goldens are the reference output.**

The verdict invariant applies to every schema admitted by the checked enforced profile.
Exact diagnostic-record parity is scoped to what the corpus and vectors cover:
`jsonschema` and Ajv can diverge on record *sets*, and finding an unlisted difference is
a reason to characterize and resolve it before expanding the profile.

The exception exists because `jsonschema` and `ajv` sometimes reach the same verdict
through a different number of records, and normalizing the difference away would cost
real information. Two cases ship today, both in the `engine_deviations` section of
`tests/vectors/hardening.yaml`: `dependentSchemas` (ajv adds a closure record for a
property that top-level `properties` already evaluated) and `anyOf` multiplicity (ajv
reports each branch’s failure alongside the `anyOf`).

The mechanism is deliberately not a tolerance.
Each runtime asserts *its own* listed record set exactly, so:

- a listed deviation passes;
- drift on either side fails, including drift that makes the engines agree;
- an unlisted divergence has nothing to pass against, and fails.

Add an entry only after establishing that no normalization removes the difference
cleanly, and say why in the entry’s `why` field.
Prefer normalizing in `errors.ts` — `collapseUndeclaredProperties` and
`dropConditionalWrappers` are both cases where that was the right answer.

For an enforced-profile change, add a semantic vector before changing the transformer.
Each supported shape should prove that the overlay never makes a raw-invalid instance
valid, preserves a raw-valid instance containing only evaluated properties, and rejects
the same instance after one unmatched property is added.
Test equivalent inline, pointer, anchor, and supplied-resource forms when the feature
involves references.
Transform-shape assertions are secondary implementation tests; they are not sufficient
evidence that annotation flow or branch selection was preserved.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
