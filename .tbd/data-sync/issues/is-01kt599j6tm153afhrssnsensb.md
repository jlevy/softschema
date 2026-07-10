---
type: is
id: is-01kt599j6tm153afhrssnsensb
title: "errors.ts: pyRepr renders whole-number floats without trailing .0"
kind: bug
status: closed
priority: 3
version: 6
spec_path: docs/project/specs/active/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - parity
  - typescript
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-02T23:04:27.097Z
updated_at: 2026-06-15T21:32:42.711Z
closed_at: 2026-06-15T21:32:42.711Z
close_reason: "Implemented and shipped in v0.2.2 (PR #18). Resolved via the canonical-number rule: whole-valued numbers below 1e21 render without a trailing fraction/exponent; Python's canonical_number normalizes floats to match JS. Byte-identical across impls within the IEEE-754 safe-integer range; non-round >=2^53 documented as out of scope."
---
pyRepr uses String(2.0)=\"2\" but Python repr(2.0)=\"2.0\". Any whole-valued float bound/value in a message diverges. Partly inherent: JS loses int/float distinction after parse; needs int/float tracking through YAML/JSON parse to fully close.

## Notes

v0.2.2 re-evaluation: confirmed in code. normalizeAjvError() receives error.data (instance value) and error.schema (bound) as plain JS numbers; YAML parse already collapsed 2.0 -> 2, so pyRepr cannot recover float-ness. An exact fix requires preserving source-token float/int distinction from BOTH the document YAML parse AND the compiled-schema YAML parse, threaded through ajv into the structural error records, then mirrored in Python -- the ~150-line hot-path change the original analysis flagged. That pipeline is the foundation of the byte-parity invariant (proven across all keywords + golden 14/14), so a bug there risks ALL error rendering, not just this edge case. The golden corpus already normalizes error-case values to avoid whole-number floats, so cross-impl parity holds. RECOMMENDATION: do not force this into the 0.2.2 patch; if desired, schedule as a dedicated, golden-backed change (add whole-number-float scenarios first) outside a patch. Deferred from 0.2.2 pending maintainer go-ahead.
