---
type: is
id: is-01m5td24m1m7cgccafvvvbrzf5
title: "PR #66 Qodo r4372291104: restored catch fallbacks not checked for JSON (NaN/Infinity -> null, BigInt throws) (https://github.com/jlevy/softschema/pull/66#discussion_r4372291104)"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5tbxx8437j99campa81w7hx
created_at: 2026-10-25T20:47:01.249Z
updated_at: 2026-10-25T20:47:02.892Z
closed_at: 2026-10-25T20:47:02.892Z
close_reason: "fixed in 28db6c2: jsonDefault rejects non-finite/BigInt defaults and catch values with path, Date -> ISO; unit test covers NaN/±Inf/BigInt/Date. dispositions https://github.com/jlevy/softschema/pull/66#issuecomment-6403044947; CI run 40231901121 19/19 at 28db6c2641969adcff1294b84670f8bfe2c4b80c"
resolution: null
duplicate_of: null
---
