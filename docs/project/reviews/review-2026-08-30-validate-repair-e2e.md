---
title: validate --repair End-to-End Agent Testing
description: What a low-thinking agent actually produces against a real form contract, what repair fixed, what it reported, and one profile-inference divergence that breaks the feature's premise
author: Claude, with maintainer direction from Joshua Levy
---
# Review: `validate --repair` End-to-End Agent Testing

**Date:** 2026-08-30

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** Testing complete.
One release-blocking defect found (Finding 1).

## What Was Tested

`--repair` exists so the producing agent can run the same check its consumer will run.
That claim is only testable against artifacts a real agent really wrote, so this pass
drove **Gemini 2.5 Flash at `thinkingBudget: 0`** over a form contract and fed it
nothing but a prose runbook and a template — never the JSON Schema.
Field-name and value drift therefore arose the way it does in production rather than
being planted.

The contract is loosely borrowed from the GTIA v2 `prelim-scan-terms` form in
`finterm-ai/trading` (`v2-google-trends-information-arb/prelim-google-trends-scan/`),
whose real pipeline runs `gemini-3.6-flash` through a `gemini-cli` adapter.
It keeps that form’s shape — a ticker pattern, a date, a `search_fit` enum, an integer
`term_budget`, a `rubric_version` string, and four panels of `{term, why}` items — under
`additionalProperties: false` and `status: enforced`.

Two authoring conditions, twelve tickers each:

- **templated** — the agent gets a filled-in-the-blanks template.
  Field names are given.
- **prose** — the agent gets only the runbook’s prose descriptions and must choose the
  field names itself.

Harness in `attic/e2e-repair/` (gitignored; needs `GOOGLE_API_KEY`).

## Findings

### Finding 1 — `validate` and `--repair` disagree about whether a document is readable

**Release-blocking.** Both implementations, deterministic, no agent needed.

A document that opens frontmatter with `---` and never closes it — exactly what a
truncated agent write produces:

```
---
softschema:
  contract: t:M/v1
  schema: mini.schema.yaml
  envelope: rec
  status: enforced
rec:
  name: Acme
```

| Command | Python | TypeScript |
| --- | --- | --- |
| `softschema validate f.md` | exit 2, “Delimiter `---` for end of frontmatter not found” | exit 2, same |
| `softschema validate f.md --check-repair` | `outcome: valid`, `profile: pure-yaml` | `outcome: valid`, `profile: pure-yaml` |

The producer is told its artifact is **valid**. The consumer **cannot read the file at
all**. That is precisely the failure mode `--repair` exists to prevent, and it inverts
the feature’s premise: the check the producer runs is not the check the consumer runs.

**Root cause.** The two paths infer different profiles.
Plain validation reads through `parse_frontmatter_text`, which *raises*
`PortableInputError` on an unterminated fence
(`packages/python/src/softschema/validate.py:966-971`). The repair path reads through
`split_frontmatter`, which *returns `None`* for the same input
(`packages/python/src/softschema/_portable.py:217`, and its TypeScript twin).
`None` means “no frontmatter”, so profile inference — which reads a fenceless document
carrying a root `softschema:` block as `pure-yaml` — selects `pure-yaml`, the leading
`---` is consumed as a YAML document-start marker, and the whole file parses cleanly.

`split_frontmatter`’s own docstring asserts the invariant that is violated:

> Returns `None` when the document has no frontmatter, matching what
> `read_frontmatter_doc` reports: no leading fence, **an unterminated fence**, or an
> empty block…

`read_frontmatter_doc` does not report an unterminated fence as “no frontmatter”; it
raises. The two readers were written twice precisely so they would agree, and on this
input they do not.

Cross-implementation parity did not catch it because Python and TypeScript diverge
*identically*. Passing `--profile frontmatter-md` explicitly makes both paths agree, so
the defect is in inference, not in the readers themselves.

This ships with the unreleased `--repair` work; v0.7.0 has no repair path to disagree
with.

### Finding 2 — scalar conform handles real drift, and preserves notation

In the templated condition, 9 of 12 artifacts were invalid on arrival and **all 9 were
repaired to valid** with no agent involvement.
Every repair was the same record, `scalar_conformed` at `['rubric_version']`: the agent
wrote `rubric_version: 1.10` unquoted, YAML read it as the float `1.1`, and the contract
declares `type: string`.

Repair wrote `'1.10'` — **the trailing zero survived**, which is the spec’s stated
promise that the replacement text is the scalar as written.
On a version field, `1.1` and `1.10` are different rubrics, so this is the difference
between a correct artifact and a quietly wrong one.

`as_of_date: 2026-08-30` needed no repair: portable timestamp normalization already
carries it as a string.

### Finding 3 — near-miss field names are reported, never renamed, and the report is actionable

In the prose condition the agent systematically chose `query`/`reason` where the
contract declares `term`/`why` — 220 items across 12 artifacts.
Repair correctly declined to rename them, and emitted a **paired** diagnosis per item:

```
code=undeclared_property  property=query   path=['panels','category',0]
code=missing_property     property=term    path=['panels','category',0]
```

880 structural errors across the corpus, every one carrying `kind` + `code` + `path` +
`property`.

The actionability test was to hand those records back to the *same* zero-thinking model
and ask it to fix only what they call out.
**12 of 12 artifacts went to `valid` in a single round**, 880 errors to 0.

An earlier round scored 9 of 12; the three partials were an artifact of this harness
truncating the record list at 60, and the residual error counts matched the withheld
records exactly. Given the complete list the model fixed everything.
The records are sufficient; the only requirement is not to truncate them.

### Finding 4 — thinking budget does not change the drift that matters

`thinkingBudget: 0` and `thinkingBudget: 4096` in the prose condition produced
substantially the same failure: 880 versus 747 structural errors, the same
`query`/`reason` substitution dominating both.
Field-name drift tracks **ambiguity in the runbook prose**, not the model’s reasoning
budget — the runbook says “the query text itself and a short reason”, and the agent
takes the field names from those words at either budget.

The practical lever is naming fields in the prose exactly as the schema declares them,
or templating them. The templated condition produced zero field-name errors at
`thinkingBudget: 0`.

### Conformance guarantees held

Checked on every artifact in every run:

- `--check-repair` never wrote the file.
- Repair is idempotent — a second pass produced byte-identical output.
- An artifact needing no repair came back byte-identical.
- No repaired artifact was subsequently rejected by softschema’s own reader.

## Recommendation

Fix Finding 1 before tagging v0.8.0. The narrow fix is to make profile inference on the
repair path treat an unterminated frontmatter fence the way the reader does — as an
error on a document that declared frontmatter intent — rather than as evidence of a
fenceless `pure-yaml` document.
A golden journey case belongs with it, since parity testing cannot see a divergence both
implementations share.

Findings 2 and 3 are the feature working as designed on real agent output, including the
part that matters most: an agent with no reasoning budget can act on the report unaided.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
