---
type: is
id: is-01kz5wzmjjmxk80kt21anx5g2g
title: "PR #26: _SchemaRootNotAMapping defined after first use"
kind: chore
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wzknpm4nrrjjjramv3x5d
created_at: 2026-08-04T08:07:02.482Z
updated_at: 2026-08-04T08:11:19.128Z
closed_at: 2026-08-04T08:11:19.128Z
close_reason: Moved above _build_validator.
---
Used at validate.py:110, defined at :125. Legal but reads backwards. (PR #26)
