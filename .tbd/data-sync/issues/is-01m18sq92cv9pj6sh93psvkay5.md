---
type: is
id: is-01m18sq92cv9pj6sh93psvkay5
title: "PR #52 review F5: repair path does not name the file for a pure-yaml artifact that still fails to parse"
kind: bug
status: closed
priority: 3
version: 5
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
hold: null
hold_until: null
created_at: 2026-08-30T07:39:09.771Z
updated_at: 2026-10-25T06:26:59.159Z
started_at: 2026-10-25T06:04:17.991Z
closed_at: 2026-10-25T06:26:59.158Z
close_reason: "Fixed in 2a65587: parse_yaml_text/parseYamlText take source, readers prefix a parse failure with the backticked document path in both profiles, and the repair command prefers the reader's message over repair's own copy of the engine text. Golden: new pure-yaml journey in tests/golden/scenarios/repair.tryscript.md (fixture repair-unrepairable.yaml) pins the prefix on the repair --check record and on validate's one line; the frontmatter floor journey pins its prefix too. Goldens pass under py/ts/ts-bun, cross-impl-diff OK, plus one reader test per implementation (test_core.py, validate-extra.test.ts)."
resolution: null
duplicate_of: null
---
_parse_after_repair threads 'source' into parse_frontmatter_text but not parse_yaml_text, which takes no such parameter. Same asymmetry in TypeScript (parseYamlText).

Observed: 'missing --contract because the document could not be read: while parsing a flow sequence in "<unicode string>", line 4, column 6:' - no filename. An agent repairing a batch cannot tell which artifact this is about, and naming the artifact is exactly what PR #52's second fix was for.

Fix: give parse_yaml_text / parseYamlText the same source parameter and thread it through.

Files: packages/python/src/softschema/validate.py, packages/python/src/softschema/cli.py, packages/typescript/src/validate.ts, packages/typescript/src/cli.ts

## Notes

Corrected during triage. My review framed this as an asymmetry introduced by PR #52 (the frontmatter branch got a 'source', the pure-yaml branch did not). Verified: that framing is wrong.

Plain validate omits the filename for pure-yaml too:
  validate broken.yaml                -> 'while parsing a flow sequence in "<unicode string>", line 4'
  validate broken.yaml --check-repair -> 'could not be read: while parsing a flow sequence in "<unicode string>", line 4'

The gap is per-profile (pure-yaml artifacts never name the file), identical on both paths. So it is NOT a parity break and NOT something this PR introduced. read_yaml_doc calls parse_yaml(read_utf8(path)) and drops the path the same way parse_yaml_text does.

Still a real diagnostic gap worth closing, but doing it properly means threading a source through parse_yaml / parsePortableYaml, which every read path goes through. Too broad for a pre-release patch. DEFERRED, not blocking v0.8.0.
