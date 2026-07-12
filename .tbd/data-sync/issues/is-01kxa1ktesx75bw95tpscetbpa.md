---
type: is
id: is-01kxa1ktesx75bw95tpscetbpa
title: "PR #21 review R3: bound TypeScript YAML AST depth"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxa14h09j4qnzmmj02pv5jzt
created_at: 2026-07-12T02:13:32.248Z
updated_at: 2026-07-12T02:15:53.224Z
closed_at: 2026-07-12T02:15:53.223Z
close_reason: Fixed with AST depth accounting before TypeScript document.toJS() and strengthened the shared deep-sequence vector to 1,000 levels.
---
PR #21 follow-up Bugbot medium finding at packages/typescript/src/portable.ts:37-113: the AST walk counts nodes but does not reject depth before document.toJS().
