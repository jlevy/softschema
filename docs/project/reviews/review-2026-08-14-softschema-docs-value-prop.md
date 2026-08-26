---
title: softschema Documentation Value-Proposition Review
description: Review of how the public docs present soft schemas, with proposed descriptions, use cases, and a README structure
author: Claude, with maintainer direction from Joshua Levy
---
# Review: How the Public Docs Present the Value of Soft Schemas

**Date:** 2026-08-14

**Author:** Claude, with maintainer direction from Joshua Levy

**Status:** Review complete; PR #37 contains a focused implementation.
See the status addendum for the disposition of each finding.

**Scope:** Public presentation surfaces only: `README.md`, the opening sections of the
guide, both package READMEs, package metadata, and the GitHub repository description.
No change to the spec, the CLI, the artifact format, or any behavior is proposed.

## Summary

The documentation is accurate, well organized, and unusually disciplined about
ownership: the README summarizes, the guide teaches, the spec is normative, and the
skill routes. The 2026-05-26 docs-design review set that structure up and it held.

The problem is not organization.
It is that the public surfaces describe the mechanism and never state the result.
Every description in the repository is a variation on “validation for Markdown/YAML
artifacts.” A reader who already builds with coding agents can read that sentence and
still not know what changes for them.
The claim that would tell them—that agents given this convention plan and build
differently, and that they do not arrive at it on their own—appears once, in the third
section of the README, inside a hedge.

Four related problems follow from that, and there are three gaps: no domain use cases,
no numbers from the project’s own record, and a lead example that reads like static-site
frontmatter.

The recommendation is to rewrite the top of the README around three things a reader
needs in order: what the convention is, what happens when an agent is told about it, and
what the tools add that the convention alone does not.
Add a section naming where soft schemas fit, using four concrete workflows.
Settle on one description of the project and use it on all six surfaces that currently
disagree.

## Audience and Register

The reader to write for is someone who builds with coding agents regularly and has hit
the problem already: an agent produces a directory of Markdown, the useful values are
spread through prose and tables, and the code that has to consume them is either brittle
or absent. That reader does not need to be convinced that agents are useful, that
structure has value, or that validation is good practice.
Anything spent on those is spent on ground they already stand on.

What that reader needs is a plain description of what the convention is and what it
does, with enough specificity to evaluate it.
Marketing register works against this.
Slogans, two-part contrasts, and phrases like “unreasonably effective at scale” get
discounted on sight, and they are also less informative than the plain sentence they
replace.
“Agents given the convention put consumed values in frontmatter instead of prose
tables” is both plainer and more useful than any compression of it.

Two consequences for the rewrite:

- **Describe the mechanism precisely and let the reader draw the conclusion.** The
  conclusion this project wants a reader to reach is that the convention is small and
  the effect on agent work is large.
  A reader reaches that faster from a four-sentence description of the convention plus
  one accurate sentence about what agents do with it than from any assertion of value.
- **Prefer the concrete noun to the abstraction.** Not “large, complex projects” but the
  actual work: a scraping run that touches forty sources, a performance loop with
  fifty-one experiments, a research project assembling claims from a hundred documents.
  Not “tools that lock it in” but the specific mechanisms: `softschema validate`
  returning structured errors, `compile --check` failing CI on drift, a report
  regenerated from validated artifacts.

## Findings

### 1. The claim about agents is buried and hedged

The README’s third section says the idea is “non-obvious enough that coding agents do
not come up with this approach themselves,” and that given the information and tools,
soft schemas are “unreasonably effective.”
This is the most useful thing the repository says about itself.
It is an empirical observation, it is specific, and it is testable by any reader in
about ten minutes.

It currently sits below two other sections, and it is wrapped in qualifiers: “The idea
is quite simple, but I’ve found it non-obvious enough that…”. The qualifiers do not make
the claim more credible.
What makes it credible is the paragraph that immediately follows it—the description of
what agents actually do differently—and that paragraph currently stays general,
promising better results on “designing and building complex workflows that mix
structured and unstructured data” where it could name the observable behavior.

