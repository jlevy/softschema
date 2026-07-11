# softschema Conformance Kit

This directory is the versioned, language-neutral contract and case corpus for
softschema. It separates portable semantics from Python/Pydantic and TypeScript/Zod
implementation details.
The reference CLI goldens in `tests/golden/` remain the byte-for-byte compatibility
suite; this kit is the contract a third implementation can consume on its own.

The source kit is a publication candidate, not a released namespace.
Its schemas retain `urn:softschema:draft:` identifiers until every final HTTPS URL
serves exact candidate bytes.
`publication.json` records that gate, and `publication.py` stages the final-ID bytes
without rewriting source schemas.

## Run the Kit

Validate integrity without executing an implementation:

```bash
uv run --locked --no-sync python conformance/run.py --check-only
```

Build the TypeScript package, then execute every ready artifact case, portable-core
vector, and doctor claim under Python, Node, and Bun:

```bash
cd packages/typescript
bun run build
cd ../..
uv run --locked --no-sync python conformance/run.py --implementation all
```

An extracted release archive can verify itself without installing softschema or a YAML
library:

```bash
python conformance/consumer.py --json
```

The standard-library consumer verifies the sorted path, size, and SHA-256 inventory in
`manifest.lock.json`. Authenticate the archive’s external SHA-256 before trusting that
internal lock.

## Contents

- `manifest.yaml` records versions, policies, defaults, exit/result contracts, coverage,
  schemas, cases, vector suites, and support artifacts
- `schemas/` contains Draft 2020-12 contracts, including the optional `x-softschema`
  annotation-vocabulary metaschema and the explicit offline bundle shape
- `cases/` uses YAML descriptors and expected results to exercise artifact parsing, both
  storage profiles, metadata, validation, legacy JSON, diagnostic-v1 JSONL, schema
  errors, formats, regexes, and identities
- `vectors/` uses YAML suites to exercise runtime-neutral core operations through a
  strict JSON adapter protocol
- `implementations.json` declares the official Python, Node, and Bun execution matrix
- `evolution.json` defines independent kit versioning and immutable-path rules
- `WALKTHROUGH.md` is the third-implementation protocol

Case and vector order is significant and deterministic.
Resources are data supplied in the descriptor; a URI never authorizes network,
filesystem, package, or implicit relative retrieval.
Missing resources fail closed.

## Release Manifest Limits

The release-manifest contract accepts a declared subject size from 1 through 536,870,912
bytes (512 MiB). The protected release driver also rejects a manifest when the sum of
all declared subject sizes exceeds 1,073,741,824 bytes (1 GiB). The schema enforces the
per-subject limit. The aggregate limit is a cross-subject semantic invariant enforced by
`devtools/release_state.py` before subject files are read.

## Publication Gate

Build the version-preserving static candidate in an empty directory:

```bash
python conformance/publication.py build publication-out
```

Before deployment, reconstruct the complete append-only Pages namespace and reject any
conflicting bytes:

```bash
python conformance/publication.py verify-predeploy publication-out \
  --promotion-marker conformance/publication-promoted.sha256
```

`publication-index.json` inventories every deployed file, not only `schema/v1/`. The
predeploy gate verifies and retains each live entry before it adds new paths, so a
deployment cannot delete an older version or unrelated root file.
Every declared file path is immutable; the root index changes only by adding entries.

The promotion marker is absent before the first deployment.
That is the only state in which a wholly absent live namespace is accepted.
After every live verification, independently review the generated marker from the
workflow artifact and commit its root `publication-index.json` digest as
`conformance/publication-promoted.sha256` through protected `main` before running the
workflow again. The marker binds the complete prior namespace, so a missing, changed, or
incomplete root index and every outage fail closed.

The Pages workflow performs this check from protected `main`, deploys the reconstructed
namespace, and verifies the live marker and every declared file:

```bash
python conformance/publication.py verify-live publication-out \
  --promotion-marker conformance/publication-promoted.sha256
```

Promotion requires status 200, zero redirects, a declared media type, and byte-for-byte
SHA-256 equality for the root namespace index and every declared file.
Until that sequence succeeds against `https://jlevy.github.io/softschema/schema/v1/`,
draft URNs remain authoritative and no stable public schema ID is claimed.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
