---
cwd: ../../..
env:
  NO_COLOR: "1"
patterns:
  VERSION: '[0-9][0-9A-Za-z.+-]*'
path:
  - $SOFTSCHEMA_BIN_DIR
---

# Test: --version prints the package version

Both CLIs print `softschema <version>` and exit 0. The version string itself is
environment-specific (git-derived on Python, `package.json` on TypeScript), so it is the
one genuinely variable field and is matched with a `[VERSION]` pattern; the `softschema `
prefix and the exit code are asserted.

```console
$ softschema --version
softschema [VERSION]
? 0
```
