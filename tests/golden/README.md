# Golden Corpus (Cross-Language CLI Parity)

One [tryscript](https://github.com/jlevy/tryscript) corpus runs against the Python CLI
and the TypeScript CLI under Node and Bun. It keeps a small set of end-to-end user flows
visible while unit and conformance tests cover boundary combinations.

## How It Works

Each scenario in `scenarios/` invokes the **neutral** `softschema` command and captures
full stdout/stderr/exit-code.
`run.sh` builds a shim that points `softschema` at the chosen implementation and runs
the suite:

```bash
SOFTSCHEMA_IMPL=py     ./tests/golden/run.sh   # the Python CLI (softschema-py)
SOFTSCHEMA_IMPL=ts     ./tests/golden/run.sh   # the TypeScript CLI under Node
SOFTSCHEMA_IMPL=ts-bun ./tests/golden/run.sh   # the TypeScript CLI under Bun
```

`ts` runs the built CLI under **Node**, the runtime npm users actually get via
`npx softschema`; `ts-bun` runs the same bundle under Bun.
Both must produce byte-identical output, so the published runtime is proven, not just
the dev one. (Run `bun run build` in `packages/typescript` first so `dist/cli.js`
exists.)

Because the CLI uses the same explicit portable serializer for compact hashes, pretty
JSON, and JSONL, plus engine-neutral errors and canonical compiled schemas, a single
expected-output block validates every implementation.
SARIF is projected from the same diagnostic-v1 records.
Parity is a test pass, not a manual audit.

Running the same scenarios against one committed expectation already proves
cross-implementation equality. There is no second parity runner with a duplicate command
inventory.

## File Formats

Scenario files are Markdown because tryscript records commands, output, and exit codes
together. Their output blocks preserve the CLI's literal format: JSON remains JSON when
the command's public output contract is JSON. Human-authored structured expectations
and shared vectors use YAML. Compiled JSON Schemas, strict JSON wire inputs, vendored
JSON standards, and generated integrity locks remain JSON because their encoding is
part of the contract.

## Stable vs Unstable

These scenarios are deterministic: commands use relative paths.
The only genuinely variable field is the version string (`--version`), matched with a
`[VERSION]` pattern.
Otherwise no patterns are needed.
Note in particular:

- `schema_sha256` is shown **literally**. It is a deterministic fingerprint of the
  canonical schema, so both implementations must produce the same digest; a divergence
  in the canonical profile surfaces here as a changed hash.
- Implementation-specific **semantic** errors (Pydantic vs Zod, with version-specific
  URLs) are intentionally avoided: failure scenarios validate against the schema only
  (`--schema`, no `--model`), so the structural error records are identical across
  engines. The `validate --model` scenarios (per-impl) assert only the semantic-ok path.
- **User-error stderr is engine-specific by design.** A missing file is
  `[Errno 2] No such file or directory` on Python and `ENOENT` on Node; a malformed
  `softschema` block ends `got list` vs `got object`. Where the wording diverges, the
  scenario merges streams with `2>&1` and asserts the stable `softschema <cmd>:` prefix
  plus exit code, eliding the engine-specific tail with `[..]`/`...`. Where the wording
  is identical (ambiguous envelope, missing implementation) it is asserted in full on
  stderr (`!`).
- **Number formatting.** Both implementations serialize the complete portable finite
  number domain with one byte contract.
  Whole-valued accepted numbers have no trailing fraction (`2.0` becomes `2`); non-whole
  values preserve the shared shortest spelling.
  Mathematically integral values outside `[-9007199254740991, 9007199254740991]` fail
  the portable value boundary before validation, hashing, or output rather than entering
  a divergent runtime representation.
- **Unicode source and output.** Literal U+0085, U+2028, and U+2029 source separators
  fail before YAML parsing; double-quoted escaped forms remain ordinary string values.
  Output key ordering uses Unicode scalar values, and JSONL records split only on the
  framing LF written by the serializer.

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

- `scenarios/`: neutral end-to-end scenarios that run on every runtime (py, ts, ts-bun).
  They use only language-neutral inputs (the compiled JSON Schema via `--schema`, batch
  discovery, `inspect`, `docs`, `skill`, `generate`, `--version`).
- `scenarios-py/`: Python per-impl scenarios (`compile` from a Pydantic class;
  `validate --model` against a Pydantic model).
  Run under `py`.
- `scenarios-ts/`: TypeScript per-impl scenarios that are **Node-safe**
  (`validate --model` against a plain `.mjs` Zod model importing only `zod`). Run under
  both `ts` and `ts-bun`.
- `scenarios-ts-bun/`: TypeScript per-impl scenarios that need a TS-capable runtime
  (`compile` imports a `.ts` model module, which plain Node cannot load).
  Run under `ts-bun` only; the same Zod→canonical-schema parity is independently proven
  by the cross-language conformance unit test
  (`packages/typescript/test/conformance.test.ts`).
- `fixtures/`: shared input artifacts.

| File | Scope | Covers |
| --- | --- | --- |
| `scenarios/validate.md` | all | schema-only validate: structural ok; structural failure (engine-neutral, sorted records); absent designated envelope (`envelope_mismatch`, exit 1) |
| `scenarios/cli-errors.md` | all | representative usage, input, and parse failures with exact exit behavior |
| `scenarios/warnings.md` | all | `document-status-mismatch` warning on a status override |
| `scenarios/inspect-and-docs.md` | all | complete `inspect` output, docs discovery, and bundled-topic resolution |
| `scenarios/pure-yaml.md` | all | explicit `pure-yaml` success, binding precedence, profile selection, malformed roots, and value-domain failures |
| `scenarios/batch-diagnostics.md` | all | recursive no-match as an exact diagnostic-v1 aggregate; byte-stable legacy JSON serialization |
| `scenarios/generate.md` | all | `generate --check` no-drift and drift (exit 1) |
| `scenarios/version.md` | all | `--version` (`[VERSION]` pattern) |
| `scenarios/error-normalization.md` | all | every structural error keyword, engine-neutral |
| `scenarios-py/compile.md` | py | `compile --check` no-drift (literal digest) and drift; source is a Pydantic class |
| `scenarios-py/validate-model.md` | py | `validate --model` semantic-ok paths for `frontmatter-md` and `pure-yaml` (Pydantic) |
| `scenarios-ts/validate-model.md` | ts, ts-bun | `validate --model` semantic-ok paths for `frontmatter-md` and `pure-yaml` (Zod `.mjs`) |
| `scenarios-ts-bun/compile.md` | ts-bun | same compile output; source is a Zod module (needs a TS runtime) |

Compile parity (content-identical compiled schema, equal digest) across languages is
additionally asserted by the cross-implementation conformance test.
Batch JSON/JSONL/SARIF, include/exclude filters, mixed-result precedence, and Unicode
source positions are covered by the shared Python and TypeScript batch tests.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
