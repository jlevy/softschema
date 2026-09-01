---
type: is
id: is-01m184vjqxckqhnfdb28gze3b2
title: Changelog and review-doc updates for the repair fix
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies: []
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:34:30.652Z
updated_at: 2026-08-30T01:53:11.266Z
closed_at: 2026-08-30T01:53:11.266Z
close_reason: "CHANGELOG Unreleased now states that an unterminated frontmatter fence is a frontmatter-md read error on every path including --repair, and records the package description change visible on the PyPI and npm listing pages. Both review docs updated: the e2e review marks Finding 1 resolved with the fix and its coverage, the readiness review clears the release-blocking step. Spec profile-resolution rule 2 disambiguated: a document that *opens* a fence is frontmatter-md whether or not it closes one, and resolution must not depend on the document parsing."
resolution: null
duplicate_of: null
---
Record the fix where a consumer of the release will find it.

- CHANGELOG.md `Unreleased`: the divergence is a defect in unreleased work, so it does
  not need a "Fixed" entry against a shipped version. What does belong there is any
  change in documented behavior the fix introduces — state plainly that a document
  whose frontmatter fence is opened and never closed is a frontmatter-md read error
  under every path including `--repair`, and is not treated as a pure-yaml document.
- Also record the package description change already on the branch and still unlisted
  (both `pyproject.toml` and `packages/typescript/package.json` now read "Gradual
  contracts for YAML data, with optional Markdown context"). That is the text on the
  PyPI and npm listing pages.
- Update docs/project/reviews/review-2026-08-30-validate-repair-e2e.md Finding 1 to
  point at the fix and the regression cases.
- Update docs/project/reviews/review-2026-08-29-softschema-v080-readiness.md: clear the
  release-blocking step once the fix and its cases are green.
- If the spec states or implies how profile detection treats a fence, make sure
  docs/softschema-spec.md agrees with the fixed behavior.
