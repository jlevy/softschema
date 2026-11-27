# SoftSchema Collection Design

**Status:** The bounded eager scan is implemented in the collection API change.
The reference, streaming, and reconciliation APIs below are proposed.
Their names describe capabilities and are subject to implementation review.

A collection is a read-only view of a root and a discovery policy.
Its source files contain records and compiled schemas.
A notebook with ten records can load them in one call.
A table backed by many directories can identify files, catalog contracts, index selected
cells, and load a record on demand.
Each caller chooses how much data to inspect and how long to retain it.

## References and Observations

| Concept | Minimum information | When it can be known |
| --- | --- | --- |
| Collection scope | Root identity and discovery policy, including an ignore-policy identity for refresh | At open |
| File candidate | Scope-relative normalized path, candidate kind, and observed file revision | From enumeration and file metadata |
| Record reference | Candidate locator plus the declared contract, profile, status, envelope, and optional schema pointer | After portable declaration inspection, or from a matching cached observation |
| Schema reference | Locator, declared contract if present, and canonical parsed schema identity | After schema inspection |
| Materialized record | Payload, requested host metadata and body, and any requested validation verdict and repair diagnostics | After reading the referenced revision and resolving the requested validation context |

A path identifies a location within its scope.
A rename is a removal and an addition at that level.
A business identifier such as a typed `id` lives in the payload.
A host can index it for links and check for duplicates.
A file revision describes which input was observed, and a binding revision records which
schema and selection rules determined a verdict.
A file stamp is a cheap cache key.
Use a content digest when a client requires exact byte identity.

Discovery can enumerate candidates without opening files.
Certifying collection membership requires enough of the portable reader to find and
check the declaration.
An unreadable file, a truncated declaration, or an exhausted read budget leaves
membership unknown. A file that was successfully inspected and had no declaration can be
reported as outside the SoftSchema record set.

Reading a reference can return the observed revision, `stale`, `gone`, or an input
diagnostic. A live filesystem can provide a newer observation after a change.
Reading an older version requires a host that retained those bytes.
Revision checks apply before and after reading, and resolution uses the same root
boundary and symlink policy as the scan.

## Optional Library Operations

| Operation | Result | Work the caller opts into |
| --- | --- | --- |
| Open a collection | A handle defining root, discovery policy, and bounds | Resolve the scope |
| Enumerate candidates | A stream of file references and terminal coverage | List and stat files |
| Inspect a declaration or schema | A record or schema reference, absence, an unknown result, or a diagnostic | Inspect selected files without retaining their values |
| Load a record | A payload and requested host metadata or body | Open and parse one referenced revision |
| Bind, validate, or repair | Schema selection, execution, verdict, and optional in-memory repairs | Apply the compiled schema to one payload |
| Scan and reconcile | Observations and a revisioned set of input changes | Compare covered observations with optional prior state |
| Eager scan | Records, schemas, summary, and runtime-local refresh state | Collect and validate a bounded tree in memory |

Hosts can take a simple path through these operations.
A CLI audit can consume observations and retain only counts and problem paths.
An inspector can list references and load one on activation.
A table indexer can inspect the schema catalog, stream record payloads through a
projection, and drop each payload as soon as its cells and links have been indexed.

