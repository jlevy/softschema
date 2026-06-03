# Golden Corpus (Cross-Language CLI Parity)

One [tryscript](https://github.com/jlevy/tryscript) corpus, run against **both**
the Python and the TypeScript softschema CLIs, proving they behave identically.

## How It Works

Each scenario in `scenarios/` invokes the **neutral** `softschema` command and
captures full stdout/stderr/exit-code. `run.sh` builds a shim that points
`softschema` at the chosen implementation and runs the suite:

```bash
SOFTSCHEMA_IMPL=py ./tests/golden/run.sh   # the Python CLI (softschema-py)
SOFTSCHEMA_IMPL=ts ./tests/golden/run.sh   # the TypeScript CLI (softschema-ts), once built
```

Because the CLI emits deterministic, key-sorted JSON, engine-neutral structural
error records, and a canonical JSON Schema sidecar, a single expected-output
block validates both implementations. Parity is a test pass, not a manual audit.

## Stable vs Unstable

These scenarios are fully deterministic: every command uses relative paths, so
there are **no unstable fields** and no patterns are needed. Note in particular:

- `schema_sha256` is shown **literally**. It is a deterministic fingerprint of
  the canonical schema, so both implementations must produce the same digest; a
  divergence in the canonical profile surfaces here as a changed hash.
- Implementation-specific **semantic** errors (Pydantic vs Zod, with
  version-specific URLs) are intentionally avoided: failure scenarios validate
  against the schema only (`--schema`, no `--model`), so the structural error
  records are identical across engines.
- **Whole-number floats are avoided in error cases** (e.g. `2.0`, `10.0`). Python
  preserves the int/float distinction from the YAML source token (`repr(2.0) ==
  "2.0"`); JS collapses `2.0` to `2` at parse, so a whole-number float renders as
  `2` on the TypeScript side. This is the one documented parity limitation
  (`ss-wbnm`); keep golden values that appear in a `value`, `validator_value`, or
  message as integers or **non-whole** floats (`0.3`, `8.6`) so the corpus stays
  byte-identical on both engines. Non-error values elsewhere are unaffected.

## Updating

1. Change behavior in the CLI.
2. Re-run `SOFTSCHEMA_IMPL=py ./tests/golden/run.sh` (or `npx tryscript run … --expand`).
3. Review the diff in `scenarios/` as a behavioral change.
4. Commit the scenario files alongside the code.

## Layout

- `scenarios/`: **neutral** scenarios that run on **both** implementations. They use
  only language-neutral inputs (the JSON Schema sidecar via `--schema`, `inspect`,
  `docs`, `skill`). The semantic layer (`--model`: Pydantic vs Zod) and `compile` (whose
  source is a Pydantic class vs a Zod module) are language-specific and are **not** here.
- `scenarios-py/` and `scenarios-ts/`: per-implementation scenarios whose *invocation*
  differs by language even though the *output* is identical (e.g. `compile`). `run.sh`
  runs `scenarios/` plus `scenarios-$IMPL/`.
- `fixtures/`: shared input artifacts.

| File | Scope | Covers |
| --- | --- | --- |
| `scenarios/validate.md` | both | schema-only validate: structural ok; structural failure with engine-neutral, sorted error records |
| `scenarios/inspect-and-docs.md` | both | `inspect`; `docs --list`; `skill --brief` |
| `scenarios/envelope-errors.md` | both | ambiguous envelope and missing validation implementation (exit 2, stderr) |
| `scenarios-py/compile.md` | py | `compile --check` no-drift (literal digest) and drift; source is a Pydantic class |
| `scenarios-ts/compile.md` | ts | same output; source is a Zod module |

Compile parity (byte-identical sidecar, equal digest) across languages is additionally
asserted by the cross-implementation conformance test.
