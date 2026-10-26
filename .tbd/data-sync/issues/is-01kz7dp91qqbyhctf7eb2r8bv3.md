---
type: is
id: is-01kz7dp91qqbyhctf7eb2r8bv3
title: Python validate_artifact and load_artifact type the document parameter as Any (the _UNREAD sentinel); TypeScript gets a typed ParsedDocument
kind: chore
status: open
priority: 3
version: 4
labels: []
dependencies: []
created_at: 2026-08-04T22:18:15.991Z
updated_at: 2026-10-26T03:32:54.506Z
---
In Python, `_UNREAD: Any = object()` (`packages/python/src/softschema/validate.py:808`) is the default for the pre-parsed-document parameter. That forces `document: Any` on both public entry points, `validate_artifact` (line 842) and `load_artifact` (line 1346), and the same on the private `frontmatter` (line 912) and `raw` (line 1034) parameters. A caller can pass anything without a type error. The TypeScript counterparts take a typed `ParsedDocument` (`packages/typescript/src/validate.ts:110`). Line numbers are at main 8085986.

Nothing is functionally wrong; this is lost static checking, not a defect. It was triaged for v0.6.2 and deferred because the fix touches a public signature.

Fix: give the sentinel a type the checker can narrow, for example a private singleton class or `enum` member, with the parameter typed as a union of the parsed-root type and that sentinel type. Python has no named `ParsedDocument` yet; the root is a mapping, `None` (no frontmatter), or a parsed YAML value. Decide whether the public signature visibly changes shape, and record it in the CHANGELOG if it does. A natural fit for the next minor release that allows API-surface changes.
