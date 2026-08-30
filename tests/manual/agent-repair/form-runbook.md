# Prelim Scan Terms — Runbook

You propose high-recall customer search queries for one ticker, so a later stage can
pull Google Trends panels for them.

Do a quick mental check of the company’s current brands and products, then fill in the
form. Keep it fast — this is a breadth-tier pass, not a deep dive.

## What each part of the form means

- **Ticker** — the exchange ticker symbol, capitalized.
- **Company** — the company’s common name.
- **As of date** — today’s date, in year-month-day form.
- **Recognized** — whether you actually recognize this company.
  True or false.
- **Search fit** — whether the company has standard consumer search demand, or only
  limited search demand (B2B, holding companies, obscure names).
- **Term budget** — how many queries you are proposing.
  Use 20 for a company with standard search fit, 10 for limited fit, and 0 if you do not
  recognize the company.
- **Rubric version** — the scoring rubric you used.
  The current one is 1.10.
- **Fit reason** — one short sentence on why you chose that budget.
- **Panels** — the queries themselves, grouped into four panels:
  - *identity*: the company or brand name as customers type it
  - *products*: major products, services, models, or sub-brands
  - *intent*: purchase or use queries, company-qualified
  - *category*: category, market context, or a direct competitor Every query needs the
    query text itself and a short reason it connects to demand.

Spread the budget across the four panels.
Every panel needs at least one query.

## Output

Return the complete filled-in document, frontmatter and all, in a single fenced
`markdown` code block.
Keep the `softschema:` block exactly as given.
