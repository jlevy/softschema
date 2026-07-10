---
softschema:
  format: "1"
  contract: example.conformance:Movie/v1
  schema: schema.yaml
  envelope: movie
  status: enforced
  extensions:
    com.example.review:
      labels: [classic, family]
    https://schemas.example/extensions/source/v1: conformance
movie:
  title: Spirited Away
  year: 2001
---

# Spirited Away

The opaque extensions are preserved as metadata and do not alter core validation.
