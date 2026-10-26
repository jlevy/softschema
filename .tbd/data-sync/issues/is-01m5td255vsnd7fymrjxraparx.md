---
type: is
id: is-01m5td255vsnd7fymrjxraparx
title: "PR #66 Qodo r4372333328: compile re-invokes default/prefault/catch factories (https://github.com/jlevy/softschema/pull/66#discussion_r4372333328)"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5tbxx8437j99campa81w7hx
created_at: 2026-10-25T20:47:01.819Z
updated_at: 2026-10-25T20:47:03.281Z
closed_at: 2026-10-25T20:47:03.281Z
close_reason: "rebutted: Zod calls default/catch factories per parse (core/schemas.js:2169,2185,2255) and per node during its own generation (2 calls for .describe() on main); reusing Zod's value would lose the NaN check (serializeDefaultValue). Reply https://github.com/jlevy/softschema/pull/66#discussion_r4372343062. dispositions https://github.com/jlevy/softschema/pull/66#issuecomment-6403044947; CI run 40231901121 19/19 at 28db6c2641969adcff1294b84670f8bfe2c4b80c"
resolution: null
duplicate_of: null
---
