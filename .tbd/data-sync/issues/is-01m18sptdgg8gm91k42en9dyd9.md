---
type: is
id: is-01m18sptdgg8gm91k42en9dyd9
title: "PR #52 review F2: opens_frontmatter_fence disagrees with the reader when the first line has no trailing newline"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:38:54.768Z
updated_at: 2026-08-30T07:55:15.861Z
closed_at: 2026-08-30T07:55:15.860Z
close_reason: "Fixed on claude/senior-engineering-review-h24e5m (b70010a, 12ef4ed). F2 turned out to be a live defect, not latent: --repair silently skipped any artifact whose closing fence was the file's last byte. Covered by 3 Python + 3 TypeScript cases, each verified to fail pre-fix, plus a golden journey on all three runtimes."
resolution: null
duplicate_of: null
---
_line_end returns None when there is no newline in the text, so opens_frontmatter_fence('---') is False while read_frontmatter_doc treats it as an opened, unterminated fence and raises. Same in TypeScript: lineEnd uses indexOf('\\n'), parseFrontmatterText uses split(/\\r?\\n/) which keeps a final unterminated line.

The docstring claims 'exactly as read_frontmatter_doc treats it'. That is false for this input, in both runtimes.

Not reachable as a wrong verdict today (both CLIs still exit 2, because the pure-yaml fallback needs a mapping with a root softschema: key and a single-line '---' cannot be one), so the correct verdict survives on the fallback rather than on the helper. Same shape as the bug being fixed, and 'no trailing newline' is exactly what a truncated write produces.

Fix: treat EOF as a line end in the helper; add the case to both unit suites.

Files: packages/python/src/softschema/_portable.py, packages/typescript/src/portable.ts
