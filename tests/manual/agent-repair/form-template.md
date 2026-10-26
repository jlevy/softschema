---
softschema:
  contract: example.research:ScanTerms/v1
  schema: scan-terms.schema.yaml
  envelope: scan_terms
  status: enforced
scan_terms:
  ticker: "[TICKER]"
  company: "[COMPANY]"
  as_of_date: [YYYY-MM-DD]
  recognized: [true or false]
  search_fit: [standard or limited]
  term_budget: [0, 10, or 20]
  rubric_version: [rubric version]
  fit_reason: [one short reason for the budget choice]
  panels:
    identity:
      - term: [customer-facing company or brand name]
        why: [short demand connection]
    products:
      - term: [major product, service, model, or sub-brand]
        why: [short demand connection]
    intent:
      - term: [company-qualified purchase or use query]
        why: [short demand connection]
    category:
      - term: [category, market context, or competitor query]
        why: [short context connection]
---
# [TICKER] - Scan Terms

## Notes

[One short paragraph on the demand surface and any uncertainty.]