### 2. Six presentation surfaces describe the project six different ways

| Surface | Current text |
| --- | --- |
| GitHub repository description | Agentic tooling for blending structured data with documents |
| `README.md` | Soft schemas: gradual, practical validation for Markdown/YAML artifacts that mix prose and structured data—built for humans and coding agents |
| `pyproject.toml` | Soft schema conventions and validation tools for Markdown/YAML artifacts |
| `packages/typescript/package.json` | Soft schema conventions and validation for Markdown/YAML artifacts (TypeScript/Zod) |
| `packages/python/README.md` | (same as root README) |
| `packages/typescript/README.md` | validate and structure Markdown/YAML artifacts with frontmatter contracts |

These are not contradictory, but they are six answers to one question, and all six lead
with the mechanism. A reader arriving from PyPI, from npm, and from GitHub gets a
different first sentence each time, and none of the three tells them what changes if
they adopt it.

### 3. Benefits are written as eligibility criteria

The README’s “When and Why Are Soft Schemas Useful?”
opens with “You should consider using soft schemas if:” followed by three conditions.
The guide’s “When to Use It” opens with “Reach for softschema when all three of these
hold.” Both answer the question “do I qualify?”

That is the right form for the guide, where a reader is deciding whether to adopt.
It is the wrong form for the README, where a reader is deciding whether to keep reading.
The README needs to answer “what does this do for the work I am already doing,” and
eligibility criteria answer a different question.

### 4. There are no domain use cases

The guide’s playbooks are organized by task: adopt an artifact, choose which values to
promote, add validation, validate in CI, migrate.
That organization is right for a guide, and the 2026-05-26 review correctly asked for
it.

What is missing is the other axis: the kinds of work this pattern serves.
The research-loop playbook added in v0.6.1 is the only section organized around a
scenario, and it is the strongest section in the guide for exactly that reason—a reader
recognizes their own situation in it.
Four scenarios are worth naming, drafted below.

### 5. The lead example is the weakest one for this audience

The movie page is a good teaching example: it exercises constrained integers, an enum,
lists of scalars, a list of records, nested objects, and optional fields, all in a
domain that needs no explanation.
It should stay in the guide and remain the example the CLI prints.

But as the first artifact a reader sees, it invites the wrong comparison.
A Markdown file whose frontmatter holds a title, a year, and a rating looks like Jekyll
frontmatter, and the reader’s next thought is that they already have this.
Nothing in the movie example shows a consumer, a contract that tightened over time, or a
report that cannot drift, which are the parts that distinguish the pattern.

The experiment artifact from the research-loop playbook does show those things: an
enforced contract, measurements with confidence intervals, a verdict drawn from a fixed
set, and a ledger regenerated from the validated artifacts.
It is the better lead example for the README even though it is the worse teaching
example for the guide.

### 6. The evidence in the repository never reaches the presentation

Two concrete numbers exist in the project’s own record and appear nowhere in the
material a new reader sees:

- The research-loop playbook comes from a real loop of **51 performance experiments**,
  whose entire rig is a model, a recorder, and a regenerated ledger.
- The v0.6.0 notes describe a downstream workload that validates **1,274 artifacts**,
  where the parse-once change moved validation from 171.1s to 69.2s.

The first is evidence that the pattern carries a long-running project.
The second is evidence that real corpora of this size exist and are validated in
production. For the intended reader, either number does more than any adjective in the
current text.

## What the Opening Needs to Establish

Three things, in this order.
Everything else in the README is reference material that follows.

### The convention

A soft schema is structure added to a document as consumers need it, rather than
declared before the data exists.
The artifact is Markdown with YAML frontmatter.
The body carries prose: context, reasoning, caveats, anything a reader needs and no
program reads. The frontmatter carries the values a program does read, under a single
envelope key, named by a contract.
A value moves from prose into frontmatter when something starts reading it, and the
strictness of its validation moves from `soft` to `permissive` to `enforced` as the
shape settles. The body is never parsed for data.

