---
type: is
id: is-01ktvqwsay626pt02sc1aq5b52
title: "P2: softschema.schema metadata binding (JSON-Schema-first linkage)"
kind: feature
status: closed
priority: 1
version: 8
spec_path: docs/project/specs/done/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwtf685q8561mhxg2c15b
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T16:22:54.557Z
updated_at: 2026-07-10T03:49:21.682Z
---
Design 5 + 0.2.0 pre-release review (D1/D2/D4): metadata quartet contract/schema/envelope/status. schema: optional recommended pointer, RELATIVE-ONLY in reference CLIs (absolute rejected -> use --schema), resolved from doc dir, bounded to doc-dir+cwd (escape -> schema_missing with bound-naming message). envelope: optional declared envelope key (multi-key artifacts self-describe; declared-but-absent -> envelope_mismatch). Precedence (host over document): --schema/--envelope flag > registry Contract.schema_path/envelope_key (library only) > softschema.schema/envelope metadata > metadata-only/inference. Library validate_artifact/validateArtifact apply the precedence (CLI is a thin wrapper). inspect reports schema+envelope. Unknown-key set: contract/schema/envelope/status. Golden: no-flag validate of self-describing spirited-away; --schema override beats metadata; absolute/escape/missing/non-string rejections; envelope declared-but-absent.
