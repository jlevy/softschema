# Migrating to softschema 0.3

Version 0.3 tightens unsafe or ambiguous boundaries and adds new opt-in surfaces without
changing the default artifact profile or the legacy single-file JSON result.
Most self-describing 0.2 artifacts continue to validate, but authored schemas, YAML edge
values, TypeScript bindings, and skill installation may need deliberate changes.

This document describes the unreleased source candidate.
Repository quickstarts and the agent skill use `release-metadata.json` package `pin`
values, which remain on the last dual-registry-verified stable release.
The separate package `version` values name candidate artifacts and must not be used as
published install instructions until registry verification succeeds.

## Migration Checklist

1. Run existing artifacts through 0.3 in a branch and keep the complete structured
   results.
2. Remove YAML aliases, merge keys, tags, duplicate or non-string keys, timestamps
   materialized as YAML types, non-finite numbers, and unsafe integers.
3. Make every non-fragment schema resource explicit and available offline.
4. Recompile model-derived schemas once.
   Review the contract/schema identity change and commit the new schema and hash
   together.
5. Update TypeScript callers to `ContractDescriptor` plus `bindContract`; compile Node
   model modules to `.js` or `.mjs`, or use Bun for direct `.ts`.
6. Keep parsers of the existing single-file JSON result unchanged when discovery
   classifies one single explicit path as a regular file, including when a later read
   fails, and for the narrow missing-path or broken-symlink `not_found` exception.
   Expect diagnostic-v1 for other discovery failures, multiple or discovered paths,
   JSONL, and SARIF.
7. Preview every skill install with explicit scope and review every target before
   writing.

## Artifact and YAML Changes

The storage profile remains explicit.
`frontmatter-md` is still the default; `.yaml` and `.yml` never imply `pure-yaml`.

The portable value domain is JSON-compatible YAML with bounded bytes, resources, nodes,
depth, and scalar length.
It rejects representation features that ordinary object construction can erase:
duplicate keys, non-string keys, aliases, merge keys, custom tags, and cycles.
It also rejects non-finite numbers and mathematically integral values outside
JavaScript’s safe-integer range.
Negative zero normalizes to ordinary zero.

Plain date- and timestamp-looking YAML 1.2 Core scalars stay strings.
Quote or rewrite a value if a parser would otherwise create a YAML-specific runtime
type. Frontmatter fences use only CR, LF, or CRLF line breaks and exactly `---` with
optional ASCII space or tab.
Unicode line and paragraph separators are rejected as literal source characters rather
than treated as parser-specific fences.

Metadata mappings may carry namespaced extensions without a separate format version:

```yaml
softschema:
  contract: example.movies:MoviePage/v1
  schema: movie-page.schema.yaml
```

An `extensions` mapping is keyed by a canonical HTTPS namespace or lowercase reverse-DNS
name. Extension values are preserved portable data; they never load code or change core
validation.

## Schema and Identity Changes

A logical contract ID is no longer copied into JSON Schema `$id`.
`x-softschema.contract` continues to name the payload contract.
Supply a separate canonical HTTPS or URN schema identity with `schema_id`/`schemaId` or
`compile --schema-id` when reference resolution needs one.

New-profile validation is offline.
Fragment references remain available.
Other resources must be supplied as already-loaded in-memory mappings by canonical
absolute URI; validation never treats a URI as permission to retrieve it.
A narrow `legacy-0.2` profile accepts official older compiler output only with fragment
references and migration guidance.

JSON Schema `format` is annotation-only in the default portable profile.
Patterns must fit `portable-regex-v1`; unsupported lookaround, backreferences, named
groups, property escapes, inline flags, or ambiguous class operators fail as
`schema_invalid/pattern`. Character classes are normalized to merged ranges, and
matching uses bounded lazy-DFA caches plus one validation-wide work budget.
A schema-resource aggregate pattern limit fails as `schema_invalid/pattern`; runtime
work exhaustion fails deterministically as `schema_invalid/compile` rather than
returning an inexact match.

Document-declared `softschema.schema` paths containing C0 control characters or DEL now
fail closed as `schema_missing`. Replace such metadata with an ordinary relative path;
use the host-controlled `--schema` or library binding for an absolute schema location.