The relationship to a hard schema is close to the relationship between gradual typing
and a fully typed language, and the analogy is worth stating once because it imports a
conclusion this reader already accepts.
TypeScript did not require rewriting a JavaScript codebase before types could pay for
themselves; annotations accrued where they were worth adding.
The correspondence is nearly exact: prose is untyped code, frontmatter values are
annotations, the status ladder is `checkJs` through `strict`, a contract is an
interface, and the compiled JSON Schema is the declaration file that lets another
language consume the same contract.

The description above is around ninety words.
That length is itself part of the point, and the README should present it in a form a
reader can copy into a prompt, because doing so is the fastest way to check the claim in
the next section.

### What happens when an agent is told about it

State it as the observation it is, with the observable behavior named:

> Coding agents do not propose this pattern on their own.
> Told about it, they apply it to the artifacts they write: consumed values go into
> frontmatter under a contract instead of into a Markdown table in the body, and the
> prose stays for what prose is good at.
> On work that runs over many sessions and many files, that difference compounds,
> because the artifacts an earlier session produced remain readable by code rather than
> needing to be re-derived.

The last clause is the part worth being explicit about, and the current docs only imply
it. The reason this matters more for agents than for humans is that an agent’s working
memory ends with the session while the artifacts persist.
A directory of prose is context an agent must re-read and re-interpret; a directory of
validated artifacts is data it can query.
That is the mechanism behind the claim, and stating the mechanism is more convincing
than stating the claim.

### What the tools add

A convention described in a prompt lasts one session and holds only as well as the
agent’s attention. The packages make it durable, and each mechanism is worth naming
concretely rather than gesturing at:

- `softschema validate` returns structural and semantic results separately as JSON,
  which is directly usable in an agent’s feedback loop.
  A validation failure named in JSON is actionable in a way that “your output was wrong”
  is not.
- `softschema compile --check` fails CI when a committed schema drifts from its source
  model, so the contract cannot quietly diverge from what the artifacts are validated
  against.
- `softschema generate --check` keeps derived tables in a document a projection of the
  schema, so a runbook cannot disagree with the contract it documents.
- Reports built by reading validated artifacts are views rather than documents, so a
  roll-up cannot report something the record does not contain.
- The same contract validates in Python and in TypeScript, at exact parity, so the
  choice of ecosystem is not a commitment.
  The spec is language-neutral; the two implementations share commands, exit classes,
  result meaning, and `schema_sha256`, and release together under one version.

The bootstrap belongs in this section rather than in the install instructions, because
it is unusually short and is itself an argument: telling an agent to run
`uvx softschema@latest --help` and follow the instructions is enough for it to install
the skill, read the brief, and start producing conforming artifacts.
Nothing is installed by the user first.

## Candidate Descriptions

One description should be chosen and used on all six surfaces from finding 2, adjusted
only for length. All of these are descriptive rather than promotional, per the register
decision above.

**Longer form, for the README and the guide lede:**

1. Markdown artifacts whose frontmatter carries the values code reads, validated against
   a named contract, while the body stays prose.
   Structure is added per field, as consumers need it.
2. A convention and validator for documents that mix prose with the structured values a
   program consumes: promote a value into frontmatter when something reads it, and
   tighten validation as the shape settles.

**Shorter form, for package metadata and the repository description:**

3. Gradual schemas for Markdown and YAML artifacts: values move into validated
   frontmatter as consumers need them.
   Python and TypeScript.
4. Add structure to agent-written documents one field at a time, and validate it at the
   boundary. Python/Pydantic and TypeScript/Zod.

**Where the agent claim goes.** It should not be compressed into the description.
It is a paragraph, not a phrase, and it needs the mechanism from the previous section to
carry it. Putting it in a package description would turn an observation into a boast.
The README, the guide, and any post about the project are the right places for it,
stated at full length.

**On “unreasonably effective.”** The phrase is doing real work in the current README and
has a useful lineage, but it asserts a conclusion rather than describing what happens.
If it stays, it should stay as a section heading with the observation underneath it,
never as the description of the project.
The plainer statement—that agents do not propose the pattern and readily use it once
told—is stronger because a reader can check it.

