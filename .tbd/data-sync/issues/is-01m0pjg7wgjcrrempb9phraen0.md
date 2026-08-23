---
type: is
id: is-01m0pjg7wgjcrrempb9phraen0
title: Add stable code enum to structural error records
kind: feature
status: open
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-08-23-enforced-composition-closure.md
labels:
  - diagnostics
  - parity
dependencies:
  - type: blocks
    target: is-01m0pjkkgq8r3k9pe3eby7mz3b
  - type: blocks
    target: is-01m0pjkm7kd2kf57ennae999ye
parent_id: is-01m0pjfmt8vxpkcjk8msfa8c32
created_at: 2026-08-23T05:46:39.375Z
updated_at: 2026-08-23T05:48:30.322Z
---
Maintainer direction: consumers must match a softschema-owned category, never an engine keyword.

Add a small closed 'code' enum to every structural error record, computed as a pure function of validator in the shared normalization layer (errors.py, mirrored in errors.ts) beside the message table:
- undeclared_property <- additionalProperties, unevaluatedProperties
- missing_property <- required
- invalid_value <- every other mapped keyword
- unmapped_keyword <- explicit allowlist miss (visible signal to extend the map, never a silent default)

validator keeps reporting the raw JSON Schema keyword (mechanism); code names the category (what the author got wrong). Also add the unevaluatedProperties message template emitting the SAME string as additionalProperties — one category, one code, one message. Today it falls to the generic branch and spills the whole payload into the message.

Documented match surface is kind + code + path; validator/validator_value are diagnostic; message wording may improve in a minor.
