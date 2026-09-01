---
type: is
id: is-01m184tjxg9zgfkppdsm13fcsh
title: Shared vectors and unit cases for the unterminated frontmatter fence
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies:
  - type: blocks
    target: is-01m184vk6ayjkkpjp9d7ncgnfh
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:33:58.064Z
updated_at: 2026-08-30T01:42:41.887Z
closed_at: 2026-08-30T01:42:41.887Z
close_reason: "Added regression coverage in both languages: packages/python/tests/test_cli.py (6 cases) and packages/typescript/test/repair-profile-detection.test.ts (5 cases). Each covers the unterminated fence on both paths, the unparsable-frontmatter reason, and the two controls that prove the narrowing did not go too far (a genuinely fenceless document is still pure-yaml; a *.yaml file with a --- document-start marker is still pure-yaml on the suffix rule). Verified they fail against the pre-fix code: Python 2 failures, TypeScript 1."
resolution: null
duplicate_of: null
---
Pin the fixed behavior at the unit layer in both packages, so the divergence cannot
return quietly.

Cases, each on a document not named `*.yaml`:

1. Opening `---` fence, no closing fence, root carries a `softschema:` block. Profile
   detection must return frontmatter-md, and both `validate` and `--check-repair` must
   report the frontmatter delimiter error rather than a verdict.
2. Control: the same document with its closing `---` present validates normally under
   both paths.
3. Control: a genuinely fenceless document whose root carries `softschema:` is still
   detected as pure-yaml. This is the rule the fix must not break.
4. Control: a `*.yaml` file whose first line is an explicit `---` YAML document-start
   marker is still pure-yaml on the suffix rule, unaffected by the fence check.

Cases 3 and 4 matter as much as case 1: the fix narrows what counts as "fenceless", and
these prove it did not narrow too far.

Python: packages/python/tests/. TypeScript: packages/typescript/src/ or test/.
Add a `tests/vectors/` section if the case is expressible as shared data rather than
per-language test code.
