---
softschema:
  contract: test.numbers:Big/v1
  status: enforced
data:
  big: 9.0e15
---
# Large whole-number float parity (ss-wbnm)

Regression guard for the large-whole-float edge of the canonical-number rule. The bound
`minimum: 1.0e16` and the value `big: 9.0e15` are both whole-valued floats above 2^53.
Python's `canonical_number` renders them as plain integers (`10000000000000000`,
`9000000000000000`) — the same form JavaScript emits natively (`JSON.stringify` prints a
whole-valued number in full integer notation below 1e21) — so the `value`,
`validator_value`, and message stay byte-identical across `jsonschema` and `ajv`. Before
the threshold moved from 1e16 to 1e21, Python emitted `1e+16` here while TypeScript
emitted `10000000000000000`, breaking parity in `validator_value`.
