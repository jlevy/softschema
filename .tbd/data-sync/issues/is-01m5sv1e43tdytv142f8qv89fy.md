---
type: is
id: is-01m5sv1e43tdytv142f8qv89fy
title: "Upstream to tbd: the generated npx get-tbd fallback pins only the top-level package (PR #64 D2)"
kind: task
status: open
priority: 2
version: 3
labels:
  - upstream
dependencies: []
parent_id: is-01m5v4505x0s8nc898036ey4wh
created_at: 2026-10-25T15:32:03.843Z
updated_at: 2026-10-26T03:32:24.284Z
---
PR #64 review D, finding D2 (Medium): https://github.com/jlevy/softschema/pull/64#pullrequestreview-5642133204. Deferred upstream in round 2.

When no local `tbd` can read the repository, the generated session hooks fall back to `npx --yes "get-tbd@$configured_fallback_version"`. That pins only the top-level package. `get-tbd` ships no `npm-shrinkwrap.json`, so on every cold cache `npx` resolves its transitive tree (67 packages at review time) to the newest in-range versions and runs their lifecycle scripts, with the session's `GH_TOKEN` in the environment. This bypasses the 14-day cool-off for that tree. Review D found no live exposure (nothing under 14 days old, no install scripts), so the risk is the next compromised in-range release.

Locations at main 8085986, all marked "Installed by: tbd setup --auto":

- `.claude/scripts/tbd-session.sh:67` and `.codex/tbd-session.sh:67`
- `.claude/hooks/tbd-closing-reminder.sh:45` and `.codex/tbd-closing-reminder.sh:45`

Fix upstream in tbd (https://github.com/jlevy/tbd), not here, since `tbd setup` regenerates these files. Either:

- (a) publish `get-tbd` with an `npm-shrinkwrap.json`, or bundle its dependencies; or
- (b) have the generated launcher run `NPM_CONFIG_IGNORE_SCRIPTS=true NPM_CONFIG_BEFORE=<now-14d> npx --yes ...`.

Then run `tbd setup --auto` here after the tbd release that carries the fix, and close this bead with that commit.
