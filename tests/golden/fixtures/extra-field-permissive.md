---
softschema:
  contract: test.enforced:Record/v1
  status: permissive
record:
  name: Acme
  meta:
    source: web
    fetched_by: agent
  confidence: high
---
# Acme

Fixture for the enforced-status scenario: `confidence` and `meta.fetched_by` are
extension fields the schema does not declare.
