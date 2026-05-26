# Future TypeScript/Zod Package

This directory is intentionally a stub.

A future TypeScript implementation should be an idiomatic port, not a line-by-line
translation of the Python package.

Likely constraints:

- source schemas use Zod
- JSON Schema sidecars are exported from Zod
- artifact metadata remains `softschema.contract`
- contract ID conventions remain language-neutral
- validation result shape should match Python conceptually while using idiomatic
  TypeScript types

Do not add Node, npm, pnpm, or Zod build machinery until the TypeScript package is
actually being implemented.

Use the root [Softschema Guide](../../docs/softschema-guide.md) for the concept and
[Softschema Spec](../../docs/softschema-spec.md) for the artifact format that a future
TypeScript package must preserve.

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