Recompile and review rather than editing `schema_sha256` by hand:

```bash
softschema compile package.model:Model \
  --contract example.docs:Report/v1 \
  --schema-id https://example.com/schemas/report/v1 \
  --out schemas/report.schema.yaml
```

Remove any model-supplied root `x-softschema` block before recompiling.
Version 0.3 reserves that root annotation for compiler-owned contract, profile, and
digest metadata and fails before writing if a model attempts to provide it.
Per-field annotations remain supported.

## Results, Batch Validation, and Exits

When discovery classifies one single explicit path as a regular file, JSON keeps the
legacy result shape and bytes, including when a later read fails.
A single explicit missing path or broken symlink keeps the legacy
`input_error/not_found` record as a narrow compatibility exception.
New result families are separate contracts:

- readable parse or validation failure exits 1;
- a missing, unreadable, unexpanded directory, invalid glob, or no-match discovery exits
  2;
- recursive discovery exceeding 64 directory levels or 100,000 encountered entries per
  operand exits 2 with `input_error/discovery_limit`;
- batch precedence is 2 for any input error, otherwise 1 for any readable failure,
  otherwise 0; and
- JSONL emits one self-contained diagnostic-v1 result per line and no summary line.

Directory discovery, multiple operands, and other discovery-input failures select
diagnostic-v1. An explicit FIFO, unsafe symlink target, or directory without
`--recursive` therefore produces an aggregate even when it is the only input record.
Use one explicit profile for the whole invocation:

```bash
softschema validate docs --recursive --profile frontmatter-md --format json
softschema validate data --recursive --profile pure-yaml --format jsonl
softschema validate docs --recursive --format sarif > softschema.sarif
```

Discovered symlinks are skipped.
Explicit symlinks to regular files are allowed after checks.
Includes and excludes are operand-relative portable globs and require `--recursive`. An
invocation has fixed aggregate pattern, token, static-complexity, and dynamic match
budgets. Static exhaustion is `match_work_limit`; candidate-dependent exhaustion is
`discovery_limit`. Directory revisits are suppressed by filesystem identity, and
discovery never returns a partial operand result after a traversal budget is exceeded.

Portable YAML now rejects ambiguous compact flow spellings such as `{a:}` and `[a:]`.
Write `{a: }` or `[a: ]` when the intended value is null.
Empty-value source locations are now identical across Python, Node, and Bun at flow
delimiters, comments, line ends, and EOF.

## TypeScript Changes

New code should import portable definitions from `softschema/core` and Node/Bun adapters
from `softschema/node`. The package root remains a compatibility facade during 0.3.

Bind a Zod model once so its serializable descriptor cannot drift from the executable
validator:

```ts
const descriptor = defineContractDescriptor({
  id: "example.movies:MoviePage/v1",
  model: "./model.js:MoviePage",
  envelopeKey: "movie",
  status: "enforced",
  profile: "frontmatter-md",
  schemaPath: "movie-page.schema.yaml",
});
const contract = bindContract(descriptor, MoviePage);
```

Node loads built `.js` and `.mjs` models.
Bun also loads direct `.ts`; this does not promise tsconfig path aliases or non-erasable
TypeScript syntax.

## Skill Installation Changes

Unmanaged, locally modified, unknown, or newer-format skill files are never overwritten.
Global installation is explicit and requires agent selectors.
Project installation outside a non-home Git repository requires
`--project --no-repo-check --dir PATH`.

Preview first:

```bash
softschema skill --install --project --dry-run --text
softschema skill --install --project --agent codex --agent claude --dry-run --text
```

The default project pair remains `.agents/skills/softschema/SKILL.md` and
`.claude/skills/softschema/SKILL.md`. See [Agent Compatibility](agent-compatibility.md)
for native targets and Aider’s explicit read recipe.

## Further Detail

- [softschema Spec](softschema-spec.md): normative grammar, limits, profiles, policies,
  and result contracts
- [API Reference](api.md): Python and TypeScript library entrypoints
- [Security Policy](../SECURITY.md): the 0.2.2 disclosure and trust boundaries
- [Changelog](../CHANGELOG.md): user-visible release delta

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