The eager Python `scan_collection` and TypeScript `scanCollection` calls already provide
the last row of the table above.
They return parsed payloads and bodies and can retain them for refresh.
Their entry, per-file, and aggregate-byte limits protect the bounded call.
The independently callable operations and the streaming implementation are follow-up
work. They should reuse the same portable readers, binding rules, and validation states.
[Current collection usage](softschema-guide.md#inspecting-a-collection)

## Scanning and Reconciliation

Scanning observes files under a scope.
Reconciliation compares those observations against a previously committed index for the
same scope. A scan can stream in filesystem order with bounded buffering, cancellation,
and backpressure from its consumer.
Sorting a complete catalog requires retaining references or using an external sort.
User-facing stable pagination belongs on a committed index generation.

Track directory-listing coverage, declaration-inspection coverage, and schema discovery
coverage independently.
A completed directory listing can establish a known file’s removal even if the
payload-read budget is exhausted.
An unreadable subtree leaves files previously known under that subtree unresolved.
Cancellation, early iterator exit, and interrupted walks leave the prior membership
available.
The host can stage observations and commit updates for a scope after observing
its terminal coverage.
A cap reached before terminal coverage produces a reason and the affected scope.

Report file additions, changes, and removals separately from record or verdict updates.
A schema edit can change many verdicts even when every record file is unchanged.
A new same-contract schema can invalidate a previously unique fallback.
A host that persists outcomes should key them on the input revision, the binding context
and selected schema, and the validation policy.
A host that wants to reconform without reopening a file needs the original input or its
relevant scalar spellings, since conformance can depend on how the source represented a
value.

An observed usable pointer can bind once its target has been inspected.
Unique fallback requires a closed schema catalog for the applicable scope.
A typed or bound verdict that depends on an open catalog remains pending.
An unreadable ordinary record does not by itself invalidate completed schema discovery.
A host that needs final verdicts as rows stream can catalog schemas first and defer
record work. A single traversal can stage candidates and resolve deferred bindings once
catalog coverage closes.

## What Tables Need

A table needs a stable row locator, a full contract identity for grouping, and the
compiled field description for columns.
An initial file inventory can return only references and catalog information.
Showing cell values requires a payload read or an existing projection of that revision.

For a small collection, the host can hold the references and whichever values it wants
to display. For a large collection, the host can keep a disk-backed projection of
selected cells, labels, source paths, and diagnostics.
Filtering and ordering across an entire table may require examining every relevant row,
even when the page itself is small.
Build the projection incrementally and serve pages from a stable generation.
Fetch complete values and Markdown prose for record detail on demand.

Linked tables can add a host index from a typed target ID to its matching row locations
and an index from a source row and field to its target ID. This supports forward links
and backlinks without loading all payloads.
Report duplicate targets explicitly.
An incomplete index has unknown coverage for omitted links and counts.
A table’s visible folder can be narrower than the scope used for link resolution.
The host owns the projection, link policy, persistence, query semantics, and UI.

## Schema Discovery Conventions

The default collection policy discovers `.schema.json`, `.schema.yaml`, and
`.schema.yml` files throughout the root.
Retaining all three suffixes lets the same scan work with existing compiled YAML schemas
and machine-generated JSON schemas.

A host that controls the tree can put compiled schemas in a dedicated directory such as
`_schemas/` and use an optional catalog policy to restrict fallback discovery to that
directory and its chosen suffixes.
A JSON-only catalog is one such policy.
Its closed coverage means all candidates under the configured catalog were examined.
An explicit relative schema pointer can still be resolved safely inside the collection
root and checked for contract compatibility, even outside the fallback catalog.
Catalog policy and its identity belong in the refresh scope.

Schema-first discovery exposes known contracts and column definitions early.
The presence of a schema gives the host a known contract to present.
Record discovery still reads declarations, including declarations whose schema is absent
or unresolved. An application can use an explicit configuration or a catalog hit to show
a collection entry point before opening record payloads.

## Formats and Performance

- **Markdown with YAML frontmatter.** Inspect through the closing fence for declarations
  and frontmatter fields.
  A header-only request leaves body decoding unverified.
  Preserve the existing fence, source offset, and line ending rules.
  A fenceless file can still be a pure-YAML artifact under the profile rules.
- **Pure YAML.** Declaration keys and values can appear anywhere in a mapping.
  Inspection may require processing the whole artifact.
  Parsing one bounded file and discarding its payload still keeps memory independent of
  the number of files.
- **JSON.** JSON uses the pure-YAML profile today.
  A native JSON fast path is an implementation option for that profile if it preserves
  its portable restrictions, including duplicate keys, safe numbers, and structural
  limits. A suffix alone neither authenticates the declaration nor narrows accepted
  syntax. An explicitly strict JSON source could be a separate host choice if measured
  gains justify it.

The declaration detector looks for a root `softschema` key in bare YAML or JSON, or in
the opening fenced metadata block of Markdown.
A JSON object written inside the fence is a YAML flow mapping and follows the same
frontmatter rules. Escaped keys, quoted keys, and late properties can carry real
declarations. A nested key, a body mention, or a substring in a value does not establish
membership. A lexical check can skip content only when it can prove that the declaration
is absent. The portable reader confirms membership and reports malformed declarations.

Bound retained state separately from total work.
A stream can limit outstanding bytes, per-file parsing, and concurrent reads while
continuing through a large tree.
Consumers may retain all references when that is practical, or write them to a
disk-backed sink. A limit or cancellation must leave explicit coverage, so consumers can
tell a partial result from a complete one.

Before treating the streaming path as large-directory support, measure incremental
results on a large flat directory and a deep mixed tree.
Include JSON, frontmatter, large unread Markdown bodies, and schema-only edits.
Record time to first reference and first table page, aggregate bytes read, peak memory,
index size, and cold and warm refresh time.
Compare streamed complete membership, bindings, and verdicts with the eager result where
both fit the bounds.
Exercise unreadable scopes, cancellation, renames and deletes, declaration and schema
changes, and optional native parsers on the same fixtures in both runtimes.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
