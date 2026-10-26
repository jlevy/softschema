---
type: is
id: is-01m5sv1eeh21s6jd2m0t9neh1n
title: "Owner: delete or salvage the 3 stale branches with unmerged work (PR #64 D3)"
kind: task
status: open
priority: 2
version: 4
labels: []
dependencies: []
parent_id: is-01m5v4505x0s8nc898036ey4wh
created_at: 2026-10-25T15:32:04.177Z
updated_at: 2026-10-26T03:31:59.589Z
---
PR #64 review D, finding D3(a): https://github.com/jlevy/softschema/pull/64#pullrequestreview-5642133204. Stale remote branches keep content that main has since cleaned up publicly browsable. The coordinator deleted the fully merged ones. The owner accepted D3(b), the `tbd-sync` history, and D3(c), the old 0.8.x sdists.

Three branches with unmerged commits remain. `git ls-remote --heads origin` on 2026-10-26 lists only these besides `main` and `tbd-sync`, and none has an open PR:

- `claude/c-first-on-vendored` (tip 55ffbac, 2026-10-24): 21 commits ahead of main, 30 behind. No PR. It merges earlier revisions of #59, #60, and #62, all of which have since been squash-merged, so it probably holds nothing unshipped. Confirm with a diff before deleting.
- `codex/softschema-hardening` (tip 827c59b, 2026-07-10): 25 ahead, 176 behind. Its PR #20 was closed unmerged. The work shipped in reduced form through plan-2026-07-11-minimal-softschema-hardening.md (done).
- `codex/softschema-hardening-plan` (tip 098b5ec, 2026-07-09): 1 commit ahead, which adds `docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md`.

Before deleting the two `codex/` branches: those branches hold the only copy of `plan-2026-07-09-softschema-hardening-and-conformance.md`, and 115 closed beads still name it as their `spec_path`. Decide whether to keep it, for example by copying it into `docs/project/specs/archive/` on main after the same private-reference sweep #64 applied to the tree, or to accept the dangling links.

Fix (owner decision, since it destroys unmerged work): delete each branch with `git push origin --delete <branch>`, or merge what is worth keeping first.
