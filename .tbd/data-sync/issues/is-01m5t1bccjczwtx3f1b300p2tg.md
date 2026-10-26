---
type: is
id: is-01m5t1bccjczwtx3f1b300p2tg
title: "PR #59 review G: one strict resource-identity grammar in both runtimes"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T17:22:21.201Z
updated_at: 2026-10-25T20:42:29.313Z
closed_at: 2026-10-25T20:42:29.313Z
close_reason: Review G fixed in 0135d56 (+ merge e0f6c75 of main 5b32389, + pin 20f9421), pushed to enforcement-clarity. One strict identity grammar (softschema/_identity.py, identity.ts) shared by validate (root, nested, supplied resource id/key) and compile --schema-id. Reviewer fuzz 1444x6 = 8664 cases, 0 diffs (694 at 725fa53); extended 2459x12 = 29508 cases, 3 diffs all in the listed relative-id-under-urn/tag class (one pinned). pytest 532/1 skipped, -m slow 21, PURE_YAML 532/1 skipped, lint pass, bun test 447, typecheck/lint:ci/build/publint clean, goldens py 90 / ts 85 / ts-bun 90, cross-impl OK; CI 40231595337 19/19. Reply https://github.com/jlevy/softschema/pull/59#issuecomment-6402989041
resolution: null
duplicate_of: null
---
Review G (follow-up, round 5) on https://github.com/jlevy/softschema/pull/59#pullrequestreview-5644285034. Coordinator decision: replace the ad hoc root/urn checks with one strict identity grammar implemented identically in Python and TypeScript, shared by validate (root, nested, supplied resources) and compile --schema-id; no urlparse/new URL in the decision. Covers G1 (root absolute test differs: urlparse vs regex), G2 (%7E urn accepted, Ajv cannot resolve), G3 (compile writes fragment ids), G4 (non-normalized/malformed resource identities), G5 (tag: why text), Qodo r4371485450 (fixed) and r4371456789 (rebut).
