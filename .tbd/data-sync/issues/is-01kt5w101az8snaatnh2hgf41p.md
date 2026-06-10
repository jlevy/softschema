---
type: is
id: is-01kt5w101az8snaatnh2hgf41p
title: Apply common-doc-guidelines across docs + code comments (em dashes, and/+/&, headings)
kind: task
status: closed
priority: 2
version: 2
labels:
  - docs
dependencies: []
created_at: 2026-06-03T04:31:49.285Z
updated_at: 2026-06-03T04:49:11.394Z
closed_at: 2026-06-03T04:49:11.381Z
close_reason: "Done: removed all em dashes from doc prose + code comments (146 docs + ~18 comments), +/& -> and, Title Case H1/H2, field_list generator uses ':' not em dash. Only remaining em dash is the tbd-generated AGENTS.md integration block (upstream, tracked separately)."
---
Rigorous pass applying tbd common-doc-guidelines: remove em dashes (user reads them as overuse; prefer ./,/:/; ), write 'and' not +/& in prose, Title Case H1/H2, no sweeping language, present-state framing. Scope: all tracked doc markdown + code comments; exclude generated skill mirrors (regenerate from source), golden expected-output blocks, and example fixture data (spirited-away.md). flowmark preserves em dashes so fixes stick.
