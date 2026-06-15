# Golden Corpus (Cross-Language CLI Parity)

One [tryscript](https://github.com/jlevy/tryscript) corpus, run against **both** the
Python and the TypeScript softschema CLIs, proving they behave identically. It covers the
whole CLI surface (every command, flag, and user-error exit path), so the design changes
in later phases are refactored against a real safety net.

## How It Works

Each scenario in `scenarios/` invokes the **neutral** `softschema` command and captures
full stdout/stderr/exit-code. `run.sh` builds a shim that points `softschema` at the
chosen implementation and runs the suite:

```bash
SOFTSCHEMA_IMPL=py     ./tests/golden/run.sh   # the Python CLI (softschema-py)
SOFTSCHEMA_IMPL=ts     ./tests/golden/run.sh   # the TypeScript CLI under Node
SOFTSCHEMA_IMPL=ts-bun ./tests/golden/run.sh   # the TypeScript CLI under Bun
```

`ts` runs the built CLI under **Node**, the runtime npm users actually get via `npx
softschema`; `ts-bun` runs the same bundle under Bun. Both must produce byte-identical
output, so the published runtime is proven, not just the dev one. (Run `bun run build` in
`packages/typescript` first so `dist/cli.js` exists.)

Because the CLI emits deterministic, key-sorted JSON, engine-neutral structural error
records, and a canonical compiled JSON Schema, a single expected-output block validates
both implementations. Parity is a test pass, not a manual audit.

## Direct Cross-Implementation Diff

`cross-impl-diff.sh` runs the same neutral commands through the Python CLI and the
TypeScript CLI under Node and byte-compares stdout and exit codes directly, so a parity
break is reported as a py-vs-ts difference rather than as one side drifting from the
committed goldens:

```bash
./tests/golden/cross-impl-diff.sh
```

## Stable vs Unstable

These scenarios are deterministic: commands use relative paths. The only genuinely
variable field is the version string (`--version`), matched with a `[VERSION]` pattern.
Otherwise no patterns are needed. Note in particular:

- `schema_sha256` is shown **literally**. It is a deterministic fingerprint of the
  canonical schema, so both implementations must produce the same digest; a divergence in
  the canonical profile surfaces here as a changed hash.
- Implementation-specific **semantic** errors (Pydantic vs Zod, with version-specific
  URLs) are intentionally avoided: failure scenarios validate against the schema only
  (`--schema`, no `--model`), so the structural error records are identical across
  engines. The `validate --model` scenarios (per-impl) assert only the semantic-ok path.
- **User-error stderr is engine-specific by design.** A missing file is `[Errno 2] No
  such file or directory` on Python and `ENOENT` on Node; a malformed `softschema` block
  ends `got list` vs `got object`. Where the wording diverges, the scenario merges
  streams with `2>&1` and asserts the stable `softschema <cmd>:` prefix plus exit code,
  eliding the engine-specific tail with `[..]`/`...`. Where the wording is identical
  (ambiguous envelope, missing implementation) it is asserted in full on stderr (`!`).
- **Number formatting.** Both implementations render numbers to match Python's `repr()`.
  Numbers follow one canonical rule; one genuine edge case remains:
  - **(a) Whole-valued numbers render in canonical form** (`ss-wbnm`, resolved). A
    whole-valued number below 1e16 renders without a trailing fraction (`2.0` -> `2`) —
    the JSON-natural form JS emits natively, since it collapses the YAML token `2.0` to
    `2` at parse. The Python side normalizes its floats to match (`canonical_number` in
    `errors.py`, applied to error records and the `values` echo), so a whole-number float
    is byte-identical in a `value`, `validator_value`, or message on both engines.
    Non-whole floats (`0.3`, `8.6`) keep their fraction. The `error-normalization`
    scenario exercises this with `ratio: 1.0` failing `minimum: 2.0` (both render `1`/`2`).
  - **(b) Integer literals >= 2^53 diverge.** Python has arbitrary-precision integers
    (`repr(10000000000000000)` is `10000000000000000`), while JS collapses large integer
    literals into IEEE 754 doubles, losing precision. A YAML integer literal like
    `10000000000000000` stays `int` in Python but becomes a float in JS (same numeric
    value, different repr). Avoid integer-valued literals >= 2^53 in error-exercising
    fixtures.

## Updating

1. Change behavior in the CLI.
2. Re-run a runtime, e.g. `SOFTSCHEMA_IMPL=py ./tests/golden/run.sh`. To rewrite the
   expected blocks from the actual output, run tryscript with `--expand`:
   `bunx tryscript@0.1.7 run tests/golden/scenarios/<file>.md --expand` (with
   `SOFTSCHEMA_BIN_DIR` pointing at the shim `run.sh` builds, or via the same shell).
3. Review the diff in `scenarios/` as a behavioral change.
4. Confirm the change is byte-identical on the other runtimes (`ts`, `ts-bun`).
5. Commit the scenario files alongside the code.

## Layout

- `scenarios/`: **neutral** scenarios that run on **every** runtime (py, ts, ts-bun).
  They use only language-neutral inputs (the compiled JSON Schema via `--schema`,
  `inspect`, `docs`, `skill`, `generate`, `--version`).
- `scenarios-py/`: Python per-impl scenarios (`compile` from a Pydantic class;
  `validate --model` against a Pydantic model). Run under `py`.
- `scenarios-ts/`: TypeScript per-impl scenarios that are **Node-safe**
  (`validate --model` against a plain `.mjs` Zod model importing only `zod`). Run under
  both `ts` and `ts-bun`.
- `scenarios-ts-bun/`: TypeScript per-impl scenarios that need a TS-capable runtime
  (`compile` imports a `.ts` model module, which plain Node cannot load). Run under
  `ts-bun` only; the same Zod→canonical-schema parity is independently proven by the
  cross-language conformance unit test (`packages/typescript/test/conformance.test.ts`).
- `fixtures/`: shared input artifacts.

| File | Scope | Covers |
| --- | --- | --- |
| `scenarios/validate.md` | all | schema-only validate: structural ok; structural failure (engine-neutral, sorted records); absent designated envelope (`envelope_mismatch`, exit 1) |
| `scenarios/cli-errors.md` | all | the user-error exit paths: ambiguous envelope and missing implementation (stderr asserted), missing file, malformed frontmatter, malformed metadata, unknown docs topic (exit 2, prefix asserted) |
| `scenarios/warnings.md` | all | `document-status-mismatch` warning on a status override |
| `scenarios/inspect-and-docs.md` | all | `inspect` (movie, plain doc, no frontmatter); `docs --list`; `docs --list --json`; `docs <topic>`; `skill --brief`; `skill` |
| `scenarios/generate.md` | all | `generate --check` no-drift and drift (exit 1) |
| `scenarios/version.md` | all | `--version` (`[VERSION]` pattern) |
| `scenarios/error-normalization.md` | all | every structural error keyword, engine-neutral |
| `scenarios/frontmatter-edge-cases.md` | all | empty frontmatter (`no_frontmatter`); whitespace-only frontmatter (parse error, exit 2); unterminated fence (parse error, exit 2) |
| `scenarios-py/compile.md` | py | `compile --check` no-drift (literal digest) and drift; source is a Pydantic class |
| `scenarios-py/validate-model.md` | py | `validate --model` semantic-ok path (Pydantic) |
| `scenarios-ts/validate-model.md` | ts, ts-bun | `validate --model` semantic-ok path (Zod `.mjs`) |
| `scenarios-ts-bun/compile.md` | ts-bun | same compile output; source is a Zod module (needs a TS runtime) |

Compile parity (content-identical compiled schema, equal digest) across languages is
additionally asserted by the cross-implementation conformance test.
