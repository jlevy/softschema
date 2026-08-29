# Golden CLI Journeys

The tryscript corpus exercises the public CLI through a few broad workflows.
The same neutral scenarios run against Python, Node, and Bun; adapter-specific model
and compile scenarios live beside them.

```bash
SOFTSCHEMA_IMPL=py     ./tests/golden/run_golden_tests.py
SOFTSCHEMA_IMPL=ts     ./tests/golden/run_golden_tests.py
SOFTSCHEMA_IMPL=ts-bun ./tests/golden/run_golden_tests.py
```

Build the TypeScript package before running the Node or Bun variants:

```bash
bun run --cwd packages/typescript build
```

## Naming

Scenario files are `*.tryscript.md`, which is tryscript's own default glob. Fixtures under
`fixtures/` are plain `.md` and are never scenarios.

The suffix is not decoration. `run_golden_tests.py` globs `*.tryscript.md`, so a stray
`README.md` dropped into a scenario directory is not fed to tryscript as a test, and a bare
`tryscript run` in this repo finds the corpus instead of matching nothing. The runner also
asserts the neutral set and the per-impl set are each non-empty: tryscript fails a run that
matches *no* files, but it is handed one combined list and cannot know that
`scenarios-ts/` was meant to contribute, so a bad rename there would otherwise leave the
neutral set reporting a healthy green.

## Selecting the implementation

Scenarios invoke `$SOFTSCHEMA`, and `run_golden_tests.py` sets it — to
`.venv/bin/softschema-py`, `node …/dist/cli.js`, or `bun …/dist/cli.js`. That one variable
is the whole switching mechanism: one corpus, three runtimes, nothing generated. Both CLIs
hardcode their program name, so the diagnostics and usage text in these transcripts are the
same whichever build produced them.

## Ownership

Goldens own complete CLI commands, stdout/stderr behavior, side effects, and exit
classes. Shared YAML vectors own library rules and edge cases. Adapter unit tests own
language-specific model loading and filesystem boundaries.

Machine-readable JSON is compared structurally across runtimes. Human-readable output,
stable diagnostics, exit codes, and compiled-schema digests are compared exactly.
Implementation-specific model errors and operating-system file errors are asserted only
to their stable boundary.

The neutral journeys are:

| File | Responsibility |
| --- | --- |
| `validate.tryscript.md` | structural success/failure, envelope failure, metadata-only validation |
| `validate-repair.tryscript.md` | `--repair` / `--check-repair`: what is fixed, what is refused, and the resulting file |
| `metadata-binding.tryscript.md` | document schema/envelope bindings, precedence, and bounded paths |
| `enforced-status.tryscript.md` | permissive and enforced extra-field behavior |
| `cli-errors.tryscript.md` | usage/input failures, diagnostics, and exit `2` |
| `generate.tryscript.md` | generated-section drift and malformed markers |
| `inspect-and-docs.tryscript.md` | inspection and bundled docs/skill discovery |

Adapter journeys are:

| File | Runtime | Responsibility |
| --- | --- | --- |
| `scenarios-py/compile.tryscript.md` | Python | Pydantic compile and drift |
| `scenarios-py/validate-model.tryscript.md` | Python | Pydantic semantic validation |
| `scenarios-ts/validate-model.tryscript.md` | Node and Bun | Zod semantic validation |
| `scenarios-ts-bun/compile.tryscript.md` | Bun | TypeScript Zod compile and drift |

`cross-impl-diff.sh` runs representative commands through Python and Node directly.
It structurally normalizes JSON before comparison and compares non-JSON output exactly.

## Mutating scenarios

`validate-repair.tryscript.md` is the one journey file whose commands **rewrite their
input**. Four rules follow, and a new mutating scenario has to keep all of them:

- Set `sandbox: true` and declare the starting layout in `fixtures:`. Pointing a mutating
  command at a checked-in fixture passes once and then fails on a dirty tree; the sandbox
  gives the file a fresh temporary directory, so the source tree is never written to.
- Give each journey its own directory under that sandbox, and copy the fixtures it needs
  into it. The sandbox is per *file*, not per command, so journeys starting from the same
  fixture would otherwise inherit each other's writes. Keep a copy under `original/` for
  the journeys that must prove a file was left alone.
- Pin the **complete JSON result**, its `path` field included, rather than grepping
  fragments out of it; the short sandbox-relative paths are what make that practical.
  Broad state over surgical checks: a grep pins one field and lets a regression in any
  other slip through green, which is how a failure-path bug once survived this corpus.
- Print the file afterward. The write is the deliverable, so a transcript showing only the
  JSON verdict has not covered it, and having the bytes in the transcript is what surfaces
  an emitter that starts restyling what it was asked to fix.

## Updating

1. Change the behavior and its narrow primary test.
2. Run all three golden variants.
3. If the public CLI behavior intentionally changed, update the affected tryscript
   transcript with `bunx tryscript@0.2.1 run <scenario> --update`.
4. Review the transcript diff as a public behavior change.
5. Run `cross-impl-diff.sh` and commit the reviewed transcript with the code.

Keep journeys broad and few. Do not add a golden for behavior already owned by the
shared vectors or an adapter unit test.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
