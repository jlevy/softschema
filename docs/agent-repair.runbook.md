---
name: agent-repair
description: >-
  The manual end-to-end check for `softschema repair`: drive a real
  low-thinking model at a form contract it has never seen the schema for, and
  watch both halves of the feature work — the drift repair fixes silently, and
  the drift it refuses to guess at and reports instead. Use after changing
  repair, conform, or profile detection, and before tagging a release that
  touches them.
---
# Agent Repair Runbook

`repair` exists so the agent that writes an artifact can run the same check its consumer
will run, while it can still act on the answer.
That claim is only testable against artifacts a real agent really wrote, so this runbook
drives one and reads the results.

CI proves repair against fixtures whose mistakes were chosen by a person.
This runbook proves it against mistakes chosen by a model, which is where the surprises
live: the first run of it found a defect where `--repair` reported `valid` for a
document plain `validate` could not open at all
([review](project/reviews/review-2026-08-30-validate-repair-e2e.md), Finding 1).

Run it after changing `repair`, `conform`, `pipeline`, or profile detection, and before
tagging a release that touches them.
It is manual by design: it makes live model calls and cannot run in CI.

## What It Costs

- A `GOOGLE_API_KEY` with access to the Gemini API.
- About 50 model calls across the four phases, on `gemini-2.5-flash`. A few minutes.
- No repository state: every artifact is written under `tests/manual/agent-repair/runs/`
  and `work/`, both gitignored.

```bash
export GOOGLE_API_KEY=...        # required by phases 1-3
cd tests/manual/agent-repair
```

## Phase 0 — The Setup, and Why It Is Shaped This Way

Four files, all in `tests/manual/agent-repair/`:

| File | Role |
| --- | --- |
| `prelim-scan-terms.schema.yaml` | the contract. **The agent never sees this.** |
| `form-runbook.md` | prose describing the form, the way a pipeline runbook does |
| `form-template.md` | a fill-in-the-blanks template |
| `run_agents.py` / `evaluate.py` / `feedback.py` | drive the model, judge, and loop |

The contract is loosely borrowed from the GTIA v2 `prelim-scan-terms` form in
`finterm-ai/trading`, whose real pipeline runs a Gemini Flash model through a
`gemini-cli` adapter.
It keeps that form’s shape — a ticker pattern, a date, a `search_fit` enum, an integer
`term_budget`, a `rubric_version` string, and four panels of `{term, why}` items — under
`additionalProperties: false` and `status: enforced`.

**The agent must never be shown the JSON Schema.** That is the whole point.
An agent handed the schema copies field names out of it and the exercise proves nothing;
an agent handed prose has to choose the names itself, and the drift that follows is the
drift production actually sees.

Two authoring conditions, twelve tickers each, because they fail differently:

- **templated** — field names are given.
  Expect *value* drift.
- **prose** — field names must be inferred from the runbook’s wording.
  Expect *field-name* drift.

## Phase 1 — Templated Authoring: What Repair Fixes Unaided

```bash
python3 run_agents.py gemini-2.5-flash 0 templated
python3 evaluate.py templated
```

`0` is the thinking budget.

**Expect** most artifacts to arrive invalid and **all of them to repair to valid with no
agent involvement**, each with a single `scalar_conformed` record at
`['rubric_version']`.

The recorded run: 9 of 12 invalid on arrival, 9 of 9 repaired.
The agent wrote `rubric_version: 1.10` unquoted, YAML read it as the float `1.1`, and
the contract declares `type: string`.

Check the repair preserved the notation, which is the spec’s stated promise and the
difference between a correct artifact and a quietly wrong one — `1.1` and `1.10` are
different rubrics:

```bash
grep -h rubric_version runs/templated/*.md | sort | uniq -c    # before
grep -h rubric_version work/templated/*.md | sort | uniq -c    # after: '1.10', not 1.1
```

`as_of_date` needs no repair: portable timestamp normalization already carries it as a
string.

`evaluate.py` also asserts the three conformance guarantees on every artifact —
`repair --check` never writes, repair is idempotent, and an artifact needing no repair
comes back byte-identical.
`python3 summarize.py templated` prints them.

## Phase 2 — Prose Authoring: What Repair Refuses to Guess

```bash
python3 run_agents.py gemini-2.5-flash 0 prose prose
python3 evaluate.py prose
python3 summarize.py prose
```

**Expect** every artifact to stay invalid, with a large, *paired* error count.

The recorded runs: 880 and 906 structural errors across 12 artifacts, essentially all
`undeclared_property` or `missing_property` in equal numbers.
The model systematically wrote `query`/`reason` where the contract declares `term`/`why`
— 220 and 226 items.

Repair **must not rename them**, and the report must name both halves at the same path:

```
code=undeclared_property  property=query   path=['panels','category',0]
code=missing_property     property=term    path=['panels','category',0]
```

That pairing is the deliverable.
A rename would be a guess about intent; the paired records let the agent make that call
itself with the position pinned exactly.

## Phase 3 — The Loop: Can the Agent Act on the Report?

```bash
python3 feedback.py prose
```

Hands every record back to the *same zero-thinking model* and asks it to fix only what
the records call out.

**Expect all twelve to reach `valid` in one round.** Both recorded runs cleared every
error — 880 to 0, and 906 to 0.

> **Do not truncate the record list.** An earlier run capped it at 60 records and scored
> 9 of 12; the residual error counts on the three failures matched the withheld records
> exactly. `feedback.py` sets `RECORD_CAP = 500` for this reason.
> A low cap makes the feature look worse than it is and hides the real result.

