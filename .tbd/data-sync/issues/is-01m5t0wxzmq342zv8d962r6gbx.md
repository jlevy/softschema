---
type: is
id: is-01m5t0wxzmq342zv8d962r6gbx
title: "PR #62 E2: the reason given for SOFTSCHEMA_REQUIRE_JSON_PATH is no longer true on this layer"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0wx1zedsf15d8pn6cwkqx
created_at: 2026-10-25T17:14:27.699Z
updated_at: 2026-10-25T17:23:39.272Z
closed_at: 2026-10-25T17:23:39.272Z
close_reason: "fixed in 9f6cb2b: build-job comment, REQUIRE_JSON_PATH docstring and installed-release test say the variable guards against an unchecked ruamel release skipping the two slow comparisons on this layer"
resolution: null
duplicate_of: null
---
Low. ci.yml:138-139; test_json_fast_path.py:37-43, :644-645. On #62 _json_path_enabled ignores the parser; reword to 'an unchecked ruamel release would skip the two slow comparisons' or fold into E1's switch. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5644280692
