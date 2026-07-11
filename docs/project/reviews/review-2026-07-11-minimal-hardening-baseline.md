---
title: Minimal Hardening Baseline
description: Main-branch behavior, public surface, and defect reproductions for the minimal hardening implementation
author: Codex, with maintainer direction from Joshua Levy
---
# Minimal Hardening Baseline

**Reviewed:** 2026-07-11

**Code baseline:** `main` at `3f31aa8`

**Implementation epic:** `ss-gwdt`

## Healthy Baseline

The implementation branch began from the working `main` code, with only the approved
plan committed. Before runtime changes:

- Python: 146 tests passed
- TypeScript: 170 tests passed, 95.85% function and 98.53% line coverage
- Python CLI goldens: 47 passed
- Node CLI goldens: 45 passed
- Bun CLI goldens: 47 passed
- direct Python-to-Node command parity: 20 commands passed
- TypeScript build and `publint`: passed
- production source: 6,120 lines
- unit tests: 14 Python files and 17 TypeScript files
- CLI goldens: 15 scenarios

These results characterize the existing capabilities.
They do not disprove the boundary defects below because the original tests did not
exercise those inputs.

## Defect Reproductions

The rows correspond in order to “Applicable Defects From `main`” in the plan spec.
Each is a reachable behavior in the baseline, not a defect in machinery added by the
abandoned PR.

| # | Baseline reproduction |
| --- | --- |
| 1 | Direct `validate_artifact` catches `OSError` as `parse_error`, while the CLI pre-read reports the same missing path as exit 2. Readable malformed YAML also exits 2 through the CLI instead of the planned validation-failure boundary. |
| 2 | A `Draft202012Validator` with `$ref` set to a local HTTP test server returned valid and the server recorded `GET /schema`. The Python validation path therefore performs implicit retrieval. |
| 3 | Python delegates embedded resource behavior to `jsonschema`; TypeScript deletes the root `$id`, uses one global Ajv instance, and exposes no explicit loaded-resource map. Nested resource bases and collisions therefore have no shared contract. |
| 4 | Python schema construction and iteration can raise schema, reference, and regex exceptions; TypeScript `sharedAjv.compile` throws. These failures bypass the normalized structural result in both low-level APIs. |
| 5 | Python parsed `x: 2026-07-11` as `datetime.date`; TypeScript parsed it as the string `"2026-07-11"`. The same source therefore reaches models and output with different types. |
| 6 | Artifact, sidecar, `SchemaView`, and drift-check paths use `read_text`, `readFileSync`, or parser helpers without a byte check. A large untrusted artifact is fully allocated before rejection. |
| 7 | Python considered `"not-an-email"` valid under `{type: string, format: email}`; TypeScript returned invalid because `addFormats` installs assertions. |
| 8 | Patterns are passed directly to Python `re` and JavaScript `RegExp` through the validators. The runtimes accept different syntax and have different anchor and Unicode behavior. |
| 9 | TypeScript `stableStringify({"10":"ten","2":"two","a":"a"})` emitted key order `2,10,a` even after its sorting pass because JavaScript reorders integer-like keys. Python `sort_keys=True` requests lexical order `10,2,a`. |
| 10 | Canonicalization handles only a partial set of schema-bearing keywords and removes empty `default` annotations. It can therefore skip nested compiler normalization and discard authored annotation data. |
| 11 | Applying the current enforced overlay to two `allOf` object branches made `{a: x, b: y}` invalid: each branch rejected the property declared by the other branch. |
| 12 | `Contract(id="bad id")` succeeded. `compile_model` without `contract_id` also succeeded and copied the optional contract into `$id`, conflating logical and resource identities. |
| 13 | Compiler augmentation calls `.update` on model-supplied root `x-softschema`; a nonmapping value crashes, while a mapping is silently merged with compiler-owned metadata. |
| 14 | Python Pydantic metadata and TypeScript compile-time interfaces enforce different runtime rules. JavaScript callers can pass malformed group/order/owner/aliases, and Python may coerce values before emission. |
| 15 | Python drift comparison uses ordinary equality, where `True == 1`. TypeScript decodes committed sidecars through a nonfatal UTF-8 string read. Either can hide nonportable committed content. |
| 16 | A property with `$ref` and sibling `description: sibling` produced `description: target` in `SchemaView.field`; the sibling annotation was discarded. The nullable helper also selects the first typed/enum branch from genuine unions. |
| 17 | `SchemaView.contract_id` falls back to `$id`, so a JSON Schema URI can be reported as the logical artifact contract. |
| 18 | Python resolves real paths before document-schema containment. TypeScript checks the lexical path and then opens it, so an in-tree symlink can select an out-of-tree target. |
| 19 | TypeScript dynamically imports a raw resolved path string. Spaces, `#`, `%`, and Windows drive paths can be interpreted as URL syntax instead of one local file URL. |
| 20 | Python walks arbitrary module ancestors looking for `pyproject.toml` and `docs`; TypeScript walks package ancestors for matching resource paths. A consumer repository can shadow installed resources. |
| 21 | Both installers overwrite any existing target whose bytes differ. They have no unmanaged-file refusal, explicit scope, target selector, or dry run. |
| 22 | README, help, and skill bootstrap examples execute `softschema@latest` through zero-install runners even though consumers are not guaranteed to have the repository cool-off policy. |
| 23 | CI uses moving action tags, project-synchronizing installs, and source-oriented checks. Publication does not prove one exact wheel/sdist/npm candidate through installation before both OIDC jobs publish it. |
| 24 | Public docs claim byte-identical general output, imply broader schema safety, and list agent bootstrap/discovery behavior more strongly than installed-package tests prove. |

## Excluded Prior-PR Work

The old PR’s later Windows descriptor fixes, glob and discovery budgets, conformance
adapter validation, Pages publishing, release recovery, transactional installer repair,
SARIF, JSONL, source maps, and custom regex automata fix systems that do not exist on
`main`. They are not baseline reproductions and do not enter this implementation.

## Baseline Commands

```bash
uv run --no-sync pytest

cd packages/typescript
bun run check
bun run build
bun run publint

cd ../..
SOFTSCHEMA_IMPL=py bash tests/golden/run.sh
SOFTSCHEMA_IMPL=ts bash tests/golden/run.sh
SOFTSCHEMA_IMPL=ts-bun bash tests/golden/run.sh
bash tests/golden/cross-impl-diff.sh
```

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
