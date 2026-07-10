---
type: is
id: is-01ksrzx0a7npry68ee6z8y3sf6
title: "publish.yml: SHA-pin GitHub Actions on the publish path"
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:25.190Z
updated_at: 2026-07-10T03:49:04.924Z
closed_at: 2026-05-29T04:29:43.276Z
close_reason: "publish.yml now SHA-pins actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6 and astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0. ci.yml keeps tag pins (no publish rights)."
---
Per supply-chain-hardening publish-side controls: SHA-pin every uses: action on the workflow that holds PyPI publish rights. actions/checkout@v6 -> de0fac2e..., astral-sh/setup-uv@v8.1.0 -> 08807647... Tag-pinning is still acceptable on ci.yml (no publish rights).
