---
title: repair Command End-to-End Review
description: A fresh end-to-end pass over the repair command on live agent output plus a 21-case matrix of ordinary authoring mistakes, finding one cross-runtime read divergence, one harness misscoring, and two documentation defects
author: Claude, with maintainer direction from Joshua Levy
---
# Review: `repair` Command End-to-End

**Date:** 2026-08-30

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** Testing complete.
One cross-runtime defect found and fixed, one harness defect fixed, two documentation
defects fixed. No release blockers outstanding.

## What Was Tested

Two passes, because they answer different questions.

The first re-ran [`docs/agent-repair.runbook.md`](../../agent-repair.runbook.md) in
full, as written, on the PR #52 surface — `gemini-2.5-flash` at `thinkingBudget: 0`, 24
live artifacts across the templated and prose conditions.
That asks whether the feature holds on mistakes a model actually made.

The second is new here: a **21-case matrix of ordinary authoring mistakes**, each run
through `validate`, `repair --check`, `repair --dry-run`, and `repair` twice, on **both
implementations**, comparing every field of both results.
The runbook drives one model at one form; a model that never happens to write a tab or a
duplicate key leaves that behavior untested no matter how many times the runbook runs.
The matrix covers the classes on purpose: unquoted `: `, numeric-looking strings, a
truncated fence, a missing key separator, tab indentation, duplicate keys,
`yes`/`no`/`off` scalars, a `#` mid-value, `@` and `*` leading scalars, curly quotes,
CRLF, a byte order mark, a whole document wrapped in a code fence, no frontmatter, empty
frontmatter, a sequence where a mapping belongs, invalid UTF-8, a file ending at its
closing fence, an unindented list, and both repairable classes in one document.

## Findings

### Finding 1 — A leading byte order mark split the two runtimes (fixed)

**The defect.** `read_utf8` / `readUtf8` is the one function both implementations route
every artifact and schema read through, and the two decoded a BOM differently.
TypeScript uses `TextDecoder("utf-8")`, whose default `ignoreBOM: false` strips the
mark; Python’s `bytes.decode` kept it as a U+FEFF character.

Every fence check in the codebase — `opens_frontmatter_fence`, `split_frontmatter`, and
both readers — asks whether a first line equals `---`, and `"﻿---"` does not.
So identical bytes got opposite verdicts:

```
npx softschema validate bom.md   ->  exit 0, outcome valid
uvx softschema validate bom.md   ->  exit 2, missing --contract because the document
                                     has no YAML frontmatter
```

**Why it matters more than a BOM usually does.** Two reasons, neither about the mark.

The first is that this is the *only* parity break in 21 cases, and parity is an
invariant this project holds with a dedicated CI job.
A pipeline producing on Node and consuming on Python gets opposite answers about whether
an artifact is readable at all, which inverts the premise `repair` exists to serve.

The second is the wording.
`missing --contract because the document has no YAML frontmatter` is the exact
diagnostic this PR set out to eliminate: a block that is plainly there, and a flag that
would not have helped, delivered to the caller who most needs a real answer.
The unterminated-fence journey states the rule — *neither may report that the document
has no frontmatter* — and one invisible byte walked around it.

**The fix.** Strip on decode, once, where the bytes become text, so no fence comparison
has to know about it.
A U+FEFF anywhere but position zero is content and survives.
The mark does not survive a rewrite, because repair emits the decoded text — a BOM
artifact and its plain twin converge on identical bytes on both runtimes.
Repair only writes when it has a change to make, so a clean BOM document keeps its mark;
stripping is a read rule, not a normalization pass over the tree.

**Why the corpus missed it.** Unlike the unterminated fence, where both runtimes
diverged in the *same* direction and left `cross-impl-diff.sh` clean while both were
wrong, this divergence ran between the runtimes — the parity job could have caught it,
and nothing in the corpus carried a BOM. The new fixture is what gives it something to
compare, alongside per-implementation unit tests and a golden journey pinning that the
two twins converge.

Golden corpus: **80 Python / 78 Node / 80 Bun**, parity OK.

### Finding 2 — The runbook’s own harness misscored a correct refusal (fixed)

`evaluate.py` classifies a document-level record as `refused_with_cause` — the designed
outcome — only when its `kind` is in `DOCUMENT_LEVEL_KINDS`. That set listed six kinds.
The CLI emits at least sixteen: every `PortableInputError.code` reaches the record
unchanged.

`yaml_duplicate_key`, `yaml_alias`, and `invalid_utf8` were missing, and all three are
well within what a model writes — a repeated field, an `&anchor` copied out of an
example, a mangled byte in a long value.
Any of them scored `reported_unclear`, so a **correct** refusal would have read as a
repair failure.

This is the same trap the runbook already documents for the phase 3 record cap: a
harness bug that makes the feature look worse than it is.
The set is now complete and carries the derivation of each half, so the next kind added
to the CLI has somewhere obvious to go.

### Finding 3 — Phase 4 could not be run as written on the TypeScript build (fixed)

The runbook offers `node packages/typescript/dist/cli.js` as the alternative `SS`, on
the line directly above `cd "$(mktemp -d)"`. A relative path does not survive that `cd`;
following the runbook verbatim on the TypeScript build gets `MODULE_NOT_FOUND`, not a
regression result.

