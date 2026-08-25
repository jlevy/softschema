---
softschema:
  contract: demo:Thing/v1
  status: enforced
thing:
  kind: plain
  bogus: 1
---
# A plain thing with an undeclared key

Fixture for the enforced-composition scenario: `bogus` is declared nowhere in the
schema, so closure must reject it even though the schema composes.
