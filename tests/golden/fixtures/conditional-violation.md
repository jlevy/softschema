---
softschema:
  contract: demo:Thing/v1
  status: enforced
thing:
  kind: special
---
# A special thing, missing its extra

Fixture for the enforced-composition scenario: `kind: special` fires the conditional,
which requires `extra`. The reported error must be the missing property, not a refusal
to enforce the composition.
