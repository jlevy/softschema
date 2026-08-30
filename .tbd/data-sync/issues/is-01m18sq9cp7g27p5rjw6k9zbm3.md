---
type: is
id: is-01m18sq9cp7g27p5rjw6k9zbm3
title: "PR #52 review F6: TypeScript parseAfterRepair swallows every throw, unlike Python and unlike its own sibling"
kind: bug
status: closed
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:39:10.102Z
updated_at: 2026-08-30T07:55:15.872Z
closed_at: 2026-08-30T07:55:15.872Z
close_reason: "Fixed on claude/senior-engineering-review-h24e5m (b70010a, 12ef4ed). F2 turned out to be a live defect, not latent: --repair silently skipped any artifact whose closing fence was the file's last byte. Covered by 3 Python + 3 TypeScript cases, each verified to fail pre-fix, plus a golden journey on all three runtimes."
resolution: null
duplicate_of: null
---
packages/typescript/src/cli.ts parseAfterRepair catches everything and converts non-Errors via new Error(String(error)). Python catches only PortableInputError.

The sibling reparse() in repairValidate.ts deliberately narrows to PortableInputError | YamlParseError and rethrows the rest, with a comment that anything else 'is a programming error and must crash rather than be quietly reclassified - mirroring Python's except PortableInputError'. parseAfterRepair breaks that invariant.

PR #52 makes the consequence worse: before, a swallowed internal error produced a vague 'no YAML frontmatter'; now it is reported as 'the document could not be read: <internal message>', presenting an implementation bug to the user as a defect in their file.

Fix: narrow the catch to PortableInputError | YamlParseError to match its sibling.