## Draft: Where Soft Schemas Fit

A README section naming four kinds of work.
Each entry describes what goes in frontmatter and what stays prose, since that is the
decision a reader is trying to evaluate.

- **Scraping and harmonization across sources.** Many sources with inconsistent shapes
  converging on one record.
  Each source’s output is an artifact: the harmonized record in frontmatter under one
  contract, the provenance and the per-source cleanup decisions in prose.
  The contract starts permissive and tightens as sources normalize, so an odd source is
  documented in the artifact rather than handled by a special case in code, and
  aggregation reads only validated values.

- **Research loops.** Any process that proposes, measures, and decides repeatedly:
  performance work, prompt tuning against an eval, comparing libraries.
  Measurements, intervals, and a verdict from a fixed set in frontmatter; the hypothesis
  and the interpretation in prose.
  The ledger is regenerated from validated artifacts, so refuted hypotheses stay
  queryable instead of being lost in session notes, and an agent resuming months later
  reads what was tried and why it was dropped without re-running it.
  The guide’s playbook covers this in full.

- **Research projects assembling many sources.** A literature review, a market scan, a
  diligence process. Each source is an artifact carrying citation, date, extracted
  claims, and confidence in frontmatter, with the analysis in prose.
  Bibliographies and claim tables are regenerated views rather than hand-maintained
  lists, which is what makes “systematic” a property that is checked rather than a
  property the agent is asked to maintain.

- **Application data with a long tail.** Content a UI renders, where some fields are
  consumed by components and many are not yet.
  The consumed fields are validated with the same Zod schema the application imports;
  everything else rides along in prose or as unvalidated YAML until a component needs
  it. A new field does not wait for a migration, and a field that becomes load-bearing
  gets a contract at that point.

The generalization worth stating after the list: artifacts that pass between steps of a
pipeline, records that accumulate over time, and content that feeds code.
All three are cases where the right structure is not knowable at the start but matters
increasingly as the work scales.

## README Structure

Current order: what it is, quick start, what soft schemas are, how they work, when and
why useful, research-loop example, artifact shape, validate, install, library, skill,
two implementations, further reading.

Proposed order:

1. **Description.** One of the longer-form candidates above.
2. **The convention.** The ninety-word description, in a form that can be copied into a
   prompt.
3. **What agents do with it.** The observation, the mechanism behind it, and the
   bootstrap sentence.
4. **Where soft schemas fit.** The four workflows.
5. **An artifact.** The experiment record, annotated to show which values a consumer
   reads.
6. **Try it.** The existing quick start, with the tell-an-agent bootstrap as the first
   path rather than a later section.
7. **The rest**, largely as it stands: validate, install, library use, skill, the two
   implementations, further reading.

This keeps the README a subset of the guide, as `AGENTS.md` requires.
Two structural consequences: “When and Why Are Soft Schemas Useful?”
dissolves, since its eligibility criteria already exist in the guide and its slot is
taken by the workflows section; and the movie example moves out of the README’s lead
position while remaining the guide’s teaching example and the CLI’s bundled example.

An alternative worth considering is opening with the artifact instead of the
description, then explaining.
It suits the audience, but it delays the agent claim past the first screen, and the
claim is the part a reader cannot get anywhere else.

## Propagation

A chosen description needs to reach the six surfaces in finding 2.
`skills/softschema/SKILL.md` is deliberately excluded: its description is a routing
trigger for agents matching a task, not a description of the project, and it should stay
functional.

The guide’s opening sentence should match the README’s description so that a reader who
follows the link is not re-oriented.

## Recommended Sequence

1. Choose the description from the candidates and settle the register question above.
2. Rewrite the top of the README: description, convention, agent observation, workflows.
3. Add the experiment artifact as the README’s lead example, with a note that the movie
   example in the guide is the fuller teaching case.
4. Add one of the two numbers from finding 6 to the agent section.
5. Propagate the description to the five other surfaces.
6. Update the guide’s lede to match, leaving its playbooks and eligibility criteria as
   they are.
