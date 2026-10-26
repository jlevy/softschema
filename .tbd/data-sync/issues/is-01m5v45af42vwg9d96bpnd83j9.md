---
type: is
id: is-01m5v45af42vwg9d96bpnd83j9
title: "Metaproc: move to softschema 0.9 and retire its own repair and conform copies"
kind: task
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4505x0s8nc898036ey4wh
created_at: 2026-10-26T03:30:42.787Z
updated_at: 2026-10-26T03:30:42.787Z
---
Metaproc (https://github.com/jlevy/metaproc) is the downstream consumer two softschema plans coordinate with, and it has not moved yet. Checked 2026-10-26 at its default branch:

- `pyproject.toml:28` pins `softschema>=0.8.0,<0.9`, which excludes 0.9.0.
- It still carries its own `src/metaproc/engine/yaml_repair.py` and `src/metaproc/engine/schema_conform.py` (with `tests/test_yaml_repair.py` and `tests/test_schema_conform.py`).

What the plans ask of the Metaproc change:

1. From docs/project/specs/done/plan-2026-08-29-validate-repair.md (Rollout Plan, step 2): delete `engine/yaml_repair.py` and the per-artifact half of `engine/schema_conform.py`, retire the `metaproc softschema repair` subcommand, and repoint `repair_declared_outputs` and `conform_declared_outputs` at softschema's `repair_and_validate_artifact`. Bump the pin in the same change, so Metaproc never runs without repair.
2. From docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md: widen the released dependency range to admit 0.9 (for example `softschema>=0.9.0,<0.10`). Its serializer must forward both complete layer records, including `execution` and structural skip reasons. Source integration through native dataclass forwarding already passed 96 Metaproc tests against softschema `b494f72`. Historical reports without `execution` must stay readable.

Before bumping, read the CHANGELOG `## v0.9.0` Compatibility section: 0.9.0 newly rejects raw characters outside YAML 1.2 c-printable, line separators, and lone carriage returns, and the Python layer-result constructors now require `execution`.

The work lands in the Metaproc repository. Close this bead with the Metaproc commit or PR that merged it.
