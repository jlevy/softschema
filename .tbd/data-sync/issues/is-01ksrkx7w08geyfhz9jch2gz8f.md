---
type: is
id: is-01ksrkx7w08geyfhz9jch2gz8f
title: Decide gzip-on-read intent and document in spec
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T00:59:50.015Z
updated_at: 2026-05-29T01:22:01.993Z
closed_at: 2026-05-29T01:22:01.993Z
close_reason: "Decision: keep gzip-on-read. Documented as optional spec feature in docs/softschema-spec.md (#Gzipped artifacts section under Artifact Profiles) and as a transport-level convenience in docs/softschema-python-design.md (#Gzipped artifacts under Validation)."
---
Upstream consumer review (2026-05-28) flagged a gap: the PR description says gzip-on-read was dropped, but validate.py:482-492 still has gzip handling and test_core.py:165 (test_validate_artifact_accepts_gzipped_markdown) exercises it. At least one downstream consumer writes `.md.gz` outputs from its pipelines and validates them via validate_artifact, so the behavior is load-bearing for at least one consumer. Decide: keep, drop, or accident. If keeping, document in docs/softschema-spec.md (artifact format level, the .gz extension belongs in the format rules) and add a short note in docs/softschema-python-design.md about the implementation. If dropping, remove the code path in validate.py plus the test, and note the removal in release notes.
