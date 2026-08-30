---
type: is
id: is-01m184t4f55k2qgsm215ve0cdz
title: validate --repair reads an unterminated frontmatter fence as pure-yaml (TypeScript)
kind: bug
status: closed
priority: 0
version: 7
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies:
  - type: blocks
    target: is-01m184tjxg9zgfkppdsm13fcsh
  - type: blocks
    target: is-01m184tkby56c2s7phxdzm1kq1
  - type: blocks
    target: is-01m184vjqxckqhnfdb28gze3b2
  - type: blocks
    target: is-01m184v3tye1c77f0mmzfr5fnf
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:33:43.269Z
updated_at: 2026-08-30T01:41:21.889Z
closed_at: 2026-08-30T01:41:21.889Z
close_reason: "Fixed: detect_profile/detectProfile now test whether the document opens a frontmatter fence (new opens_frontmatter_fence / opensFrontmatterFence helper) instead of whether split_frontmatter can split it, so an unterminated fence stays frontmatter-md in both languages. The repair path also carries the parse error into the missing-contract reason, so an unreadable frontmatter is named rather than reported as absent. split_frontmatter's false invariant corrected in both docstrings. All suites green: pytest 225, bun 223, golden 68/66/68, cross-impl parity OK."
resolution: null
duplicate_of: null
---
The TypeScript CLI diverges identically to the Python one (see the sibling bug), on the
same input and with the same verdicts:

| Command | Result |
| --- | --- |
| `node dist/cli.js validate f.md` | exit 2, "Delimiter `---` for end of frontmatter not found" |
| `node dist/cli.js validate f.md --check-repair` | `outcome: valid`, `profile: pure-yaml` |

## Root cause

Mirror of the Python defect:

- `readArtifact` (packages/typescript/src/cli.ts:413) is the non-repair path and throws
  on an unterminated fence.
- `detectProfile` (packages/typescript/src/cli.ts:675) is the repair path and tests
  `splitFrontmatter(text) !== null` at cli.ts:683; `splitFrontmatter`
  (portable.ts:204) returns `null` for an unterminated fence, so detection falls
  through to the pure-yaml branch.

## Fix

Same shape as the Python fix and it must land in the same change: add the
"does this text open a frontmatter fence?" helper to `portable.ts` and consult it in
`detectProfile` before the pure-yaml fallback. The two runtimes deliberately implement
this scan twice so they split identically, so the helper has to be written twice too.

## Why parity testing did not catch this

`cross-impl-diff.sh` compares Python against TypeScript. Both implementations diverge
in exactly the same direction, so the parity diff is clean while both are wrong. The
regression coverage for this has to be a golden case that pins the *expected* verdict,
not a cross-implementation comparison.

## Acceptance

`validate` and `validate --check-repair` agree that the repro document is unreadable
under the TypeScript CLI, under both Node and Bun.
