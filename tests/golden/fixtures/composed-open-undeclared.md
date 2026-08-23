---
softschema:
  contract: demo:Composed/v1
  status: enforced
composed:
  first: Ada
  last: Lovelace
  bogus: 1
  other: 2
---
# A composed record with undeclared keys

Two undeclared keys, so the record count is observable: ajv reports one closure error
per key and jsonschema one per object, and normalization must collapse them to one.
