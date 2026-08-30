---
type: is
id: is-01m184sh0j1sn4vms3y0p3ft8m
title: validate --repair reads an unterminated frontmatter fence as pure-yaml (Python)
kind: bug
status: closed
priority: 0
version: 8
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies:
  - type: blocks
    target: is-01m184t4z0a98z50dphabs947j
  - type: blocks
    target: is-01m184tjxg9zgfkppdsm13fcsh
  - type: blocks
    target: is-01m184tkby56c2s7phxdzm1kq1
  - type: blocks
    target: is-01m184vjqxckqhnfdb28gze3b2
  - type: blocks
    target: is-01m184v3tye1c77f0mmzfr5fnf
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:33:23.346Z
updated_at: 2026-08-30T01:41:21.880Z
closed_at: 2026-08-30T01:41:21.880Z
close_reason: "Fixed: detect_profile/detectProfile now test whether the document opens a frontmatter fence (new opens_frontmatter_fence / opensFrontmatterFence helper) instead of whether split_frontmatter can split it, so an unterminated fence stays frontmatter-md in both languages. The repair path also carries the parse error into the missing-contract reason, so an unreadable frontmatter is named rather than reported as absent. split_frontmatter's false invariant corrected in both docstrings. All suites green: pytest 225, bun 223, golden 68/66/68, cross-impl parity OK."
resolution: null
duplicate_of: null
---
A document that opens frontmatter with `---` and never closes it — exactly what a
truncated agent write produces — gets opposite answers from the two paths:

| Command | Result |
| --- | --- |
| `softschema validate f.md` | exit 2, "Delimiter `---` for end of frontmatter not found" |
| `softschema validate f.md --check-repair` | `outcome: valid`, `profile: pure-yaml` |

The producer is told its artifact is valid; the consumer cannot read the file at all.
That inverts the feature's premise.

## Repro

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

(no trailing `---`). Named `*.md`, so the `*.yaml` suffix rule does not apply.

## Root cause

`_read_artifact` (packages/python/src/softschema/cli.py:348) — the non-repair path —
calls `read_frontmatter_doc`, which raises `PortableInputError` on an unterminated
fence. It commits to frontmatter-md and never reaches the pure-yaml fallback.

`_detect_profile` (packages/python/src/softschema/cli.py:463) — the repair path, which
must not require a successful parse — calls `split_frontmatter`, which returns `None`
for an unterminated fence (_portable.py:217). `None` reads as "fenceless", so detection
falls through to `_yaml_root_or_none`, the leading `---` is consumed as a YAML
document-start marker, the whole file parses, `softschema` is found at the root, and
the profile comes back `pure_yaml`.

## Fix

`_detect_profile` must treat a document whose first line is a `---` fence as
frontmatter-md whether or not that fence is terminated, because that is what the reader
does. The "fenceless document" rule must mean genuinely fenceless — no leading fence —
not "split_frontmatter returned None".

Add a helper alongside `split_frontmatter` that answers only "does this text open a
frontmatter fence?" and consult it in `_detect_profile` before the pure-yaml fallback.
Do not change `split_frontmatter`'s return contract; its repair-region callers depend
on `None` meaning "no region to rewrite".

Note the rule only affects files not named `*.yaml`/`*.yml`: the suffix rule already
returns pure-yaml first, so a legitimate pure-yaml file carrying an explicit `---`
document-start marker is unaffected.

## Acceptance

`validate` and `validate --check-repair` agree that the repro document is unreadable,
and both report the frontmatter delimiter error rather than one of them returning
`valid`.
