# Implementing the softschema Conformance Kit

The kit is a data-only contract for an implementation that does not import the Python or
TypeScript packages.
Start by authenticating the release archive SHA-256, extract it into an empty directory,
and run:

```bash
python conformance/consumer.py --json
```

That standard-library consumer verifies every declared path, size, and SHA-256 from
`manifest.lock.json`. It does not import softschema, execute a model, resolve a schema
over the network, or read files outside the extracted kit.

## Implement the Protocol

1. Read `manifest.yaml` for policies, supported artifact profiles, and coverage.
2. Validate descriptors with `schemas/case.schema.json` and vector suites with
   `schemas/vector-suite.schema.json`.
3. Implement each operation named in `implementations.json`.
4. For a vector suite, accept one JSON request with `format`, `operation`, and `cases`.
   Return strict JSON with `format: softschema-vector-results-v1`, the suite ID, and one
   `{id, actual}` record per input case in the same order.
5. Compare JSON values, not object key order.
   Do not coerce booleans to numbers or accept non-finite numbers.
6. Run every ready artifact case.
   A case’s `expected.schema` identifies the result schema, and `expected.result` gives
   the exact expected JSON value.

Missing schema resources are failures.
A resource URI is only a key in the explicit `resources` object; it never authorizes
HTTP, file, package, or relative-path retrieval.
Compound resources may contain nested `$id` values, but the complete resource graph must
remain inside the supplied bundle.

## Versioning and Publication

Read `evolution.json` before changing an existing vector or result.
Published versioned paths are immutable.
Add compatible capabilities in a new minor kit and change existing outcomes only in a
new major kit.

Source schemas retain draft URNs until the generated HTTPS candidate is live and every
URL returns status 200 with no redirect, an allowed JSON media type, and exact candidate
bytes. `publication.py` builds those staged bytes without modifying the source schemas.
Before deploying, `verify-predeploy` requires the versioned namespace to be wholly
absent or already byte-identical; after deployment, `verify-live` rechecks every
candidate byte.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
