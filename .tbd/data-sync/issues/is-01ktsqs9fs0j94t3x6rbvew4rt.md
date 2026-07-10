---
type: is
id: is-01ktsqs9fs0j94t3x6rbvew4rt
title: "P1: Python cli.py hardening (error boundary, --version, generate exit codes, dev-root fail-clear, atomic skill write, dedent)"
kind: task
status: closed
priority: 1
version: 7
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqsdqeadg067hwcw146k2m
  - type: blocks
    target: is-01ktsqsexjfpcr1t1j2m7q9jdx
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:31.160Z
updated_at: 2026-07-10T03:49:14.166Z
closed_at: 2026-06-10T21:56:58.135Z
close_reason: null
---
FILE SCOPE: packages/python/src/softschema/cli.py only.
- Single error boundary across validate/compile/inspect/generate: catch OSError, FileNotFoundError, FmFormatError, YAMLError, ModuleNotFoundError/ImportError, TypeError, ValueError, ValidationError; print one-line 'softschema <cmd>: <msg>' to stderr; exit 2. No tracebacks for user mistakes. Reproduced cases: missing file, malformed frontmatter, bad --model spec, malformed softschema block in inspect.
- generate: runtime errors exit 2 (reserve 1 for drift) for consistency with validate/compile.
- Add --version (wire existing _installed_version()).
- _install_skill: use strif.atomic_write_text (parity with compile/generate).
- _brief_skill_text: dedent (no flush-left multi-line string).
- _dev_repo_root: raise clear error instead of guessing parents[4].
PARITY PAIR with P1 ts cli.ts bead: error-boundary message shape, exit codes, --version output must match. Per-language regression tests (test_cli.py). Refs review Specific Issues>Python.
