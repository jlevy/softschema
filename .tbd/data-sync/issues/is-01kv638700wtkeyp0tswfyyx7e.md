---
type: is
id: is-01kv638700wtkeyp0tswfyyx7e
title: "cli.py _compile_cmd: redundant inner try/except duplicates _run_cmd's _USER_ERRORS handling (parity-check message prefix first)"
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
created_at: 2026-06-15T16:53:47.648Z
updated_at: 2026-06-15T17:41:51.403Z
closed_at: 2026-06-15T17:41:51.402Z
close_reason: "Removed the redundant inner try/except in _compile_cmd; the shared _run_cmd boundary reports model-load errors as 'softschema compile: ...' exit 2 (message identical)."
---