The Python form was already correct — `$PWD/../../..` expands before the `cd` — which is
what hid it. Both forms now resolve through `$PWD`, and the reason is stated, because it
is the sort of thing that gets “tidied” back into a relative path.

This matters more than an ordinary typo because of what the surrounding paragraph
promises: run this against **the build under test**, since a globally installed copy
would quietly test the wrong code.
The one runtime where that warning was hardest to honor was the one whose command did
not work.

### Finding 4 — `repair --check` exit 1 read as a failure in phase 4’s second case (fixed)

The first regression case annotates both exit codes.
The second pins `"outcome": "valid"` and says nothing about the exit code, which is
**1** — `--check` asserts nothing needed changing, and something did.
A reader following the runbook sees a passing verdict and a failing exit on the same
command and has no way to tell which was intended.

Stated now, along with the `--dry-run` contrast, since that is exactly the distinction
the two flags exist to draw.

## What Held

**The runbook reproduced, phase for phase**, on the new surface:

| Phase | Recorded | This run |
| --- | --- | --- |
| 1 — templated | 9 of 12 invalid, 9 of 9 repaired | 9 of 12 invalid, **9 of 9 repaired** |
| 2 — prose | 880–906 records, exactly paired, 0 renames | **888 records: 444 `undeclared_property`, 444 `missing_property`**, 0 renames |
| 3 — feedback | 12/12 valid in one round | **12/12 valid, 888 → 0** |
| 4 — regression | both paths refuse | `validate` exits 2, `repair --check` exits 1, same cause |

Notation preservation held: nine artifacts arrived with `rubric_version: 1.10` unquoted,
and all nine came back `'1.10'` — not `1.1`, which is a different rubric.
Phase 2’s pairing was exact at every path: zero paths carried an `undeclared_property`
without its `missing_property`, or the reverse.

**The conformance guarantees held on all 45 artifacts** — 24 live agent artifacts and
the 21 matrix cases, on both implementations:

- `repair --check` never wrote.
  `repair --dry-run` never wrote.
- Repair is idempotent — a second pass changed nothing, in every case.
- An artifact needing no repair came back byte-identical.

**The two write-suppressing flags behave as the PR describes them.** Across the matrix,
`--dry-run` exits 0 whenever the document repairs to valid and `--check` exits 1
whenever anything would change, with no case where the two disagreed about *what* would
change.

**Repair is byte-minimal in the ways that are easy to get wrong.** A CRLF document came
back with nine CRLF line endings and no bare LF. A document ending at its closing fence
kept that ending — no trailing newline was added.
Only the one scalar moved in each.

**Reporting quality on the enforced path is good.** A near-miss key (`rubric_versionn`)
came back as an `undeclared_property` paired with the `missing_property` it resembles,
with no rename attempted; enum violations name the permitted set; nested paths are
exact.

## Observations, Not Defects

**Repair’s value-conforming power is entirely schema-gated, and that is worth saying out
loud.** Under `status: soft` with no schema bound, `zip: 02134` reads as `2134`,
`ticker: 007` as `7`, and `version: 1.10` as `1.1`, all reported `valid` — correctly,
since no contract declares them strings.
The templated phase works because the contract says `type: string`. An artifact with no
schema gets no protection from the most common class of value drift; this is by design
and matches the documented adoption path, but it is the sharpest argument in the docs
for binding a schema early.

**A `#` inside an unquoted value is silently truncating and nothing can see it.**
`note: see issue #42 for detail` parses to `"see issue"`, and both implementations
report `valid`. Unlike the `: ` case, this is not a parse failure — it is legal YAML
whose value is simply not what the author typed, so there is no signal for repair to act
on and no defect here to fix.
It is the one common authoring mistake in the matrix that the feature cannot help with,
and it may deserve a line in the guide beside the two it does fix.

**Python’s YAML diagnostics are less precise than TypeScript’s for the same document.**
For an unindented list, ruamel reports line 1, column 1; the `yaml` package reports line
6, column 9 and prints the offending line with a caret.
Both are honest, both come from the engines rather than from softschema, and the machine
records are identical — but an agent reading the message gets materially better guidance
on Node. Worth knowing when reading a phase 2 or 3 result that came from one runtime.

**`repair` conforms a number to a declared string but not a string to a declared
integer.** `term_budget: "12"` against `type: integer` is reported, not repaired.
This is consistent with the documented scope — quoting is lossless, unquoting is a guess
about intent — and the report is clear.
Noting it only because over-quoting is the mirror of the mistake phase 1 exercises.

## Verdict

The feature does what the PR claims, on live agent output and on a systematic sweep of
ordinary authoring mistakes, with byte-level guarantees holding on every artifact
tested.
The one real defect found was a cross-runtime read divergence of exactly the kind
this PR exists to close, reached through a byte nobody can see; it is fixed, pinned in
the corpus where the parity job can see it, and pinned per-implementation where the unit
tests can.

The other three findings are in the testing apparatus and its documentation rather than
in the product, and all three shared a shape worth naming: each would have made a
correct result look like a failure, or made a check impossible to run as written.
A runbook is only as good as its worst instruction, and phase 4 had two.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
