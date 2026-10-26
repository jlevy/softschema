---
type: is
id: is-01m5v8833z5s4p9s8svsdja37w
title: doctor recommends softschema under uvx/npx, which is not on the caller's PATH
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@vm
labels:
  - release-0.9.1
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-26T04:42:07.871Z
updated_at: 2026-10-26T05:16:47.037Z
started_at: 2026-10-26T04:42:12.699Z
closed_at: 2026-10-26T05:16:47.036Z
close_reason: "Fixed in PR https://github.com/jlevy/softschema/pull/74 (head bd1a73d1e01242cd59e974fba0600e360148f7b8; commits 41533dc, bd1a73d, both SSH-signed). Both runtimes skip runner caches in PATH lookup (uv bucket under a CACHEDIR.TAG root; npm _npx/<hash>/node_modules) and recommend the first available of softschema, the starting runner, uvx, npx. Evidence: real 'uvx --from <built wheel> softschema doctor' -> softschema: no, recommended invocation: uvx softschema@latest; real 'npx -y --package=<packed tgz> softschema doctor' -> recommended invocation: npx -y softschema@latest. Python and Node doctor JSON/text identical under the same injected PATH. Local gate: lint --check passed; pytest 615 passed/1 skipped; TS typecheck, lint:ci, bun test --coverage 525 pass, build ok; goldens py 102, ts 97, ts-bun 102 passed; cross-impl-diff parity OK. CI 19/19 pass on bd1a73d. Qodo's 3 findings fixed in bd1a73d, replied to, threads resolved; no new findings on bd1a73d."
resolution: null
duplicate_of: null
---
Run through an ephemeral runner (uvx softschema@latest, npx -y softschema@latest), doctor found the runner's throwaway softschema on the PATH the runner prepended (uv archive-v0/<id>/bin, npm _npx/<hash>/node_modules/.bin) and printed 'recommended invocation: softschema'. The caller's shell has no softschema, so an agent following the skill's advice fails. Fix in both runtimes: skip ephemeral runner caches in PATH lookup, recommend the runner form (uvx softschema@latest / npx -y softschema@latest) when the running softschema lives in one; an installed softschema still wins.
