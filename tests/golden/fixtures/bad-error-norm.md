---
softschema:
  contract: test.errors:Sample/v1
  status: enforced
data:
  step: 7
  scale: 0.3
  count: "x"
  rating: X
  tags:
    - a
  extra1: 1
  extra2: 2
---
# Bad error-normalization fixture

Exercises the structural-error keywords that the movie fixture does not:
missing `required` keys, `multipleOf`, `type`, `enum`, `minItems`, and
`additionalProperties`. Deliberately avoids whole-number floats so the
`value`/message rendering is byte-identical across `jsonschema` and `ajv`.
