# Softschema Conformance Kit (Draft)

This directory is the language-neutral contract and case corpus for softschema.
It is unreleased infrastructure while the 0.3 behavior is being defined.
Draft schema identifiers use `urn:softschema:draft:` and are not stable public
identifiers.

The existing `tests/golden/` corpus remains the byte-for-byte CLI compatibility suite.
This kit instead describes semantics that another implementation can consume without
using Python or TypeScript model source.

Run the integrity checks and all currently supported implementations:

```bash
uv run python conformance/run.py --check-only
uv run python conformance/run.py --implementation all
```

The runner validates every schema against the Draft 2020-12 metaschema, validates the
manifest and case descriptors, and checks every declared SHA-256 digest.
It then executes every `ready` case against the selected CLI. `--implementation all`
selects Python, Node, and Bun; the summary reports ready and pending case counts
separately.

Behavior-specific beads extend the draft cases and finalize their owned schemas.
The foundation may carry `execution.status: pending` negative vectors whose owning bead
has not implemented the behavior yet; the runner validates their files, digests,
descriptor, and expected-result schema but does not execute them.
The owner changes a vector to `ready` only with the behavior implementation.
The kit receives immutable HTTPS identifiers and a standalone archive only after the
full semantic contract is settled.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
