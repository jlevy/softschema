---
type: is
id: is-01m5tg51ecy4z6vjzt39kv67kj
title: "PR #64 F1: TS tab check tolerates a tab after a block scalar header, a closing quote, or a flow collection's closing bracket"
kind: bug
status: closed
priority: 1
version: 2
labels:
  - pr-64
dependencies: []
created_at: 2026-10-25T21:41:02.027Z
updated_at: 2026-10-25T21:43:22.484Z
closed_at: 2026-10-25T21:43:22.483Z
close_reason: "Fixed in 62e88c3 (PR #64, head 6c366f6): checkPlainTabs walks block-scalar props, only start/items of a flow collection as flow spacing, and quoted scalars' end tokens (same gap found for t: \"a\"<TAB>). Vectors tab_after_block_scalar_header, tab_between_block_scalar_header_and_comment, tab_after_flow_collection(_before_comment), tab_after_root_flow_collection, tab_after_quoted_scalar (rejected); tab_in_block_scalar_header_comment, tab_before_flow_collection_end, tab_after_nested_flow_collection (accepted). 5,000-case tab-insertion sweep py(C-first+pure) vs TS: 330 mismatches before, 0 after; reviewer's 62-fixture p5_tabs matrix via py/node/bun CLIs: rc/outcome/kind/values identical for all 62. CI run 40236576983: 19/19 pass. Dispositions: https://github.com/jlevy/softschema/pull/64#issuecomment-6403718248"
resolution: null
duplicate_of: null
---
Review F (https://github.com/jlevy/softschema/pull/64#pullrequestreview-5645232362) F1, Medium. packages/typescript/src/portable.ts checkPlainTabs returned early for block-scalar before walking props, skipped quoted scalars' end tokens, and walked flow-collection end with flow=true, so title: |<TAB>, title: |<TAB># c, tags: [a, b]<TAB>, t: "a"<TAB> were valid in node/bun and yaml_parse_error in Python (exit 0 vs 2).
