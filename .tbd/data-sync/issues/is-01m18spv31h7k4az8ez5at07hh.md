---
type: is
id: is-01m18spv31h7k4az8ez5at07hh
title: "PR #52 review F4: Node prefixes softschema's own delimiter diagnostic, Python does not"
kind: bug
status: closed
priority: 1
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m18sptr5svfcbcvb2mxcmpkb
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:38:55.457Z
updated_at: 2026-08-30T07:55:15.867Z
closed_at: 2026-08-30T07:55:15.867Z
close_reason: "Fixed on claude/senior-engineering-review-h24e5m (b70010a, 12ef4ed). F2 turned out to be a live defect, not latent: --repair silently skipped any artifact whose closing fence was the file's last byte. Covered by 3 Python + 3 TypeScript cases, each verified to fail pre-fix, plus a golden journey on all three runtimes."
resolution: null
duplicate_of: null
---
Python: 'softschema validate: Delimiter `---` for end of frontmatter not found: `f.md`'
Node:   'softschema validate: Error parsing YAML metadata: Delimiter `---` for end of frontmatter not found: `f.md`'

The prefix comes from packages/typescript/src/cli.ts:433, whose comment justifies it as 'mirroring the Python CLI's FmFormatError handling'. Python has no such prefix; the string appears nowhere in the Python package. The comment is stale.

Unlike the engine-specific YAML errors the golden corpus rightly elides, this is softschema's own message, identical on both sides underneath. cross-impl-diff.sh compares machine JSON and cannot see it.

Fix: drop the prefix so both CLIs emit the same line; correct the comment. Then F3 can assert the full line.
