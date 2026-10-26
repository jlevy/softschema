---
type: is
id: is-01m5t0wxhjpfqfag3mh6esvdzp
title: "PR #62 E1: without the C extension the build job skips every C-first test and stays green"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0wx1zedsf15d8pn6cwkqx
created_at: 2026-10-25T17:14:27.249Z
updated_at: 2026-10-25T17:23:39.015Z
closed_at: 2026-10-25T17:23:39.015Z
close_reason: "fixed in 9f6cb2b: SOFTSCHEMA_REQUIRE_C_PARSER=1 in the build job; requires_c does not skip under it; test_ci_requires_the_checked_c_parser asserts _C_PARSER_AVAILABLE; verified failing with _ruamel_yaml blocked"
resolution: null
duplicate_of: null
---
Low. test_c_parser.py:48-52 requires_c; ci.yml:137-140. Add a CI-only SOFTSCHEMA_REQUIRE_C_PARSER switch mirroring SOFTSCHEMA_REQUIRE_JSON_PATH; under it requires_c does not skip and a default-tier test asserts _C_PARSER_AVAILABLE. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5644280692
