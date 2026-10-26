---
type: is
id: is-01m5ry9zw4mtb2dfcke80n1hxp
title: YAML engines diverge on U+0085 and C0 control characters inside scalars (ruamel folds NEL to a space and rejects FF/VT/FS as non-printable; the yaml package keeps them as content)
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxgc8kdy9fz5wgg3ew5vsq
hold: null
hold_until: null
created_at: 2026-10-25T07:09:55.459Z
updated_at: 2026-10-25T07:30:22.765Z
started_at: 2026-10-25T07:18:58.069Z
closed_at: 2026-10-25T07:30:22.765Z
close_reason: "fixed in 45eca8b: shared portable preflight (check_portable_text / checkPortableText) rejects raw non-c-printable characters and U+0085/U+2028/U+2029 before parsing in both runtimes, yaml_parse_error with one message naming character, line and column; escapes (\\f \\x7f \\N \\L \\P) accepted. Matrix 7 chars x 9 contexts: 10/63 identical before, 63/63 after. Evidence: hardening.yaml portable_values (7 raw rejections, 2 escape value cases) + frontmatter escaped_line_separators_in_scalar; cli-errors goldens on tests/golden/fixtures/next-line.md and control-character.md (full message pinned, py/ts/ts-bun); test_frontmatter_reader_keeps_unicode_separators_inside_their_line; spec Portable YAML Values paragraph; CHANGELOG."
resolution: null
duplicate_of: null
---
Found while addressing PR #64 A5. After the line-splitting fix both runtimes reach the same verdict on U+2028/U+2029/U+0085 (vector next_line_in_scalar asserts verdict only), but: (1) ruamel folds U+0085 into a space (YAML 1.1 line break) where the yaml npm package keeps it (YAML 1.2), so values differ; (2) ruamel rejects form feed, vertical tab and the ASCII separators as 'unacceptable character' (YAML 1.2 c-printable) where the yaml package accepts them, so verdicts differ (Python exit 2, TypeScript reads the document). Design decision needed: add a portable non-printable preflight on the TypeScript side (reference engine is Python) or document as an engine deviation. Repro: tests/vectors/hardening.yaml frontmatter section plus a form-feed probe.
