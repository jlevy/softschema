# Golden corpus (cross-language CLI parity)

One [tryscript](https://github.com/jlevy/tryscript) corpus, run against **both**
the Python and the TypeScript softschema CLIs, proving they behave identically.

## How it works

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

## Stable vs unstable

These scenarios are fully deterministic — every command uses relative paths, so
there are **no unstable fields** and no patterns are needed. Note in particular:

- `schema_sha256` is shown **literally**. It is a deterministic fingerprint of
  the canonical schema, so both implementations must produce the same digest; a
  divergence in the canonical profile surfaces here as a changed hash.
- Implementation-specific **semantic** errors (Pydantic vs Zod, with
  version-specific URLs) are intentionally avoided: failure scenarios validate
  against the schema only (`--schema`, no `--model`), so the structural error
  records are identical across engines.

## Updating

1. Change behavior in the CLI.
2. Re-run `SOFTSCHEMA_IMPL=py ./tests/golden/run.sh` (or `npx tryscript run … --expand`).
3. Review the diff in `scenarios/` as a behavioral change.
4. Commit the scenario files alongside the code.

## Scenarios

| File | Covers |
| --- | --- |
| `validate.md` | happy path (structural + semantic ok); structural failure with engine-neutral, sorted error records |
| `compile.md` | `compile --check` no-drift (literal digest) and drift (different contract id) |
| `inspect-and-docs.md` | `inspect`; `docs --list`; `skill --brief` |
| `envelope-errors.md` | ambiguous envelope and missing validation implementation (exit 2, stderr) |

Fixtures live in `fixtures/`.
