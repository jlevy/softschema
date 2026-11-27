# Plan: Read-Only SoftSchema Collections

**Status:** In progress

Collection consumers need to discover artifacts in a tree, bind compiled schemas, and
read payloads and per-record verdicts without launching a process for each file.
The first consumer is Metabrowser’s proposed folder Table view.
Both SoftSchema runners use the same collection semantics and CLI output.
This plan covers the bounded eager API. The
[Collection Design](../../softschema-collection-design.md) defines the proposed
reference, streaming, and reconciliation capabilities for hosts that need to control
materialization.

## Collection Boundary

A caller supplies a root.
Discovery visits regular Markdown, YAML, and JSON files, ignores hidden entries and
symlinks, and recognizes compiled schemas by `.schema.yaml`, `.schema.yml`, or
`.schema.json`. A host can narrow discovery further with an ignore rule.
A file that declares metadata becomes a record even if parsing or envelope extraction
fails. Files that cannot be examined within a bound are reported separately where the
collector cannot establish whether they are records.

Schema pointers resolve relative to the record.
A pointer may bind a scanned schema inside the collection root with a matching contract.
A missing usable pointer can fall back to a schema with the same contract.
Identical schema content is equivalent.
Several distinct candidates make that fallback ambiguous.
The collector performs only compiled structural validation and reads schema resources
offline.

Results preserve payloads after a completed rejection and identify skipped and errored
validation. Repair and conform run on copies.
A repaired verdict requires completed structural validation of the repaired payload.
The body is reader-facing.

## Delivery

1. Implement bounded discovery and a deterministic `softschema scan ROOT --json` report.
   Pin the output in one journey run by both implementations.
2. Bind schemas and use the existing portable validation and repair layers.
   Publish schema field information through `SchemaView`.
3. Persist a versioned, runtime-local snapshot through the host.
   Refresh only changed file inputs and revalidate stored payloads when a bound schema
   changes. Compare an incremental refresh with a fresh scan after rewrites, additions,
   and removals.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
