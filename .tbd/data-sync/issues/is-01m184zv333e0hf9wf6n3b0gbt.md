---
type: is
id: is-01m184zv333e0hf9wf6n3b0gbt
title: Repair path reports a misleading 'no YAML frontmatter' reason when the frontmatter exists but will not parse
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies:
  - type: blocks
    target: is-01m184vk6ayjkkpjp9d7ncgnfh
  - type: blocks
    target: is-01m184tjxg9zgfkppdsm13fcsh
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:36:50.275Z
updated_at: 2026-08-30T01:41:21.892Z
closed_at: 2026-08-30T01:41:21.892Z
close_reason: "Fixed: detect_profile/detectProfile now test whether the document opens a frontmatter fence (new opens_frontmatter_fence / opensFrontmatterFence helper) instead of whether split_frontmatter can split it, so an unterminated fence stays frontmatter-md in both languages. The repair path also carries the parse error into the missing-contract reason, so an unreadable frontmatter is named rather than reported as absent. split_frontmatter's false invariant corrected in both docstrings. All suites green: pytest 225, bun 223, golden 68/66/68, cross-impl parity OK."
resolution: null
duplicate_of: null
---
Second divergence found while fixing the profile-detection bug (ss-bh5t/ss-e2rf). Same
premise broken, different mechanism, and it predates that fix.

For a document whose frontmatter is present but unparsable — the existing
`tests/golden/fixtures/repair-unrepairable.md`, whose body is `data: [unclosed`:

| Command | Result |
| --- | --- |
| `softschema validate f.md --schema s.yaml` | the real YAML error: "while parsing a flow sequence ... line 5, column 7" |
| `softschema validate f.md --schema s.yaml --check-repair` | "missing --contract because the document has no YAML frontmatter" |

The document plainly *has* frontmatter. The agent is told the wrong thing about its own
artifact and cannot act on it.

## Mechanism

`_parse_after_repair` (packages/python/src/softschema/cli.py:486) deliberately swallows
`PortableInputError` and returns `None`, documenting that "validation reports the parse
failure itself". It does not get that far: `_infer_validation_binding` runs next, finds
no metadata, and fails with `_missing_contract_reason` (cli.py:532), whose
frontmatter-md branch is the flat string "missing --contract because the document has
no YAML frontmatter".

The existing golden journey hides this because it passes the binding as flags
(`--contract test.repair:Doc/v1 --envelope data`), and its own prose explains why: "the
document's `softschema:` block sits inside the very frontmatter that cannot be read".
With an explicit binding the result is a proper structured parse-failure verdict. The
no-flags path — what an agent validating its own output actually runs — is the broken
one.

## Fix

Keep the tolerant parse, but stop discarding the reason. Have `_parse_after_repair`
hand back the `PortableInputError` alongside the `None` document, and have the
missing-contract reason report that error when one is present rather than asserting
there is no frontmatter.

Do not make the error propagate instead: with an explicit binding, `--repair` returns a
structured parse-failure result, which is strictly better for an agent than plain
`validate`'s exit 2, and the golden journey pins that behavior.

Mirror in TypeScript: `parseAfterRepair` and `missingContractReason` in
packages/typescript/src/cli.ts.

## Acceptance

`--check-repair` with no binding flags on an unparsable-frontmatter document names the
parse failure, and a reader can tell it apart from a document that genuinely has no
frontmatter.
