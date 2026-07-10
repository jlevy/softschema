---
type: is
id: is-01ksrxxp80s58wf28t07729jec
title: Wrap CLI _load_model sys.path mutation in cleanup context manager
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T03:54:50.495Z
updated_at: 2026-07-10T03:49:07.901Z
closed_at: 2026-05-29T03:55:22.100Z
close_reason: cli._load_model now uses a _cwd_on_path() contextmanager (Generator[None]) that removes the cwd entry when it added it. Tests pass.
---
cli._load_model inserted Path.cwd() into sys.path without removing it, accumulating duplicates in test harnesses that call main() many times. Replace with a contextmanager _cwd_on_path() that removes the entry on exit when it added it. Use Generator[None] annotation per basedpyright's @contextmanager rule.
