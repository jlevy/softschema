---
type: is
id: is-01kz7dp8qp6frnzw7n1b3rymmv
title: "CLI cannot validate a pure-yaml artifact: _validate_cmd builds Contract without profile, so it is always frontmatter_md (packages/python/src/softschema/cli.py:310)"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-08-04T22:18:15.669Z
updated_at: 2026-08-22T23:15:03.602Z
closed_at: 2026-08-22T23:15:03.602Z
close_reason: "Fixed in v0.6.2 (PR #39, commit a5db704). The CLI resolved no profile, so validate/inspect always built a Contract with the default frontmatter_md and the pure-yaml branch of validate_artifact was unreachable. Resolution is now --profile flag > *.yaml/*.yml name > fenceless document whose root mapping carries a softschema: block > frontmatter-md, implemented identically in both runtimes. Also fixed envelope inference reaching pure-yaml (the spec exempts it) and inspect being equally blind. Covered by the shared golden corpus, including an enforced pure-yaml artifact that must fail its bound schema. Verified against the published 0.6.2 packages on PyPI and npm."
---
