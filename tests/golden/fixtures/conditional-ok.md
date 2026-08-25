---
softschema:
  contract: demo:Thing/v1
  status: enforced
thing:
  kind: plain
---
# A plain thing

Fixture for the enforced-composition scenario: `kind: plain` does not trigger the
conditional, so the document satisfies the schema.
