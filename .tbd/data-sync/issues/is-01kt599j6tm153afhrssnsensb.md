---
type: is
id: is-01kt599j6tm153afhrssnsensb
title: "errors.ts: pyRepr renders whole-number floats without trailing .0"
kind: bug
status: open
priority: 3
version: 4
spec_path: docs/project/specs/active/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - parity
  - typescript
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-02T23:04:27.097Z
updated_at: 2026-06-10T21:43:12.806Z
---
pyRepr uses String(2.0)=\"2\" but Python repr(2.0)=\"2.0\". Any whole-valued float bound/value in a message diverges. Partly inherent: JS loses int/float distinction after parse; needs int/float tracking through YAML/JSON parse to fully close.

## Notes

EVALUATED + DOCUMENTED (not fixed). A simple schema/Zod-type-aware fix cannot match Python: Python renders by the parsed value's runtime float-ness (source token), not the declared type, so a type-aware renderer diverges the other way (int 5 in a number field -> '5', not '5.0'). Exact parity requires preserving YAML/JSON source tokens through parse -> serialize -> ajv-unwrap -> error-resolution for BOTH instance values and schema bounds (~150 lines, hot-path risk). Everything else is proven byte-identical (parity probe across all keywords + golden 14/14 on both CLIs), so this lone edge case is documented rather than fixed. Golden corpus normalizes error-case values to integers / non-whole floats (tests/golden/README.md) so the divergence cannot hide. Revisit only if whole-number-float instance values or schema bounds become common in real artifacts.
