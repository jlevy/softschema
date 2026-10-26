---
type: is
id: is-01m5sy970th1qgf3bmcyfk3exc
title: "Owner: add dependency-audit to the Protect main ruleset's required checks, then drop the stopgap bun audit step from the typescript job"
kind: task
status: open
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4505x0s8nc898036ey4wh
created_at: 2026-10-25T16:28:44.442Z
updated_at: 2026-10-26T03:31:08.945Z
---
From PR #65 (cfa93ef), which moved `bun audit` into its own `dependency-audit` CI job.

State verified 2026-10-26 at main 8085986:

- `.github/workflows/ci.yml:239-263` defines the `dependency-audit` job.
- The "Protect main branch" ruleset (id 18755846) requires 16 status checks (build x4, golden x4, typescript, cross-impl, Artifact smoke x6). `dependency-audit` is not one of them.
- So the required `typescript` job repeats the audit as a stopgap, at `.github/workflows/ci.yml:313-319` ("Audit dependencies (stopgap until dependency-audit is required)"). The comment there names this bead.

Steps, in this order:

1. Owner: add `dependency-audit` to the required status checks of the "Protect main branch" ruleset. Agents cannot change rulesets.
2. Then, in a PR: delete the stopgap step and its comment from the `typescript` job.

Do not drop the stopgap before step 1. The audit would stop blocking merges.
