---
type: is
id: is-01ksejcv8dd7h5xb721rh3gn3d
title: Name the SHA-256 hash field in python design doc
kind: task
status: closed
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-25T03:20:59.916Z
updated_at: 2026-05-25T03:23:44.268Z
closed_at: 2026-05-25T03:23:44.267Z
close_reason: "Design doc now names x-softschema fields: contract, generated_from, softschema_format_version, schema_sha256."
---
docs/softschema-python-design.md claims 'a deterministic SHA-256 hash over canonical JSON' but does not name the field where it lives in the emitted YAML. Add the field name (e.g. x-softschema.hash) or remove the claim.
