---
type: is
id: is-01m18sq92cv9pj6sh93psvkay5
title: "PR #52 review F5: repair path does not name the file for a pure-yaml artifact that still fails to parse"
kind: bug
status: open
priority: 3
version: 3
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:39:09.771Z
updated_at: 2026-08-30T07:42:47.747Z
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
