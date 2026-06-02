---
cwd: ../../..
env:
  NO_COLOR: "1"
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: a status override emits an identical document-status-mismatch warning

The movie artifact declares `status: enforced`; overriding the contract status with
`--status permissive` makes the document's declared status disagree, which both CLIs
report as a `document-status-mismatch` warning (validation still passes). The warning
record is byte-identical across implementations.

```console
$ softschema validate examples/movie_page/spirited-away.md --schema examples/movie_page/movie-page.schema.yaml --envelope movie --status permissive | grep -A2 document-status-mismatch
      "code": "document-status-mismatch",
      "message": "document declares status 'enforced'; contract uses 'permissive'",
      "severity": "warning"
? 0
```
