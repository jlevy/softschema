---
type: is
id: is-01m5rtchc67w34gv4cmv1xznkw
title: "PR #60 A3: pinned surrogate/tab cases and json_lone_surrogate vector describe pure ruamel only"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5y30vn078tgerprth9hg
hold: null
hold_until: null
created_at: 2026-10-25T06:01:24.614Z
updated_at: 2026-10-25T06:29:31.887Z
started_at: 2026-10-25T06:01:45.792Z
closed_at: 2026-10-25T06:29:31.886Z
close_reason: "fixed in c447283 (#60): three pinned errors skip under the C extension with a reason; the vector case is settled by #62's pure fallback"
resolution: null
duplicate_of: null
---
Low. PR #60, review A: https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641761087. test_json_fast_path.py:194,:197,:202; tests/vectors/hardening.yaml:75. Fail with ruamel.yaml.clib installed. Fix: skip under the C extension with a reason; correct the PR body Not Verified note. The vector case is settled by #62 (C-first re-reads with pure).
