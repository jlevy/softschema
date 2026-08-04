---
type: is
id: is-01kz5wz0frm67wy02n14m6nvhy
title: "PR #27: Python raises uncaught RecursionError out of validate_artifact"
kind: bug
status: closed
priority: 0
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wz06084fc4q0badsavagv
created_at: 2026-08-04T08:06:41.912Z
updated_at: 2026-08-04T08:15:38.460Z
closed_at: 2026-08-04T08:15:38.459Z
close_reason: RecursionError now maps to yaml_limit; verified a depth-60 doc parsed 40 frames from the limit returns a structured result.
---
packages/python/src/softschema/_portable.py: removing MAX_DEPTH left Python with no clean stack-overflow path. At depth 1000 validate_artifact raises RecursionError instead of returning yaml_limit. No RecursionError handler exists in the Python package. main returns clean yaml_limit at 64/1000/50000. (PR #27)
