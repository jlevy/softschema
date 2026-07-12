# Golden CLI Journeys

The tryscript corpus exercises the public CLI through a few broad workflows.
The same neutral scenarios run against Python, Node, and Bun; adapter-specific model
and compile scenarios live beside them.

```bash
SOFTSCHEMA_IMPL=py     ./tests/golden/run.sh
SOFTSCHEMA_IMPL=ts     ./tests/golden/run.sh
SOFTSCHEMA_IMPL=ts-bun ./tests/golden/run.sh
```

Build the TypeScript package before running the Node or Bun variants:

```bash
bun run --cwd packages/typescript build
```

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
| `validate.md` | structural success/failure, envelope failure, metadata-only validation |
| `metadata-binding.md` | document schema/envelope bindings, precedence, and bounded paths |
| `enforced-status.md` | permissive and enforced extra-field behavior |
| `cli-errors.md` | usage/input failures, diagnostics, and exit `2` |
| `generate.md` | generated-section drift and malformed markers |
| `inspect-and-docs.md` | inspection and bundled docs/skill discovery |

Adapter journeys are:

| File | Runtime | Responsibility |
| --- | --- | --- |
| `scenarios-py/compile.md` | Python | Pydantic compile and drift |
| `scenarios-py/validate-model.md` | Python | Pydantic semantic validation |
| `scenarios-ts/validate-model.md` | Node and Bun | Zod semantic validation |
| `scenarios-ts-bun/compile.md` | Bun | TypeScript Zod compile and drift |

`cross-impl-diff.sh` runs representative commands through Python and Node directly.
It structurally normalizes JSON before comparison and compares non-JSON output exactly.

## Updating

1. Change the behavior and its narrow primary test.
2. Run all three golden variants.
3. If the public CLI behavior intentionally changed, update the affected tryscript
   transcript with `bunx tryscript@0.1.7 run <scenario> --expand`.
4. Review the transcript diff as a public behavior change.
5. Run `cross-impl-diff.sh` and commit the reviewed transcript with the code.

Keep journeys broad and few. Do not add a golden for behavior already owned by the
shared vectors or an adapter unit test.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