## Phase 4 — The Regression Case

No model needed, and it is the reason this runbook exists.
A document that opens frontmatter and never closes it — what a truncated agent write
leaves behind — must be refused by **both** paths:

Run it against **the build under test**, not whatever `softschema` resolves to on `PATH`
— a globally installed copy would quietly test the wrong code, which is the one outcome
a regression check must not have.
`SS` below is the same invocation the harness scripts use.

```bash
SS="uv run --frozen --no-config --project $PWD/../../.. softschema"   # or: node packages/typescript/dist/cli.js
cd "$(mktemp -d)"
printf -- '---\nsoftschema:\n  contract: t:M/v1\n  envelope: rec\n  status: soft\nrec:\n  name: Acme\n' > truncated.md

$SS validate truncated.md              # exit 2, delimiter not found, no result document
$SS repair truncated.md --check        # exit 1, the same cause as a record
```

The artifact binds no schema, so nothing needs copying into the temp directory: the
document never gets far enough to resolve one.

**Expect both to refuse it**, in each command’s own voice: `validate` reads, so it says
so in one line and exits 2; `repair` checks, so the same cause comes back as a
`yaml_parse_error` record at exit 1, where the agent that wrote the file can act on it.
Neither may report that the document has no frontmatter — the block is plainly there —
and `repair` must not ask for `--contract`, which would not have helped.

A `valid` from the second command is the original defect.
The golden corpus pins this as
`Journey: an unterminated frontmatter fence is unreadable on both paths`; run it against
all three runtimes with
`SOFTSCHEMA_IMPL=py|ts|ts-bun ./tests/golden/run_golden_tests.py`.

### The second case: a file ending at its closing fence

The same detector-versus-reader gap produced a second defect one function over, so check
both. A file whose last byte is the closing `---` — no trailing newline, an ordinary
shape for agent-written text — must repair exactly like the same document with a
newline. It once did not: the offset scan read “no newline left” as “no closing fence”,
found no region to rewrite, and `--repair` silently skipped an artifact it could fix.

```bash
printf -- '---\nsoftschema:\n  contract: t:M/v1\n  envelope: rec\n  status: soft\nrec:\n  summary: Note: actually Q1\n---' > ends-at-fence.md

$SS repair ends-at-fence.md --check    # outcome valid, one yaml_quoted_scalar repair
```

**Expect** `"outcome": "valid"` with a `yaml_quoted_scalar` record.
A read failure, or an empty `repairs` list, is the defect: the document is one byte from
one that repairs cleanly.

The golden corpus pins this as
`Journey: a document ending at its closing fence is still repaired`.

## Expected Results

From the recorded run on `gemini-2.5-flash`:

The model is sampled at temperature 1, so the counts move between runs; the *shapes* do
not. Two recorded runs:

| Phase | Condition | Result |
| --- | --- | --- |
| 1 | templated, budget 0 | 9-12 of 12 invalid on arrival, **every repairable one repaired to valid** unaided |
| 2 | prose, budget 0 | 12/12 invalid, 880-906 paired records, **0 renames**, every run |
| 3 | feedback, budget 0 | **12/12 valid in one round**, every error cleared, every run |
| 4 | regression cases | `validate` exits 2, `repair --check` exits 1 with the same cause as a record |

Read the bold parts as the assertions and the counts as context.
A run where Phase 2 reports 850 or 950 errors is normal; a run where Phase 1 leaves a
*repairable* artifact unrepaired, Phase 2 performs a rename, or Phase 3 lands below 12
is not.

**`refused_with_cause` in Phase 1 is a pass, not a failure.** The model sometimes writes
a line that is malformed rather than merely unquoted — a missing `: ` after a key, an
unterminated fence — and repair declines to guess at it, naming the line and column
instead. Quoting cannot insert a key separator, and inventing one would be a guess about
intent. Count those separately from the repairable artifacts before reading Phase 1 as a
drop.

Investigate a **drop**, particularly a repair that stops preserving notation, a rename
appearing in Phase 2, or a Phase 3 score below 12 that is not explained by a record cap.

## Things That Will Bite You

**Thinking budget barely moves field-name drift.** Budget 0 versus 4096 in the prose
condition gave 880 versus 747 errors with the same substitution dominating.
The drift tracks ambiguity in the runbook prose — it says “the query text itself and a
short reason”, and the model takes the field names from those words.
The lever is naming fields in prose exactly as the schema declares them, or templating
them; the templated condition produced zero field-name errors at budget 0. Do not read a
high Phase 2 error count as a model-quality problem.

**A thinking model nests its fences.** At a non-zero budget the reply often opens
`markdown` and then `yaml` immediately after, so a regex that stops at the first closing
fence captures an empty span.
`run_agents.py` anchors on the artifact’s own leading `---` instead.

**Thought parts are not answer parts.** With a thinking budget the response `parts`
array can lead with a thought summary; reading `parts[0].text` returns thinking, or
nothing. `run_agents.py` joins only the parts without a `thought` flag.

**Prompt ambiguity about the `---` delimiters will silently invalidate a run.** An
earlier prose prompt showed the metadata as a
```yaml block; at budget 4096 the model reproduced exactly that and emitted no `---`
fences at all, so all twelve artifacts failed for a reason that had nothing to do with
repair. The prompt now shows the fences explicitly.
If a whole batch fails identically, suspect the prompt before the code.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
