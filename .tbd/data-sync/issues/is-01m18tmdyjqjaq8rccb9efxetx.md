---
type: is
id: is-01m18tmdyjqjaq8rccb9efxetx
title: Bump packages/typescript/package.json to 0.8.0
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m18tmekhg694svqeavjs20sd
parent_id: is-01m18tkzqtfq03b9rxp3y9gvde
created_at: 2026-08-30T07:55:05.042Z
updated_at: 2026-10-25T06:13:03.652Z
closed_at: 2026-10-25T06:13:03.652Z
close_reason: "Shipped in v0.8.0: PR #53 (fa2ce47) set packages/typescript/package.json to 0.8.0; npm softschema@0.8.0 published 2026-08-30."
resolution: null
duplicate_of: null
---
It still reads 0.7.0. The Python version derives from the git tag via uv-dynamic-versioning, but the npm publish job aborts on a version mismatch, so this must land before tagging.