7. Run `make format` and `make lint-check`; both READMEs and the guide are bundled
   package resources, so the change ships with the next release.

Because the README and guide are bundled into the wheel and the npm tarball, this is a
docs-only patch release under the same rule that produced v0.6.1.

## What Not to Change

- **The terminology discipline.** “Soft schemas” for the practice, lowercase
  “softschema” for this spec, CLI, and packages.
  It is applied consistently across the spec, guide, and README, and it is one of the
  reasons the docs read as a considered project.
- **The document ownership model** from the 2026-05-26 review: README summarizes, guide
  teaches, spec is normative, package designs are implementer references, skill routes.
  This proposal changes what the README leads with, not what it owns.
- **The spec’s register.** It is normative and should stay free of motivation and
  persuasion.
- **The guide’s playbook organization.** The workflows section proposed here is a README
  addition; the guide’s task-based playbooks are correct for a reader who has already
  decided to adopt.
- **`SKILL.md`’s functional description.** Skills are routed by task match.

## Status Addendum

**Date:** 2026-08-14

PR #37 implements the findings where they improve the public explanation and records the
two places where the current docs already address the concern:

1. **Fixed: surface the agent behavior.** The README now explains the failure mode,
   gives the authoritative-YAML rule, and names the workflows that follow from it.
   The guide expands that rule into an agent playbook.
2. **Fixed for versioned surfaces: align descriptions.** The root README, guide, package
   READMEs, `pyproject.toml`, and npm metadata now share the same present-state
   description at appropriate lengths.
   The GitHub repository description is external to this PR and can be updated after the
   wording merges.
3. **Fixed: describe outcomes instead of eligibility.** The README uses explicit
   capabilities and concrete workflow shapes instead of an eligibility list.
   The guide retains the adoption criteria, where they help a reader make a decision.
4. **Fixed: add workflow examples.** The README summarizes four shapes, and the guide
   owns the fuller explanations, including what belongs in frontmatter, what remains
   prose, and which consumer reads the payload.
5. **Rebutted: replace the movie example.** The research-loop scenario already appears
   before the movie artifact and is the README’s substantive use case.
   The movie remains the compact, copyable format and CLI example because it exercises
   more schema shapes without domain setup.
6. **Rebutted: add more numerical evidence.** The 51-experiment source is already named
   in the README and guide.
   The 1,274-artifact benchmark measures validator performance, not the effect of the
   authoring convention on agent workflows, so adding it here would weaken the
   explanation rather than support it.

### Reconciliation on 2026-08-25

Since the original review, `main` has added the `pure-yaml` artifact profile, checked
enforcement for composed and dependent schemas, stable structural error categories, and
the research and specification material behind those behaviors.
These changes refine validation after an artifact reaches a boundary.
They do not replace the authoring rule or explain why an agent should use it while
designing a workflow.

Maintainer feedback on the rebased draft identified a remaining scope error in the
original review: it treated gradual promotion from Markdown prose into frontmatter as
the center of the pattern.
softschema also supports `pure-yaml`, and contract maturity is independent of the
artifact profile. A schema can gain fields and constraints, move from `soft` through
`permissive` to `enforced`, and converge on a database or API import boundary without
any Markdown change or Markdown body.

The rebased PR therefore retains the original public-surface scope:

- The README explains gradual data modeling, the independent profile and status choices,
  and the shared boundary used by agents and software.
- The guide covers `pure-yaml` record collections, schema refinement, database and API
  staging, optional Markdown context, and a seven-step agent playbook.
  The repair step now points to v0.7’s stable `code` and `path` fields and the
  `property` field on missing- and undeclared-property records.
- The package READMEs and package metadata use the same present-state description.
- The installed skill teaches agents that Markdown is optional and schema maturity can
  advance without changing the artifact profile.
- This review remains the dated decision record; the newer composed-schema material
  remains in the spec, guide’s advanced playbook, and research brief.

The PR still changes documentation and package descriptions only.
It does not change the artifact format, API, validation behavior, or the v0.7 support
matrix.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
