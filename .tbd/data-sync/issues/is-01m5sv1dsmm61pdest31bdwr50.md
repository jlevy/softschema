---
type: is
id: is-01m5sv1dsmm61pdest31bdwr50
title: "Owner: wire the pypi and npm environments into publish.yml and the PyPI/npm trusted publishers (PR #64 D1)"
kind: task
status: open
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01m5v4505x0s8nc898036ey4wh
created_at: 2026-10-25T15:32:03.508Z
updated_at: 2026-10-26T03:31:19.717Z
---
PR #64 review D, finding D1 (High): https://github.com/jlevy/softschema/pull/64#pullrequestreview-5642133204. The owner deferred it in round 2.

The repository has `pypi` and `npm` environments, each with required reviewers and a deployment policy limited to `v*` tags. `publish.yml` never declares them, so neither gate applies, and the PyPI and npm trusted publishers accept an OIDC token from any ref that runs the workflow.

State verified 2026-10-26 at main 8085986:

- `.github/workflows/publish.yml` jobs `publish-pypi` (line 15) and `publish-npm` (line 51) have no `environment:` key.
- `gh api repos/jlevy/softschema/environments` lists `npm` and `pypi`.
- v0.9.0 was published through this unwired path (publish run on release v0.9.0, 2026-10-26, success).
- The `github-editing: granted` policy that review D tied this risk to is now in effect on main (PR #64).

Fix (owner change: workflow files and registry settings are outside `github-editing`):

1. Add `environment: pypi` to `publish-pypi` and `environment: npm` to `publish-npm`.
2. Set the same environment name in the PyPI project's trusted-publisher settings and in the npm package's trusted-publisher settings.
3. Keep the `v*` deployment policy and the required reviewers.

Verify with the next release's publish run: it should wait for environment approval.
