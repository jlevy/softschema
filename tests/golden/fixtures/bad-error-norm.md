---
softschema:
  contract: test.errors:Sample/v1
  status: enforced
data:
  step: 7
  scale: 0.3
  ratio: 1.0
  count: "x"
  rating: X
  label:
    kind: x
  choice:
    tier: bronze
  tags:
    - a
  extra1: 1
  extra2: 2
---
# Bad error-normalization fixture

Exercises the structural-error keywords that the movie fixture does not:
missing `required` keys, `multipleOf`, `type`, `enum`, `minItems`, and
`additionalProperties`. The `ratio: 1.0` field (failing `minimum: 2.0`) covers the
whole-number-float case (`ss-wbnm`): both the value `1.0` and the bound `2.0` render
in canonical form (`1`, `2`) so the `value`/`validator_value`/message are
byte-identical across `jsonschema` and `ajv`.
