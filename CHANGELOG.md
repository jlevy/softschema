# Changelog

All notable changes to softschema are documented here.
Both the Python (PyPI) and TypeScript (npm) packages release together under the same
version number.

## Unreleased

### Fixed

- **`doctor` recommends a prefix that works from the caller’s shell.** Run through
  `uvx softschema@latest` or `npx -y softschema@latest`, `doctor` found the runner’s own
  throwaway copy of `softschema`, which the runner had put on the `PATH` of the process
  it started, and recommended `softschema`, a command the caller’s shell cannot find.
  An agent following the skill’s advice to use the recommended prefix then failed.
  Both implementations now skip runner caches when looking for `softschema`: a uv cache
  bucket (`archive-v0`, `environments-v2`, `builds-v0`) under a root uv tagged with
  `CACHEDIR.TAG`, wherever `UV_CACHE_DIR` puts it, and npm’s `_npx/<hash>/node_modules`.
  They report `softschema: no` when only such a copy exists, and recommend the runner
  that started them when it is on `PATH`: `uvx softschema@latest` from the uv cache,
  `npx -y softschema@latest` from `_npx`. An installed `softschema` on `PATH` is still
  recommended first, and a recommendation always names a runner `doctor` lists as
  available. The TypeScript CLI also counts only executable files as runners now, as the
  Python CLI already did.

- **Python reads C-first only with `ruamel.yaml.clib`’s parser.** The C-first gate
  admitted any C parser that reported libyaml 0.1.7 on ruamel.yaml 0.18–0.19.
  `ruamel.yaml.clibz` reports the same version but is a different build, compiled with
  Zig and flagged for free-threading, and the differential search behind the C-first
  guards has never run on it.
  No released ruamel.yaml `YAML()` uses clibz, so no install changes mode today, but a
  patch release that switched to it would have turned C-first on for an unsearched
  build. The gate now also checks the parser’s module (`ruamel.yaml.clib._ruamel_yaml` or
  `_ruamel_yaml`): a clibz parser leaves every text to pure ruamel, and `doctor`’s
  `yaml_parser_reason` says clibz is not a checked build.
  When clibz is installed and `YAML()` does not use it, the reason says so.

- **The Python package excludes ruamel.yaml 0.19.0.** That release alone depends on
  `ruamel.yaml.clibz` by default, which compiles libyaml with Zig at install time, and
  its `YAML()` does not use it.
  The requirement is now `ruamel-yaml>=0.18,!=0.19.0`.

## v0.9.0—2026-10-26

This is a minor release (0.9.0): the portable YAML rule gains a normative rejection, and
documents that validated under 0.8.1 can now be refused.
Validation results now record actual execution independently for structural and semantic
checks. Declared `status` still selects validation mode; it does not prove a check ran.
The TypeScript package also moves to zod 4.6 and a patched `fast-uri`.

### Compatibility

**Newly rejected input.** Both implementations now reject, as `yaml_parse_error`, any
raw character outside YAML 1.2 `c-printable` (the C0 controls other than tab, line feed,
and carriage return; DEL; the C1 controls; U+FFFE and U+FFFF), the line separators
U+0085, U+2028, and U+2029, and a carriage return that does not begin a `\r\n` sequence,
anywhere in the YAML text they read: the frontmatter block or the pure-yaml document,
comments and keys included, and every compiled schema file, YAML or JSON. The Markdown
body is not checked.
What changes for each runtime:

- **TypeScript** previously read every one of these characters as content.
  Any of them in frontmatter or pure-yaml now exits 2 under `validate`.
- **Python** previously folded a raw U+0085 in a flow scalar to a space and kept a raw
  U+2028 or U+2029 there; a lone carriage return was a line break.
  Each is now rejected.
  The rest of the class was already a ruamel parse error.

Write such a character as an escape inside a double-quoted scalar: `"\N"` for U+0085,
`"\L"` for U+2028, `"\P"` for U+2029, `"\r"` for a carriage return, `"\f"`, `"\v"`,
`"\0"`, or `"\xHH"` for a control character.
Both engines decode every one identically.
`repair` writes the escape for a character inside a single-line scalar value (see
Added); one in a key, a comment, a block scalar, or a value that is not a scalar is
reported with its line and escape and left for the author, and a lone carriage return is
never escaped, since it may be a line ending.
To find affected files before upgrading:

```bash
rg -l '[\x{85}\x{2028}\x{2029}\x{FFFE}\x{FFFF}\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]|\r(?:[^\n]|$)'
```

**Tabs and a plain `=`.** A raw tab inside a plain scalar, or as spacing in block
context (after a key’s colon, before a comment, at the end of a value, on a blank line,
after a block scalar header such as `|`, after a closing quote, after a flow
collection’s closing bracket), was a parse error in Python and content in TypeScript;
TypeScript now rejects it too, as `yaml_parse_error` with its own message, while a tab
inside a quoted scalar, a block scalar’s content, or a comment, and as spacing between
the brackets of a flow collection, is accepted by both.
Write such a value as a quoted scalar.
A plain `=` was the YAML 1.1 `!!value` key in Python (a parse error) and the string `=`
in TypeScript; Python now reads it as the string `=`, as YAML 1.2 does.

**Flow continuation lines.** A later line of a flow collection or a quoted scalar in
block context that is not indented with spaces past its parent block, such as
`tags: [a,` followed by a line `<TAB>b]`, or an indented `title: "first` followed by a
line indented no further than `title`, was read by Python and a parse error in
TypeScript, as YAML 1.2 makes it.
Python now rejects it too, as `yaml_parse_error`. A blank line, a comment line inside a
flow collection, a closing bracket at the parent’s column, and every line of a root flow
collection (a JSON document indented with tabs) are still accepted by both.
Indent such a line past its parent with spaces.

**Implicit keys.** A flow-mapping key whose `:` is more than 1,024 characters after the
key starts, or on a later line, such as `{"<1,100 characters>": 1}` or `{"a"` followed
by a line `: 1}`, was a parse error in Python and read by TypeScript; TypeScript now
rejects it too, as `yaml_parse_error`. For a block-mapping key or a flow-sequence pair,
TypeScript counts the 1,024 in UTF-16 code units and Python counted characters, so a key
of more than 512 characters outside the Basic Multilingual Plane read in Python and
failed in TypeScript; Python now counts UTF-16 code units there too.

**Number forms outside the core schema.** A plain scalar that ruamel reads as a number
and the YAML 1.2 core schema as a string, or the reverse, was a number in one runtime
and a string in the other, silently: `1_000`, `1_0.5`, `0b101`, `-0x10`, `+0x10`, and
`-0o17` were numbers in Python and strings in TypeScript, and `.5e3` the reverse.
Both runtimes now reject such a scalar as `yaml_unsupported_scalar`, with a message
naming it; write the number in core form (`1000`, `0x10`, `0o17`, `500.0`) or quote it.
Core-form numbers, quoted scalars, and strings such as `1:30` and `yes` are unaffected.
A generated sweep of 350,355 number-like plain scalars in block values, sequence items,
keys, flow collections, and JSON arrays now finds no number the two runtimes read
differently.

**Indicators glued to flow scalars.** Inside a flow collection, a `:` with no space
after it before `,`, `]`, `}`, `[`, or `{` was part of the scalar in Python and a key
indicator in TypeScript, silently: `[a:, b]` was `['a:', 'b']` in Python and
`[{a: null}, 'b']` in TypeScript, and `{a:, b}` and `[a :, b]` differed the same way.
`[?a]` was an explicit key in Python and the string `?a` in TypeScript.
A bare `-`, a leading `:` in a flow mapping, `["a":1]`, a `#` right after a closing
quote or bracket (`"a"#c`), and, inside a flow collection, a `#` right after an opening
`[` or `{`, a `,`, or a `:` or `?` indicator (`[#c`, `[a,#c`) were read by one runtime
and refused by the other.
Both now reject all of these as `yaml_parse_error`; write a space after the `:` or `?`,
before the `#`, or quote the scalar.
For a glued `:` or `?` both runtimes now name the indicator’s line and column.
A generated sweep of 210,000 flow-collection scalars around `:`, `?`, `-`, `#`, and the
indicator characters, and a 160,000-case fuzz of flow and block structures, now find no
flow collection the two runtimes read differently, and none that one accepts and the
other refuses. The fuzz finds one remaining class, loud and unchanged: a block scalar
without an indentation indicator whose leading lines of only spaces are indented
differently from its first content line is refused by one engine and read by the other
(429 cases). Write an indentation indicator, or trim those lines.

**A block scalar at the end of the text.** A block scalar that ended the YAML text with
no line break after it read differently, silently: `body: |` as the last key of a
frontmatter block (whose last line the reader joined without its break), or at the end
of a pure-yaml file with no final newline, was `"line one\nline two"` in Python and
`"line one\nline two\n"` in TypeScript, and `>` and `|+` the same.
Both readers now hand the parser the text with its final line break, so **Python’s value
changes**: clip (`|`, `>`) and keep (`|+`, `>+`) chomping end with `"\n"` there, as they
do anywhere else in a document; strip (`|-`, `>-`) is unchanged, and TypeScript’s values
are unchanged. A model with `pattern: ...$` or a `maxLength` on such a field may see the
extra character; write `|-` to keep a value without its final line break.

**Spaces under an explicit indentation indicator.** In a block scalar with an explicit
indentation indicator (`|2`, `>1`), a line of only spaces wider than the indentation the
indicator sets was content in Python (as YAML 1.2 reads it) and an empty line in
TypeScript, silently: `key: >1` followed by a line of four spaces read as three spaces
and a line break in Python and as an empty string in TypeScript.
Both runtimes now reject it as `yaml_parse_error`; trim the line or drop the indicator.
A line of only spaces no wider than that indentation, and every such line in a block
scalar without an indicator, is unaffected.

**Mapping entries with content but no `:`.** An entry that has a value, a tag, or an
anchor but no `:` before it, such as an explicit key `- ? k` followed by a sequence item
`- x` under it, or `{"a": b, ""!}`, was a parse error in Python and read by TypeScript
with that content left out.
TypeScript now rejects it too, as `yaml_parse_error`.

**Depth limit.** TypeScript now counts an empty collection toward the 64-collection
limit and reports the limit before a duplicate key earlier in the text or a parse error
later in it, as Python does: an empty `[]` that is the 65th open collection was
accepted, and a document past the limit with a duplicate key was `yaml_duplicate_key`.
Both are `yaml_limit` in both runtimes, while a tag, a merge key, or another refusal
earlier in the text than the deep collection is still reported first.

**Directives.** `%YAML 1.1` switched both engines to YAML 1.1 schemas that differ (`08`
was a string in Python and 8 in TypeScript, and a date a string in one and an
unsupported host value in the other); `%YAML 1.0` and `%YAML 1.3` crashed the Python
reader with an assertion; and an unknown directive such as `%FOO` was ignored by Python
and refused by TypeScript.
Both runtimes now accept only `%YAML 1.2` and `%TAG` and reject any other directive as
`yaml_parse_error`.

**Integer negative zero.** The integer literal `-0` (also `-00`, and `-0` in JSON text)
read as `0` in Python and was rejected as `number_negative_zero` in TypeScript; Python
now rejects it too, as the spec’s negative-zero rule says.
`+0` and the string `'-0'` are unaffected.

**Fence lines.** A frontmatter delimiter is `---` plus trailing spaces or tabs only.
Python previously also trimmed U+0085 and U+001C–U+001F, and TypeScript U+FEFF, so a
`---` followed by one of those opened a fence in one runtime and not the other; now it
is a fence in neither.

**Escaped surrogate pairs.** A surrogate pair written as two `\u` escapes
(`"\ud83d\ude00"`) is the one character it encodes in both runtimes, as in JSON; Python
previously rejected it as a lone surrogate.

**Message and `kind` changes.** `message` text may change within a minor release, and
these did; `kind` is the matching key:

- Every `line N, column M` in a frontmatter-md diagnostic now counts from the top of the
  file (the opening fence is line 1), in the preflight and engine messages alike; it was
  block-relative. Pure-yaml line numbers are unchanged.
- An engine error at the end of the YAML text (an unclosed `[`) now names the start of
  the line after the text’s last line, since the text is parsed with its final line
  break: in frontmatter, the closing fence’s line.
- The preflight message names the escape to write.
- A path in a human-readable message (the backticked document name) has C0/C1 controls
  and DEL written as `#xHHHH`.
- A `schema_invalid` record whose schema the reader refused, or whose root is not a
  mapping, now begins with the backticked schema path.
- `repair` without `--contract` reports a fenceless document, an empty block, or a
  pure-yaml list or scalar root with validate’s `kind` (`no_frontmatter`,
  `yaml_not_mapping`) and message; it said `yaml_parse_error`.
- `compile --check` reports a committed sidecar the portable reader refuses as drift
  (exit 1, `drift_diff` naming the file) rather than raising a usage error (exit 2).

**New record code.** `repair` emits `repair_applied` records with
`code: yaml_escaped_character`; a consumer matching repair codes exhaustively should add
it.

**Compiled schemas.** `compile` output changes only for a model whose text carries one
of the rejected characters, a carriage return, a tab, or is exactly `=`: such strings
are now double-quoted with escapes, so the sidecar one writer produces reads back in
both runtimes with the model’s content (a 4,686-case writer-to-other-reader sweep over
U+0000–U+02FF and the separators in six scalar shapes finds no remaining difference).
`schema_sha256` is computed over canonical JSON, so the escaping leaves it unchanged for
every schema.

**Zod 4.6 in TypeScript.** The TypeScript package now requires zod `^4.6.6`. String
length bounds, strict-object refinements, and `z.iso.datetime()` change behavior, and a
TypeScript model using one of the constructs listed under Changed (tuples,
intersections, records with typed keys, and `z.email()` among them) compiles to a new
`schema_sha256`; recompile its committed schema.

**Execution evidence and schema refusals.** Python layer-result constructors require an
explicit keyword-only `execution`; TypeScript layer interfaces require the same field.
Ordinary validation call signatures, `ok`, outcomes, errors, CLI exit classes, artifact
metadata, and compiled schema files are unchanged except for the corrected repair-result
verdicts (see Fixed), the Zod 4.6 model behavior (see Changed), the portable-reading
changes above, and the schema refusals below, each of which turns an artifact bound to
such a schema `invalid` (`ok` false, `validate` exit 1, under every status, with or
without `--require`) until the schema is fixed.
They affect hand-written or third-party schemas only; schemas written by
`softschema compile` carry the canonical `$schema` and absolute ids and use none of the
refused keywords. **Python users** are the ones who change for an unresolvable `$ref` on
a branch the payload never reaches (TypeScript already refused it; remove or fix the
reference), for a `$schema` line naming draft-07 or another draft, which Python used to
accept and validate as 2020-12 (TypeScript already refused it, now under
`reason: dialect` rather than `compilation`; delete the line or set the 2020-12 URI),
and for `$recursiveRef`, which Python ignored and TypeScript evaluated (write
`$dynamicRef`). **Both runtimes** change for the legacy `dependencies` keyword, which
TypeScript enforced and Python ignored (write `dependentSchemas` or
`dependentRequired`), for OpenAPI `nullable`, which TypeScript honored and Python
ignored (write `type: [..., "null"]`), and for any resource identity outside the
identity grammar, which both now refuse as `reason: resource_identity` and
`compile --schema-id` refuses too.
Before, the engines read such identities differently: a relative root `$id` against
different invented bases; `URN:`, `urn:Ex:…`, an uppercase host, `%7E`, or a dot
segment, which fast-uri normalizes and Python does not; a whitespace-prefixed id, which
Python’s `urlsplit` trims; a malformed host such as `http://[::1`, which Python refused
as `compilation` and TypeScript accepted; and `urn:example` or `urn:dir/item.json`,
which TypeScript failed to compile.
Ordinary-looking ids it also refuses: `https://example.com` with no path (write
`https://example.com/`), an explicit default port as in `https://example.com:443/x`, an
uppercase `urn:uuid:6E8BC430-…`, a trailing empty `#` as in
`http://example.com/schema#`, common in draft-07-era schemas, and `s3://` or `gs://`
ids, since only `http`, `https`, and `file` take `//host`. Write `https://host/path`,
`file:///path`, `urn:<nid>:<name>` in lowercase, or another `scheme:path`, with no
fragment. Skip reasons change only for the TypeScript library fix under Fixed.
Strict serialized-result consumers must accept the new layer fields and remove the
unreleased aggregate field.
Old reports without execution fields have **unknown** execution; preserve absence or
revalidate rather than fabricating evidence.
See the
[migration plan](docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md)
for downstream adoption and release sequencing.

Compiled schema files also change for one TypeScript construct.
A model with a `.default()` over a transforming schema, or an authored `default` or
`examples` on one, compiles to a new schema and `schema_sha256`, because the field gains
the `default` or `examples` that 0.8.1 dropped under zod 4.4 and 4.6 (see Fixed).
`compile --check` reports drift for such a model; recompile its committed schema.
The new schema is the one its Pydantic mirror compiles to.
This fix changes no compiled schema without a transform, and no Python-compiled schema.
A `.catch()` whose value the referenced `$defs` entry already carries compiles as in
0.8.1, to the bare `$ref` Zod writes; only the unreleased #66 wrote the value beside it.

### Added

- `structural.execution` and `semantic.execution` on all returned validation records,
  including CLI JSON and repair results.
  The public `ValidationExecution` type is `not_run`, `completed`, or `errored`. A
  completed check may accept or reject; read `ok` and errors for its verdict.
  Missing or malformed schemas report preparation failure without claiming payload
  evaluation. Both checks remain visible when a schema accepts and a model rejects.
- Two advisory warnings when effective mode is `enforced` and structural validation did
  not complete: `document-enforcement-via-model-only` if semantic validation completed,
  or `document-enforcement-not-applied` otherwise.
  Failures before payload extraction do not emit a payload-check shortfall warning.
- An opt-in requirement for completed checks: `require=` on Python `validate_artifact`,
  `load_artifact`, and `validate_values`, a `require` option on their TypeScript
  counterparts, and a repeatable `validate --require structural|semantic` in both CLIs.
  A required layer that did not complete is not ok and gains a `check_not_completed`
  error carrying `layer` and `execution`. An otherwise valid result becomes `invalid`,
  strict reads raise or throw, and `validate` exits 1 for readable invalid artifacts.
  An unreadable artifact retains the library’s `input_error` outcome and the `validate`
  command’s exit 2. Without a requirement, results are unchanged.
- **`repair` escapes a raw character the portable rule rejects.** A U+0085, U+2028,
  U+2029, or control character other than a carriage return inside a single-line scalar
  value is rewritten as a double-quoted scalar carrying the YAML escape, with one
  `yaml_escaped_character` record per value naming each character and its escape.
  The decoded value is exactly what YAML 1.2 gives the raw text; no character is
  replaced by a guess at what was meant (a mis-decoded cp1252 ellipsis stays a visible
  U+0085). Plain, single-quoted, and double-quoted values are handled, trailing comments
  and the author’s own escapes are kept.
  Only a scalar value is rewritten: a flow collection, a comment, an anchor, an alias,
  or a tag is left alone, a rejected character in a key, a comment, or a block scalar
  (whatever its key looks like) stays a parse error, and a lone carriage return is never
  escaped, because it may be a line ending and the text after it another line.
  Both implementations.

### Changed

- Replace the unreleased `enforcement_applied` hierarchy with per-layer execution.
  TypeScript now reports actual model invocation independently of its optional label.
- The spec defines execution boundaries, including preparation versus evaluation
  failures, and the effective status fallback to `soft`.
- Python schema preparation resolves every `$ref` that evaluation could reach before
  checking a payload, as Ajv already did while compiling.
  A schema with an unresolvable local or remote reference on a branch the payload never
  reaches is now `schema_invalid` (`reason: reference`) with structural `not_run` in
  both runtimes, instead of a Python-only completed acceptance, so
  `--require structural` gives one answer.
  The walk follows the applicators both engines evaluate; a definition nothing
  references, a `contentSchema` annotation, and a `then` or `else` with no `if` are not
  checked in raw mode.
  The remaining engine differences on degenerate schemas are pinned as
  `engine_deviations` in the shared vectors and listed in the spec.
- Both runtimes refuse, before either engine runs, a `$schema` other than the canonical
  Draft 2020-12 URI (with or without a trailing `#`) and the keywords only Ajv honored
  while jsonschema ignored them: the legacy `dependencies`, the OpenAPI `nullable`, and
  2019-09’s `$recursiveRef` and `$recursiveAnchor`, each as `schema_invalid` with
  `reason: dialect`. Write `dependentSchemas` or `dependentRequired`,
  `type: [..., "null"]`, and `$dynamicRef`/`$dynamicAnchor` instead.
- Every resource identity (the root `$id`, a nested `$id`, a supplied resource’s `$id`
  or key, and `softschema compile --schema-id`, which is `schema_id`/`schemaId` in the
  libraries) follows one grammar, implemented identically in both runtimes, and anything
  outside it is `schema_invalid` with `reason: resource_identity` before either engine
  runs (compile exits 2 with the same message).
  The grammar admits only spellings that neither Python’s `urllib.parse` nor Ajv’s
  fast-uri rewrites: printable ASCII, no fragment (not even an empty `#`), uppercase
  `%HH` escapes of reserved or non-ASCII bytes only, a lowercase scheme, `//host` only
  for `http:`, `https:`, and `file:` (lowercase host or canonical IP address,
  non-default port, no user information, a path of at least `/`), the opaque
  `scheme:path` form for every other scheme except those `urllib.parse` writes with
  `//`, a lowercase `urn:` namespace identifier and a lowercase UUID after `urn:uuid:`,
  and no `//`, `.`, or `..` path segment, trailing `;`, empty query, or `'` in a query.
  A nested `$id` may also be a relative path.
  The spec lists the rules and `tests/vectors/identities.yaml` has a case for each.
- The TypeScript `validate --require` with an unknown layer reports
  `softschema validate: invalid require: <value>` with the usual exit 2, the prefix the
  Python CLI uses, instead of the argument parser’s own line.
- Checked enforcement accepts nested nullable references to explicitly closed models
  without adding redundant object closure to their nullable wrappers.
  Explicit open object policy and rejection of unknown fields remain owned by the
  referenced model.
- **CI runs the dependency audit as its own `dependency-audit` job.** `bun audit` used
  to be a step inside the `typescript` job, so a new upstream advisory skipped the
  TypeScript typecheck, tests, build, publint, and golden runs on every PR. The audit
  now has its own check, and the TypeScript results always report on the change under
  review. Until `dependency-audit` is a required check, the `typescript` job repeats the
  audit as its last step so an advisory still blocks merging.
- **The `typescript` and `cross-impl` CI jobs are hardened like `dependency-audit`.**
  Their checkouts no longer persist the token, which neither job uses afterward, and
  they install with `--ignore-scripts`; no dependency of the TypeScript package runs an
  install script, so the builds and tests are unchanged.
- **Zod 4.5 and 4.6 semantic behavior applies to TypeScript models.** String `.min()`,
  `.max()`, and `.length()` count code points rather than UTF-16 units, matching
  Pydantic. An object-level `.refine()` or `.superRefine()` on a strict object now runs
  when the input has an unknown key, and reports its issue alongside the unknown-key
  issue; a Pydantic `model_validator(mode="after")` on an `extra="forbid"` model does
  not run in that case (refinements are outside `schema_sha256`). Field-level issues
  were already reported alongside an unknown key.
  `z.iso.datetime()` rejects minute-precision input such as `2020-01-01T06:15Z`, which
  Pydantic accepts (temporal acceptance sets were already allowed to differ).
- **Zod 4.5 and 4.6, with the compiler’s normalizations of their output, change the
  compiled schema and `schema_sha256` of TypeScript models that use these constructs;
  recompile their committed schemas.** `compile --check` reports drift for them after
  upgrading. `.startsWith()`, `.endsWith()`, `.includes()` without a position, and
  `.catch()` object fields still compile as they did under zod 4.4 (see Fixed).
  The KitchenSink parity fixture now covers the three helpers and closed tuples, and a
  unit test pins the output of the other constructs below.
  - `z.tuple([...])` with elements gains `minItems` and `maxItems`, and a rest tuple
    gains `minItems`. The compiler drops the `items: false` Zod also adds, which
    `maxItems` already implies, so `z.tuple([z.string(), z.int()])` compiles to the same
    schema as Pydantic’s `tuple[str, int]`.
  - An empty tuple drops `prefixItems: []`, which constrains nothing: `z.tuple([])`
    compiles to `minItems: 0` and `maxItems: 0` as Pydantic’s `tuple[()]` does, and an
    empty tuple with a rest schema compiles as `z.array()` of it, Pydantic’s
    `tuple[int, ...]`.
  - `z.intersection(A, B)` and `A.and(B)` of inline objects fold into the one object
    they describe, the shape a Pydantic model with both sets of fields emits; the old
    `allOf` of two strict objects accepted no value.
    A member registered with `.meta({ id })` is a `$ref`, so an intersection with one
    still emits an `allOf`.
  - `z.record(z.number(), V)` and `z.record(z.int(), V)` constrain keys with a `pattern`
    instead of `propertyNames: {type: number}`, which rejected every non-empty object.
    Pydantic’s `dict[int, V]` emits no key constraint, so the two still differ; matching
    it would drop a key constraint Zod enforces.
  - A record’s key schema no longer carries `type: "string"`, which every JSON key
    satisfies, so a record with enum, literal, or constrained string keys changes
    digest. A record with enum or literal keys and an optional, defaulted, or `.catch()`
    value also no longer lists every key in `required`. With both changes,
    `z.record(z.enum(["a", "b"]), V.optional())` equals Pydantic’s
    `dict[Literal["a", "b"], V]`, and `z.record(z.string().min(2), V)` equals
    `dict[Annotated[str, Field(min_length=2)], V]`. With required values, an enum-keyed
    record still requires every key, as Zod’s runtime does and Pydantic’s does not, and
    a `.regex()` key still differs from Pydantic’s `patternProperties`.
  - A union with duplicate members, such as `z.union([z.string(), z.string()])`,
    collapses to the one member, and `.nullable().nullable()` emits one flat `anyOf`;
    both now equal Pydantic.
  - A `z.preprocess()` field is listed in `required`, as a Pydantic field with a
    `BeforeValidator` and no default is.
  - A second `.multipleOf()` is kept in an `allOf` instead of being dropped.
  - Zod’s built-in patterns for `z.email()`, `z.emoji()`, `z.ulid()`, `z.cidrv6()`, and
    `z.base64url()` changed, and `.includes(text, { position })` now emits `^.{n,}text`,
    which matches `String.prototype.includes`.
  - `z.ipv4()` or `z.ipv6()` followed by another format check takes that check’s format,
    as every other helper already did: `z.ipv4().lowercase()` emits `format: lowercase`
    and `z.ipv4().regex(...)` emits none.

### Performance

- **A strict JSON document is parsed with `json`** when ruamel would read it
  identically, so a large `.json` artifact validates many times faster.
  YAML input, and every text on which JSON and YAML 1.2 can disagree, keeps the ruamel
  path, so values, types, key order and error codes do not change.
  The path runs only at a ruamel release the guards were checked against (0.18 and
  0.19).
- **YAML is parsed by ruamel’s optional C extension where it reads exactly as the
  pure-Python parser**, several times faster, when `ruamel.yaml.clib` is installed and
  is the libyaml build softschema was checked against.
  Every other text, and every text libyaml fails on, is read by the pure parser, so
  values and errors do not change.
  `yaml_parser_mode()` and `softschema doctor` report which parser is active, and
  `SOFTSCHEMA_PURE_YAML=1` turns the C parser off.
  Compiled schemas are always written by the pure-Python emitter.
- **The TypeScript reader is linear in the width of a mapping.** The `yaml` package’s
  own duplicate-key check compares each key with every earlier key of its mapping, so a
  0.4 MB block mapping took 6 s and grew with the square of its width; duplicates are
  now found in one pass with a set per mapping, with the same `kind`, message, and
  position, and the same document takes 0.4 s.

### Fixed

- Python `repair_and_validate_artifact(..., model=...)` uses the supplied model for both
  conformance and the final verdict.
  A model rejection now returns `invalid` after repair rather than validating against
  the caller’s model-free contract.
  The caller’s contract is unchanged.

- TypeScript repair results for a missing or invalid-UTF-8 artifact without an inferred
  contract report `input_error`, matching Python and other library reads.
  Parse failures remain `invalid`.

- TypeScript `validateArtifact` without a bound schema reports structural
  `skipped_reason: inferred_via_model` only when the call supplies a `semanticModel`, as
  Python does. A `Contract.model` label alone reports `no_schema`, and a semantic model
  without a label reports `inferred_via_model`. The CLI output is unchanged because
  `--model` sets both.

- Python `validate_values(schema=...)` with a schema file that does not exist reports
  `schema_missing` with the path, as artifact validation does, instead of
  `schema_invalid` with the operating system’s message.

- **TypeScript-compiled schemas match Pydantic again for nullable fields under zod 4.5
  and later.** Zod 4.5 began rewriting `anyOf: [{type: "string"}, {type: "null"}]`, what
  `.nullable()` and a union of plain primitives emit, as `type: ["string", "null"]`. The
  two forms validate identically, but Pydantic emits `anyOf`, so a model with a nullable
  field compiled to different canonical content and a different `schema_sha256` than its
  Python mirror. The published `^4.4.3` range already admitted those zod versions.
  The compiler now expands every `type` array back into `anyOf` branches before
  canonicalization; the committed reference schemas and goldens are unchanged.

- **TypeScript-compiled schemas match Pydantic again for `.startsWith()`, `.endsWith()`,
  and `.includes()` under zod 4.6.** Zod 4.6 writes each check’s name (`starts_with`,
  `ends_with`, `includes`) as the string’s `format`. No JSON Schema vocabulary defines
  those names and Pydantic never emits them, and the name replaces a real format written
  by an earlier check: `z.email().startsWith("a")` lost `format: email`. The compiler
  now removes the three names and restores the earlier format, so each helper compiles
  to the bare `pattern` that the `.regex()` spelling and a Pydantic `Field(pattern=...)`
  mirror emit, with the same `schema_sha256` as under zod 4.4. Only a format Zod
  generated is corrected: an authored `.meta({ format })` is kept whatever its name.
  Each other string helper zod 4.4 already had, used alone, emits the same `format` as
  under zod 4.4.

- **TypeScript-compiled schemas match Pydantic again for `.catch()` under zod 4.6.** Zod
  4.6 lists a `.catch()` field in `required` because its inner type is required,
  although Zod’s runtime fills an absent key with the catch value and the field’s
  Pydantic mirror, `f: str = "x"`, is not required.
  It also drops the catch value from `default` when the caught type transforms, which
  zod 4.4 and the Pydantic mirror, a defaulted field with an `AfterValidator`, keep.
  The compiler removes such a field from `required` again, including behind
  `z.preprocess()` and in `$defs`, and restores the `default`, so these fields compile
  as under zod 4.4, with the same `schema_sha256` as the Pydantic mirror.
  A record whose value has a `.catch()` no longer requires its enum or literal keys,
  since Zod’s runtime fills each one and a Pydantic `dict` never requires its keys.
  A tuple element with a `.catch()` still counts toward `minItems`, as an element of
  Pydantic’s `tuple[...]` does, although Zod’s runtime fills a missing trailing element;
  Pydantic cannot default a tuple element.

- **TypeScript-compiled schemas keep the `default` of a `.default()` over a transform,
  and an authored `default` or `examples` on one, as Pydantic does.** In input mode zod
  4.4 and 4.6 drop the `default` of a schema that transforms, so
  `z.string().transform(f).default("x")`, a `.default()` over `z.preprocess()` or
  `.pipe(z.transform(f))`, and an object default whose fields transform compiled without
  their `default`. The Pydantic mirror, `Annotated[str, AfterValidator(f)] = "x"`
  (`BeforeValidator` for `z.preprocess()`), keeps it.
  The compiler now restores the value, including in a record value and in `$defs`, so
  each such field compiles to the same schema and `schema_sha256` as the plain
  `.default()` and its Pydantic mirror.
  The value is written as given, because neither Zod nor Pydantic runs the transform on
  a default, and it is checked like every other default (see below).
  Zod drops an authored `.meta({ default })` or `.meta({ examples })` from a
  transforming schema the same way, while the Pydantic mirror, an `AfterValidator` field
  with `Field(examples=[...])` or `Field(json_schema_extra={"default": ...})`, keeps it;
  the compiler restores those too.
  A schema’s own value also wins over one it inherits from a transforming inner type, so
  `z.string().transform(f).default("a").default("b")` and its `.catch()` form compile
  with `default: "b"`, as they do without the transform.
  Only a value Zod dropped is restored, so a schema without a transform keeps the
  `default` and `examples` Zod writes.
  On a field that references a `$defs` entry, a restored value is left out when the
  first entry along the `$ref` chain that has the key carries the same value, so
  `X.describe("d")` compiles alike whether or not the id’d `X` transforms.
  Zod compares only one level, so where it writes a `default` or `examples` beside a
  `$ref` whose chain already carries the same value, the transforming twin leaves that
  value out: an alias such as `R.default("x").meta({ id })`, a wrapper between the field
  and its `$ref` such as `R.optional().default("x")`, or a second `.describe()` or
  `.meta()` clone such as `R.describe("a").describe("b")`. Validation is the same, and
  such shapes have no Pydantic mirror.
  The KitchenSink parity fixture now covers a defaulted transform.

- **TypeScript compile rejects a default that canonical JSON cannot carry, as Python
  compile does.** A NaN or infinite `.default()`, `.prefault()`, `.catch()`, or authored
  `default` used to compile to `default: null`, because Zod’s final JSON copy of the
  schema turns non-finite numbers into `null`. It now fails with
  `canonical JSON requires finite numbers` and the schema path of the value, as the
  Python compiler fails on a NaN or infinite default.
  An authored `examples` value is checked the same way.
  A BigInt `.catch()` value or example fails with a named error instead of Zod’s
  `Error converting schema to JSON.` A `Date` value is still written as its ISO string.

- **Python `compile` no longer restyles the host process’s own YAML output.** The Python
  package now requires `frontmatter-format>=0.5.0`. The compile writer comes from
  `frontmatter_format.new_yaml`, which in 0.4.0 registered its `dict` and `str`
  representers on ruamel’s shared `SafeRepresenter`, so after a compile every
  `YAML(typ="safe")` dump in the same process wrote mappings in block style and
  multi-line strings as `|-` block literals.
  frontmatter-format 0.5.0 keeps each writer’s representers on a private subclass.
  Compiled schema files are unchanged.

- **`compile` writes schemas the portable reader accepts.** Both writers emitted U+0085,
  U+2028, and U+2029 raw (ruamel single-quoted, the `yaml` package plain or
  double-quoted), so a model whose description, default, or enum value carried one
  produced a sidecar every later read refused as `schema_invalid`. Each writer now
  forces such a string (keys included) into double-quoted style and writes the escape
  both engines decode; `compile` runs the reader’s preflight on its own output; and
  `compile --check` reports an unreadable committed sidecar as drift.
  The cross-language parity fixture carries these characters in a description, a
  default, and an enum value.
  Two older holes of the same kind are closed: the Python writer wrote a string holding
  a CRLF as a block literal, which both readers normalize to `\n`, so the sidecar’s
  content differed from the model and `compile --check` reported drift on fresh output
  (such strings are now double-quoted, `"a\r\nb"`); and the TypeScript writer wrote a
  tab inside a plain scalar, and a bare `=`, which ruamel refuses (both are now
  double-quoted). The parity fixture carries a CRLF, a tab, and `=` as well.

- **Conform never folds a raw U+0085.** The conform pass loaded the YAML region through
  the round-trip loader, which skipped the preflight; ruamel folds the character to a
  space, so Python `repair --contract … --schema …` on a document `validate` rejects
  retyped a scalar beside the fold, wrote the folded text with no record of it, and
  reported `valid`. Conform now runs the preflight before loading, in both runtimes.
  The TypeScript round-trip emitter also re-escapes these characters on output, so a
  retype beside an escaped `\N` no longer undoes the escape.

- **Fence lines trim one explicit set.** See Compatibility; six `fence_scan` vectors pin
  the agreement.

- **The quoting pass trims one explicit set too.** `repair`’s older quoting pass trimmed
  a value with each host’s default whitespace set (U+0085 is whitespace to Python,
  U+FEFF to JavaScript), so a rejected character in the comment of a line that needed
  quoting was dropped from the file in one runtime and refused in the other.
  Both passes now trim space and tab only and treat only `[ \t]+#[ \t]` as a comment;
  such a line stays a parse error in both runtimes.

- **Tabs in plain scalars and a plain `=` read the same in both runtimes.** See
  Compatibility.

- **A tab after a block scalar header, a closing quote, or a flow collection’s closing
  bracket, an under-indented flow continuation line, a long or multi-line implicit
  flow-mapping key, an astral block key past 1,024 UTF-16 code units, and an integer
  `-0` get one verdict in both runtimes.** Each was read by one runtime and a parse or
  value error in the other; see Compatibility.
  Shared `portable_values` vectors pin every case.

- **A number form only one engine reads as a number is refused in both runtimes**
  instead of reading as a number in one and a string in the other; see Compatibility.

- **A collection used as a mapping key no longer crashes the Python reader.** A key such
  as `[?]` in `{[?]}` made ruamel’s constructor raise a bare `TypeError` (an unhashable
  key) that escaped `validate`; it is now `yaml_non_string_key`, as in TypeScript.

- **A raw rejected character right after a backslash in a double-quoted value is left
  for the author.** `repair` escaped it anyway, writing `"a\\x01b"` for `"a\<U+0001>b"`,
  which reads as a backslash and the letters `x01`, and reported the document repaired.
  Such a value is now left unrepaired with its parse error, in both runtimes; after an
  escaped backslash (`\\`) the character is escaped as before.

- **A schema file is named once in its diagnostic.** An invalid-UTF-8 compiled schema
  was reported as `` `s.yaml`: `s.yaml`: input is not valid UTF-8 ``, and
  `compile --check` named the sidecar twice the same way; the reader now names the file
  once, whichever step refused it.

- **An unexpected exception in the TypeScript YAML reader is no longer reported as a
  YAML parse error.** It reaches the caller as itself.

- **A `%YAML 1.0` or `%YAML 1.3` directive no longer crashes the Python reader.** ruamel
  raised an `AssertionError` that escaped `validate` as a traceback; the directive is
  now a `yaml_parse_error`, as in TypeScript.

- **Control characters in a filename never reach stderr raw.** A document name in a
  human-readable message is written through one helper per runtime that escapes C0/C1
  controls and DEL as `#xHHHH`, so a hostile filename in a third-party corpus cannot
  drive the terminal (an OSC title or clipboard write, a cleared and overwritten line, a
  forged second diagnostic).
  JSON output already escaped them.

- **The TypeScript preflight’s error path no longer materializes the input** to count
  the line and column (about 4x peak memory on a large single-line input); it counts
  with index loops, as Python does.

- **Diagnostics are easier to act on.** Frontmatter line numbers count from the top of
  the file, the preflight message names the escape, and a `schema_invalid` message names
  the schema file (the record’s `path` is the artifact).

- **`repair` without `--contract` uses validate’s kinds** for a document that reads but
  holds no mapping; see Compatibility.

- **A surrogate pair written as two `\u` escapes decodes to one character in Python**,
  as it already did in TypeScript and as JSON reads it.

- **The sdist no longer ships `AGENTS.md`.** The file carries repository policy for
  agents working in this repository, not package documentation; a consumer vendoring the
  sdist tree would otherwise place it inside their own repository.
  The wheel and npm package never included it.

- **`repair` no longer changes how other ruamel emitters spell `null`.** The round-trip
  emitter behind `repair` registered its null representer through a stock
  `YAML(typ="rt")` instance, and ruamel’s `add_representer` writes to the shared
  `RoundTripRepresenter` class.
  After the first repair, every round-trip emitter in the same process — a host
  application’s own included — wrote `null` where ruamel writes an empty value.
  The representer now lives on a softschema-private subclass, so the repair emitter no
  longer touches ruamel’s shared classes.
  Python only: the TypeScript emitter is configured per call and has no shared state to
  leak.

- **A YAML parse failure names the artifact.** The YAML engines say where in the text
  they stopped, not which text: ruamel reports `in "<unicode string>", line 4` and the
  `yaml` package a line and column alone.
  softschema’s own fence messages already named the document, but an engine failure in
  either profile — and every failure in a pure-yaml artifact — did not, so an agent
  repairing a batch could not tell which file a `yaml_parse_error` record was about.
  The `validate` diagnostic and the `yaml_parse_error` record now begin with the
  backticked document path, followed by the engine’s message, in both profiles, both
  commands, and both implementations.
  softschema’s own messages that name a document (an unterminated fence, non-mapping
  frontmatter, a document with no frontmatter or a non-mapping root) use the same
  backticked prefix, and the non-UTF-8 diagnostic, which named no file, now names it
  too. The record `kind` is unchanged; anything matching the engine’s message from its
  first character, or one of softschema’s own messages in full, needs its pattern
  widened.

- **`repair` reports a non-UTF-8 artifact the way `validate` does.** Without
  `--contract`, the record `repair` built for a file that is not UTF-8 carried repair’s
  raw `invalid_utf8` code as its `kind` and the verdict `invalid`, where the same file
  under `--contract`, and under `validate`, is `artifact_invalid_utf8` at `input_error`.
  Repair’s error code now goes through the same code-to-kind rule validation applies, in
  both implementations, and the TypeScript result for a contract-less unreadable
  document derives its `outcome` from the record kind as Python does.

- **The Python frontmatter reader splits lines the way TypeScript does.** It used
  `str.splitlines()`, which also breaks on U+2028, U+2029, U+0085, form feed, and the
  ASCII separators. A frontmatter scalar containing one was cut into lines the YAML
  engine could not parse, so Python `validate` exited 2 with a parse error where
  TypeScript read the document and reached the contract verdict.
  Both readers now split on `\n` alone and drop a trailing `\r`, the rule the repair
  fence scan already used.

- **Raw control and line-separator characters are a portable input error in both
  runtimes.** The two YAML engines read them differently: ruamel rejects every character
  outside YAML 1.2 `c-printable` (form feed, vertical tab, the ASCII separators, DEL,
  the C1 controls) and treats U+0085, U+2028, and U+2029 as YAML 1.1 line breaks,
  folding a NEL in a flow scalar to a space and breaking a block scalar or a comment
  into a parse error, while the `yaml` package reads all of them as content.
  So a form feed in a frontmatter scalar failed Python `validate` and passed TypeScript,
  and a mis-decoded cp1252 ellipsis (U+0085) silently became a space in Python and
  stayed a character in TypeScript.
  Both runtimes now reject any of these characters as raw text anywhere in the YAML they
  read (the frontmatter block or the pure-yaml document, comments and keys included)
  with one `yaml_parse_error` message naming the character, line, and column; written as
  a double-quoted escape (`"\f"`, `"\N"`, `"\L"`), every one of them decodes identically
  in both. The spec records the rule under Portable YAML Values.

### Security

- **The `fast-uri` override is raised to exactly 3.1.9.** It closes seven advisories
  against the 3.1.6 pin, a transitive dependency of the TypeScript implementation’s
  schema validator (`ajv`): GHSA-qw65-cvwx-89v3 (authority injection through an
  unvalidated port), GHSA-58mr-gqgx-xq4g (host confusion through an unclosed bracket),
  GHSA-hrr3-gc8f-f4qj (inconsistent host case normalization), GHSA-w74x-v6f9-j3xg
  (scheme spoofing through percent-encoded scheme decoding), GHSA-wjr9-j795-jxcr (host
  confusion through unchecked WHATWG host canonicalization), GHSA-xhq7-xmqj-769h
  (improper path equivalence in relative reference normalization), and
  GHSA-333x-w4r6-6crp (scheme injection through an unescaped first-segment colon).
  3.1.9 was published 2026-10-19, inside the 14-day cool-off; it is installed under a
  maintainer-approved exception, pinned exactly, as the only 3.x release that clears all
  seven. The override applies only to this repository’s own install, for development and
  CI. npm and Bun ignore the `overrides` of a dependency, and the published package does
  not bundle `fast-uri`, so a project that installs softschema gets the `fast-uri` its
  own lockfile resolves for `ajv`; update it to 3.1.9 or later there.
  No softschema API or artifact change is involved.
- **The TypeScript package requires zod `^4.6.6`** (locked at 4.6.6), which closes
  GHSA-mrhx-c7xc-m3w5: validating an oversized array, set, or map against a size bound
  could exhaust memory, because Zod parsed every element before checking the bound.

## v0.8.1—2026-09-11

A patch release. Python semantic validation returned a result that could not be
serialized, and the one error it crashed on was the cross-field rule a semantic model
exists to express. `--version` now also names which implementation answered.

### Fixed

- **A `model_validator` failure is reported as plain data.** `validate_semantic`
  returned `dict(error)` verbatim for each pydantic error, and pydantic puts the raised
  exception object in `ctx["error"]` when a `model_validator` fails.
  The result therefore carried a live `ValueError`, and any caller that serialized it
  died with `TypeError: Object of type ValueError is not JSON serializable`.

  The gap landed exactly where it hurt.
  A missing property or a wrong type produces a plain error that serializes fine, so
  `validate --model` and `repair --model` reported ordinary structural problems and then
  crashed on the invariants the model was written to enforce.
  Exceptions in `ctx` are now rendered as their message — what a reader needs, and what
  the CLI was already trying to print.

### Changed

- **`--version` names the implementation**: `softschema 0.8.1 (Python)` and
  `softschema 0.8.1 (TypeScript)`. The two packages share a name, a version, and a CLI,
  so the version line alone could not tell you which runtime answered — the first thing
  worth knowing when the runtimes are suspected of disagreeing.
  Anything matching the old output exactly needs its pattern widened; the name and
  version still lead the line.

### Security

- **The `fast-uri` override is raised to 3.1.6.** It closes four high-severity
  advisories against `>=3.1.3 <3.1.6` — host confusion through skipped IDN
  canonicalization, SSRF through malformed IPv6 normalization, SSRF through repeated
  hostname percent-decoding, and host confusion through percent-encoded scheme
  normalization. The package is a transitive dependency of the TypeScript
  implementation’s schema validator.

## v0.8.0—2026-08-30

### `softschema repair`

Validation normally happens after the process that wrote an artifact has exited.
By then the session that could fix the document is gone, so a large, nearly-correct
artifact is discarded over one field.
`repair` lets the producer run the same check its consumer will run, while it can still
act on the answer.

```bash
softschema validate <path>            # unchanged; read-only, never writes
softschema repair <path>              # repair, conform, write, validate
softschema repair <path> --dry-run    # report what would change; no write
softschema repair <path> --check      # exit 1 if anything would change; no write
```

The two write-suppressing flags ask different questions, and both are wanted.
`--dry-run` reports what would change and still passes when the result would be valid,
which is what an agent asks before committing to a change.
`--check` fails whenever anything would change at all, the same shape as
`generate --check`, which is what a gate runs against an artifact under review.

`validate` and `repair` also take deliberately different postures toward an artifact
that cannot be read.
`validate` is what a consumer runs, and refuses one outright with a one-line message and
exit 2: an artifact it cannot open is not a failing artifact.
`repair` is what a producer runs, and reports the same condition as a record at exit 1,
under no contract when the document declares none legibly — a truncated write is its
ordinary input, and the agent that made it needs something to act on.
Which posture applies follows from the command, never from which other flags were
passed.

One escalating pass, writing the file once: parse, quote a scalar whose text YAML reads
as structure, retype a scalar the contract declares `type: string`, then validate.
The replacement text is the scalar as written, so `1.10` and `007` survive being
retyped.

What it declines to do is the point.
A missing required property is not invented, a near-miss key is not renamed, an explicit
null is not stringified, and a parse failure quoting cannot fix — an alias, a merge key,
an explicit tag — keeps its original error code.
An artifact needing no repair comes back byte-identical.

A document that opens a frontmatter fence and never closes it — what a truncated write
leaves behind — is a frontmatter-md read error to both commands.
It is not a fenceless `pure-yaml` document whose leading `---` happens to be a YAML
document-start marker, and both name the same cause.

A document whose closing fence is the last byte of the file, with no trailing newline,
is repaired like any other.
The offset scan behind the repair region read “no newline left” as “no closing fence”,
so `--repair` silently skipped an artifact it could fix while the reader read the same
frontmatter without complaint.
Both fixes come to the same rule, now stated in the spec: a final line with no trailing
newline is a line, and the reader and the scanner must agree on where a document’s
fences are.

A leading UTF-8 byte order mark is dropped on read rather than carried into the document
as a character. This one split the two runtimes rather than two code paths:
`TextDecoder`’s default strips the mark and Python’s `bytes.decode` kept it, so
`npx softschema` read a BOM-prefixed artifact while `uvx softschema` reported that it
had no YAML frontmatter — a block plainly there, and `--contract` advised as a fix that
could not have helped.
Stripping happens in the one function both runtimes route every artifact and schema read
through, so no fence comparison has to know about it.
A U+FEFF anywhere but position zero is a real character and survives.

Both CLIs also now emit softschema’s own read diagnostics with identical wording.
The Node CLI prefixed a frontmatter read failure with `Error parsing YAML metadata:` and
the Python CLI did not, so the two disagreed about how to word the same failure for the
same file.

### Added

- `load_artifact` / `loadArtifact`: the strict consuming call.
  Returns the payload values and raises `ArtifactInvalidError` on anything short of
  valid, with the whole result attached.
  `validate_artifact` returns `values: None` on failure, so consuming code that forgets
  to check `outcome` fails later, naming neither the artifact nor the reason.
- `repair_artifact` / `repairArtifact`, `repair_yaml_text` / `repairYamlText`,
  `conform_artifact` / `conformArtifact`, and `repair_and_validate_artifact` /
  `repairAndValidateArtifact` on the public API of both packages, with their result
  types.
- `resolve_bound_schema` / `resolveBoundSchema`: the single answer to which compiled
  schema an artifact is judged against, so validation and repair cannot disagree about
  it.
- Shared `yaml_repair` and `schema_conform` vector sections, and the
  `tests/golden/scenarios/validate-repair.tryscript.md` journey, which runs against
  Python, Node, and Bun.

### Changed

- `ArtifactValidationResult` gains `repairs`, a list of what a repair pass changed.
  It is always present and empty for a plain `validate`, so every `validate` JSON result
  now carries a `"repairs": []` key.
  Records use the documented `kind`/`code`/`path` match surface, so a consumer
  identifies a repair the way it identifies an error.
- Both packages describe themselves as “Gradual contracts for YAML data, with optional
  Markdown context”. This is the summary line on the PyPI and npm listing pages.
- TypeScript semantic error records now carry `expected` on the Zod issues that have
  one. It is what identifies a type disagreement; without it an `invalid_type` issue says
  only that something was wrong, not what was wanted.

## v0.7.0—2026-08-25

This is a minor release because structural diagnostic records and supplied-resource
requirements change even though ordinary schema verdicts remain compatible.

`status: enforced` now returns real document verdicts for supported `allOf`,
`if`/`then`/`else`, and `dependentSchemas` object shapes that version 0.6.2 refused
before examining the document.
It also corrects unsafe `anyOf`, `oneOf`, and `$ref` transformations that could change
the authored schema’s result.
At each supported object location, it rejects a present property whose value is not
admitted by any successful applicable schema.
If the validator cannot apply that undeclared-property rule without changing the
schema’s other behavior, it returns an explicit unsupported result.

Support for the previously refused shapes is additive relative to version 0.6.2, but
this release is not wholly backward-compatible: corrected alternative/reference
behavior, supplied-resource handling, and structural diagnostic records can change as
described below.

### Breaking changes and migration

Structural errors now identify both a stable category and, for field-level repairs, the
affected property. Consumers that match engine keywords or assume one aggregate record
per object should migrate:

| Before | After |
| --- | --- |
| Match `validator == "additionalProperties"` | Match `code == "undeclared_property"`; composed sites report `unevaluatedProperties` |
| Match `{kind, code, path}` for a field repair | Match `{kind, code, path, property}` |
| Read one generic missing/extra record | Read one record per affected field, with a property-specific message |
| Treat every `enforcement_unsupported` as composed-schema refusal | Inspect its stable `reason`; only shapes outside the support matrix are refused |

The `code` values are `undeclared_property`, `missing_property`, `invalid_value`, and
`unmapped_keyword`. `validator`, `validator_value`, and `value` remain diagnostic
fields, not the field-repair match surface.

Callers that supply external resources must key each one by an absolute URI without a
fragment. A resource root `$id`, when present, must resolve to that key.
This makes Python and TypeScript resolve the same fully supplied offline resource graph
rather than relying on engine-specific retrieval behavior.

### Fixed

- **Supported composed object schemas now validate under `enforced`**
  ([#41](https://github.com/jlevy/softschema/issues/41)). `allOf`, `anyOf`, `oneOf`,
  `if`/`then`/`else`, `dependentSchemas`, and supported `$ref` branches remain unchanged
  internally; their parent receives annotation-aware `unevaluatedProperties: false`.
  This preserves alternative branch selection and successful-branch annotations.
  Direct lexical objects continue to use `additionalProperties: false`. Reusable
  definitions and resources remain open while each supported structured reference site
  receives its own undeclared-property rule.
  The offline graph supports local pointers, escaped tokens, anchors, nested
  definitions, embedded `$id` resources, supplied resources, and literal or
  pattern-based declarations.
  Structured `items` and disjoint `prefixItems`/`items` receive the rule independently,
  while `contains` remains an unchanged matcher.
  Pure references to targets that already state `additionalProperties` or
  `unevaluatedProperties` receive no redundant closure keyword.
  This keeps the common generated `anyOf: [$ref, null]` shape valid when its object
  graph is already explicit.
  Sibling child evaluators and context-sensitive composition references are refused when
  inserting undeclared-property rejection could change intersection, branch-selection,
  or conditional-success semantics.
- **Values APIs can request the checked structural policy.** Both Python and TypeScript
  values APIs accept `status` and offline `resources`. Existing model-only calls retain
  their semantic-only behavior, including under `status: enforced`; the status changes
  structural behavior only when a schema is supplied.
- **Field-level structural diagnostics identify the repair target.** Missing and
  undeclared-property errors name the field and preserve one record per affected field.
  `unevaluatedProperties` uses the same category and property-specific message as
  `additionalProperties`. Array indexes in `path` are numeric in both runtimes, and
  Python derives missing required fields from validator data rather than English error
  text.
- **In-memory schema graph identity is deterministic.** Reusing one mapping object at
  several schema locations now returns `schema_invalid/shared_subschema` with deep-copy
  guidance instead of allowing traversal order to select which object locations reject
  undeclared properties.
  TypeScript repeats this graph check before returning a validator-cache hit, where
  serialized content alone cannot distinguish shared identities.

### Added

- **Stable `code` and `property` error fields.** `code` groups engine keywords by repair
  category; `property` identifies the field for missing and undeclared-property records.
- **An explicit `status: enforced` support matrix.** Dynamic references, unsafe nested
  instance composition, conditionals whose matcher annotations escape the unconditional
  declaration scope, directly applied structured embedded resources, and references to
  directly applied non-reusable targets return `enforcement_unsupported` with stable
  `reason`, `schema_path`, and `message` fields.
  Malformed graphs remain `schema_invalid`.
- **Semantic parity vectors.** Shared raw-versus-enforced vectors cover alternatives,
  references, resources, patterns, conditionals, unsupported boundaries, and field-error
  multiplicity in Python and TypeScript.
- **Documented native-engine deviations.** The `engine_deviations` vectors pin the few
  accepted `jsonschema`/Ajv record-set differences exactly.
  Validation verdicts for the supported matrix remain equal.

### Compatibility

Compiled schemas and `schema_sha256` are unchanged because the checked overlay remains
validation-time only.
Explicit `additionalProperties` or `unevaluatedProperties` at an instance site still
wins, and mappings with no reachable declaration remain open.
Model-only and metadata-only validation keep their version 0.6.2 verdicts and skip
reasons; this release does not require existing hosts to add structural schemas.

Documents previously refused solely because they used supported composition now report
their real valid or invalid outcome.
A schema outside the supported matrix fails before document validation with an
actionable reason rather than receiving a partial overlay.
See the spec’s [support matrix](docs/softschema-spec.md#support-matrix) for the exact
boundary and author workarounds.

## v0.6.2—2026-08-22

Fixes a validation gap that could pass a build while checking nothing: the CLI bound
every artifact to the `frontmatter-md` profile, so a conforming `pure-yaml` artifact —
including the spec’s own example — could not be validated at all.

### Fixed

- **`validate` and `inspect` resolve the artifact profile instead of assuming
  `frontmatter-md`** ([#38](https://github.com/jlevy/softschema/issues/38)). Both CLIs
  read every artifact with the frontmatter reader and built a `Contract` with no
  `profile`, so the pure-yaml branch of `validate_artifact` was unreachable from the
  command line and any pure-YAML file failed with `no_frontmatter`. The library was
  correct throughout; only the binding was wrong.

  The gap was silent rather than loud, which is what made it worth a patch: a project
  could adopt pure-YAML datasets, mark them `status: enforced`, wire
  `softschema validate` into CI, and get a passing build that validated nothing — the
  exact failure `status` exists to prevent.
  An `enforced` pure-yaml artifact that violates its bound schema now fails with exit 1.

  Profile resolution is `--profile` flag > a `*.yaml`/`*.yml` file name > a fenceless
  document whose root mapping carries a `softschema:` block > `frontmatter-md`. The name
  is checked before the fence because a YAML document may open with the `---`
  document-start marker that the frontmatter reader would otherwise scan as a fence.
  Requiring the metadata block for the content case keeps prose that happens to parse as
  YAML on `frontmatter-md`, so a Markdown document without frontmatter reports
  `no_frontmatter` exactly as before.

- **Envelope inference no longer applies to pure-yaml artifacts.** The spec exempts the
  profile from single-key inference and multi-key ambiguity rejection, because a
  pure-yaml artifact’s whole root minus the metadata block is the payload.
  Reaching that branch through the CLI would otherwise have rejected a two-key pure-yaml
  document as ambiguous.

### Features

- **`--profile {frontmatter-md,pure-yaml}` on `validate` and `inspect`** in both
  implementations: the explicit escape hatch for an artifact whose name and content do
  not settle its shape.

- **`inspect` reports the resolved `profile`**, and reads a pure-yaml artifact’s root
  metadata block rather than reporting `metadata: null` for it.
  `has_frontmatter` stays literal — a pure-yaml artifact has none — and `profile` is
  what explains the populated metadata beside it.
  This adds one key to the `inspect` JSON output.

- **`clearValidatorCache` is exported from the TypeScript package**, matching Python’s
  `clear_validator_cache`.

### Performance

- **TypeScript compiled schemas are memoized**, closing the last gap with the Python
  cache shipped in v0.5.0. `validateStructural` constructed a fresh Ajv instance and
  recompiled the schema on every call, so a suite validating many artifacts against one
  schema paid full compilation each time; on a repeated validation of the movie example
  the per-call cost drops from roughly 17ms to 0.03ms.

  Both runtimes now key the cache on the schema’s own content plus the `enforced`
  overlay, so a rewritten schema can never be served a stale entry and two paths holding
  identical schemas share one.
  Validation with `resources` supplied builds fresh in both, rather than risk a wrong
  key.

## v0.6.1—2026-08-14

Documentation only. Both packages are unchanged in behavior, so no code, CLI surface, or
schema output differs from v0.6.0; the release exists to ship the new guidance with the
docs bundled in the wheel and the npm tarball.

Adds a worked example of using soft schemas to record a **research loop** — any process
that repeatedly proposes an idea, measures it, and decides, such as performance work,
prompt tuning against an eval, or a library comparison.
Each iteration is one artifact whose frontmatter carries the values the loop’s own
tooling consumes (hypothesis ID, fingerprints, measured medians with confidence
intervals, a verdict from a fixed set) while the body keeps the reasoning only the
author can write.

### Documentation

- **New guide playbook, “Record a Research Loop”** (`docs/softschema-guide.md`): the
  artifact shape as a complete annotated example, plus the four habits that keep the
  record and its roll-up report in sync — compile the contract from a model and
  `--check` it in CI, record measurements mechanically and ask the operator only for
  judgment, regenerate the ledger from validated artifacts, and let the record be the
  loop’s memory across sessions.
- **New README section, “Example: Recording a Research Loop”**: a short subset of the
  playbook that links to it, keeping the README a summary rather than a second copy.
  It covers why negative results survive as queryable artifacts, why a regenerated
  report cannot drift from the record, and why an agent resuming the loop months later
  can read back what was tried without re-running anything.

## v0.6.0—2026-08-04

Validation accepts an already-parsed document root on both profiles, not just
`frontmatter-md`. A consumer whose artifacts are pure YAML previously had no way to
reuse its own parse: the parameter existed but that profile ignored it and re-read the
file. On a downstream workload publishing 1,274 files, validation drops from 171.1s to
69.2s because each artifact is now parsed once rather than twice.

The parameter is renamed to reflect what it carries on either profile, and both
implementations now publish the readers that produce it.

### Upgrade

1. Rename the argument at every callsite.
   Python `validate_artifact(..., frontmatter=root)` becomes `document=root`; TypeScript
   `validateArtifact(..., { preParsed })` becomes `{ document }`, whose type
   `RawFrontmatter` is renamed `ParsedDocument`. No alias is kept, so a missed callsite
   is a `TypeError` in Python and a compile error in TypeScript rather than a silently
   ignored option.

2. Produce the root with softschema’s own readers, now exported: `read_frontmatter_doc`
   and `read_yaml_doc` in Python, `readFrontmatterDoc` and `readYamlDoc` in TypeScript.
   A supplied root is trusted as already decoded and bypasses the portable YAML rules
   (merge keys, explicit tags, aliases, the 64-collection depth bound) that reading from
   disk enforces. A root decoded by a host YAML library directly may validate in one
   implementation and be rejected by the other reading the same file, which is the
   divergence those rules exist to prevent.

3. Drop any `profile: frontmatter-md` declared on a pure-yaml artifact purely to reach
   the single-read path.
   That workaround traded a correctness hazard for a performance one and is no longer
   needed.

### Breaking

- **The pre-parse parameter is renamed** in both implementations, with no alias: Python
  `validate_artifact(..., frontmatter=)` is now `document=`, and TypeScript
  `validateArtifact(..., { preParsed })` is now `{ document }`. The parameter carries
  the parsed document root for either profile, so a caller holding one no longer has to
  know which profile it is on to avoid a second parse.
- **TypeScript type and reader renames**: the exported `RawFrontmatter` is now
  `ParsedDocument`, and `readFrontmatter` is now `readFrontmatterDoc`, matching the
  Python names.
- Minor rather than patch: these rename public API in both packages, which is what
  `publishing.md` reserves a minor bump for.
  A missed callsite fails loudly (a `TypeError` in Python, a compile error in
  TypeScript) rather than silently ignoring the option, so the break is visible at
  upgrade time rather than at runtime.

### Features

- **Pure-yaml validation honors a pre-parsed root** in both implementations.
  The parameter previously existed but reached only the frontmatter profile; a pure-yaml
  contract ignored it and always re-read the file, so the optimization was unreachable
  for exactly the consumers whose artifacts are pure YAML. TypeScript had the same
  defect and is fixed in the same release.
- **The decoders are exported**: `read_frontmatter_doc` and `read_yaml_doc` in Python,
  `readFrontmatterDoc` and `readYamlDoc` in TypeScript.
  Neither package previously published a way to decode an artifact, so a caller
  producing a `document` root had no supported parser and would reach for a host YAML
  library, silently losing the portable rules.
  `read_yaml_doc` replaces the private `_read_yaml`.
- **The trust boundary is documented** in the spec, both design docs, and the
  `validate_artifact` docstrings: a supplied root is trusted as already decoded and is
  not re-checked against the portable YAML rules.

## v0.5.0—2026-08-04

v0.5.0 removes the parser’s input, scalar, and node size ceilings, so softschema no
longer refuses a large artifact after its caller has already written it.
The nesting depth rule stays, reclassified as a portability rule rather than a resource
guard. Compiled schemas are also now cached per schema file, which cuts a large
validation run’s wall clock substantially.

### Upgrade

1. Upgrade every softschema implementation the project uses to `0.5.0`, then refresh its
   lockfiles. Projects that use both implementations must update them together.
   TypeScript lockfiles should resolve `fast-uri>=3.1.5` through Ajv; versions before
   3.1.5 have high-severity URI host-confusion advisories.

2. Remove any handling of the `artifact_too_large` error kind.
   It no longer exists, and no validation result can return it.
   Code that branched on it is now dead; code that treated it as “the artifact was
   rejected” needs no replacement, because such artifacts now validate normally.

3. Re-check any workflow that depended on softschema rejecting large artifacts.
   Inputs over 1 MiB, scalars over 256 KiB, and documents over 100,000 nodes were
   previously rejected with `outcome: input_error` and are now parsed and validated like
   any other artifact. If a pipeline used softschema as its size guard, that guard must
   move to the code that writes or accepts the artifact, where it can reject before the
   work is done rather than after.

4. Leave nesting depth alone.
   The 64-collection depth rule is unchanged and still reports `yaml_limit`. It is now
   documented as a portability rule, in the same category as `MAX_SAFE_INTEGER`: without
   it the two runtimes disagree by an order of magnitude about how deep a document may
   be, because CPython and V8 have very different stack budgets.

5. No artifact rewrite is required, and no compiled schema needs regenerating.
   Every artifact valid under v0.4.0 remains valid under v0.5.0.

### Breaking

- **`artifact_too_large` is removed** from the error taxonomy in both implementations,
  along with the internal `input_too_large` mapping and the shared `too_large`
  conformance vector. An artifact that v0.4.0 rejected with
  `outcome: input_error, kind: artifact_too_large` now returns a normal `valid` or
  `invalid` result. This widens the accepted artifact set; it never narrows it, so no
  previously valid artifact is affected.

### Features

- **Parser resource ceilings removed**: `MAX_INPUT_BYTES` (1 MiB), `MAX_SCALAR_BYTES`
  (256 KiB), and `MAX_NODES` (100,000) are gone from both implementations.
  They only answered whether a hostile document could exhaust the parser, and softschema
  reads artifacts its own callers just wrote.
  A cap that can only fire after the artifact is written destroys completed work rather
  than rejecting bad input, and none of the three was overridable by a parameter,
  profile, or environment setting.
- **Compiled validators are cached** (Python): `validate_structural` no longer reparses
  and recompiles the JSON Schema validator on every call.
  The cache is keyed on the schema text itself, so a regenerated schema can never be
  served from a stale entry and two paths holding identical bytes share one entry.
  Validation that passes `resources` is left uncached, and compile failures are not
  cached. Measured on a downstream suite: 361s to 262s, a 28% reduction.
- **`clear_validator_cache()`** (Python) is exported for long-lived processes that
  regenerate compiled schemas in place, such as a watch mode or a language server.
  Ordinary callers never need it, because a rewritten schema misses the cache on its
  own. The TypeScript implementation has no corresponding export because it does not yet
  cache compilation.

### Fixes and hardening

- **Python maps `RecursionError` to `yaml_limit`**, mirroring the TypeScript
  `RangeError` path. The depth preflight makes this unreachable for ordinary callers, but
  a caller already deep in its own stack can exhaust the budget at a legal depth, and
  that must stay a structured result rather than an exception escaping
  `validate_artifact`.
- **Depth rule documented as a portability rule**: `MAX_DEPTH` (64) is unchanged in
  value and behavior, but the spec and both implementations now explain that it bounds
  what survives a round trip through a host parser, alongside `MAX_SAFE_INTEGER`, which
  bounds what survives a round trip through a JS number.

### Dependencies

- **Patched TypeScript URI resolver**: The checked-in TypeScript dependency graph now
  constrains Ajv’s `fast-uri` dependency to reviewed version 3.1.5, removing a further
  high-severity host-confusion advisory that also covers the previously pinned 3.1.4.
  The exact pin carries the same one-package release-age exception as the 3.1.4 pin it
  replaces, because the patched release is the only way to clear the advisory and no 3.x
  version outside the affected range exists.
  Refresh and verify application lockfiles against the same safe floor; no softschema
  API or artifact change is involved.

## v0.4.0—2026-07-31

v0.4.0 makes YAML date- and timestamp-shaped scalars portable strings in both
implementations. It also aligns canonical schemas compiled from corresponding Pydantic
and Zod temporal fields.

### Upgrade

1. Upgrade every softschema implementation the project uses to `0.4.0`, then refresh its
   lockfiles. Projects that use both implementations must update them together.
   Python lockfiles should resolve `frontmatter-format>=0.4.0`; that first-party release
   is an intentional exception to the normal dependency cool-off.
   TypeScript lockfiles should resolve `fast-uri>=3.1.4` through Ajv; versions before
   3.1.4 have high-severity URI host-confusion advisories.

2. Validate the project’s full artifact corpus.
   No artifact rewrite is required: quoted and unquoted date-shaped YAML values remain
   strings, and bare dates that v0.3.0 rejected are now accepted.

3. Regenerate committed compiled schemas from Zod models that use ISO date, datetime,
   time, or duration helpers.
   Their digest may change once because compiler-intrinsic patterns are removed.
   Review and commit that generated diff.

4. If a workflow relied on a Zod-generated temporal pattern for structural rejection,
   add an explicit portable JSON Schema `pattern`. The default JSON Schema `format`
   vocabulary remains annotation-only in softschema.

5. Test the bound Pydantic and Zod semantic validators with the application’s accepted
   and rejected temporal values.
   Canonical schema parity does not promise identical semantic accept sets across the
   two model libraries.

6. Treat validation-result values as strings.
   Host code that needs `date`, `datetime`, or JavaScript `Date` objects must construct
   them explicitly after validation.

7. If the bundled project skill is installed, refresh its managed mirrors:

   ```bash
   softschema skill --install --scope project --agent portable --agent claude
   ```

The
[Dates and Timestamps Are Strings](docs/softschema-guide.md#dates-and-timestamps-are-strings)
guide section gives the complete authoring and migration rationale.

### Features

- **Portable YAML timestamp strings**: Bare dates and timestamps now decode to their
  string content in both implementations instead of being rejected.
  Existing quoted values remain unchanged, and no artifact rewrite is required when
  upgrading. Validation results retain strings; date validity remains the responsibility
  of a semantic model or explicit structural assertion.
- **Canonical temporal-schema parity**: Corresponding Pydantic temporal fields and Zod
  ISO date, datetime, time, and duration strings now compile to the same format-only
  schema and digest. JSON Schema `format` remains annotation-only; explicitly authored
  patterns remain structural assertions.
  Model-specific coercions and Zod ISO options remain semantic constraints outside the
  structural digest.

### Dependencies

- **`frontmatter-format` v0.4.0**: The Python package adopts the deterministic,
  alias-free writer used for compiled-schema YAML. Its general-purpose readers retain
  YAML-native timestamp behavior; softschema does not use them for artifacts and
  continues to own the stricter portable-string parsing boundary.
  The dependency upgrade therefore requires no artifact rewrite and does not cause the
  timestamp behavior change described above.
- **Patched TypeScript URI resolver**: The checked-in TypeScript dependency graph
  constrains Ajv’s `fast-uri` dependency to reviewed version 3.1.4, removing two
  high-severity host-confusion advisories.
  The exact pin is a maintainer-approved exception to the normal dependency cool-off.
  Refresh and verify application lockfiles against the same safe floor; no softschema
  API or artifact change is involved.

### Guidelines and Content

- **Agent timestamp guidance**: The bundled skill now tells agents that date-shaped YAML
  values are portable strings and that calendar validation belongs in the bound contract
  or model.

### Documentation

- **Date migration guidance**: The guide, spec, and language design references now
  distinguish portable string decoding from Pydantic, Zod, and JSON Schema date
  validation, including the annotation-only format policy.

**Full commit history**:
[v0.3.0 … v0.4.0](https://github.com/jlevy/softschema/compare/v0.3.0...v0.4.0)

## v0.3.0—2026-07-12

### Features

- **Paired portable-value boundary**: Python and TypeScript now share bounded UTF-8 and
  YAML input rules, safe-number limits, canonical schema digests, and structurally
  comparable validation results.
- **Contract and schema identity**: Compilers require a logical contract ID, keep an
  optional JSON Schema resource ID separate, and produce matching canonical compiled
  schemas and `schema_sha256` values.
- **Explicit skill installation**: `softschema skill --install` now requires a scope and
  agent target, supports dry-run previews, and protects unmanaged files.

### Fixes

- **Portable validation parity**: Aligned frontmatter delimiters, YAML structure limits,
  schema and pattern failures, strict-extra handling, error records, and compiler drift
  checks across both runtimes.
- **Bounded document resources**: Document-declared schemas and installed package
  resources now resolve within their intended trust boundaries.

### Guidelines and Content

- **Installed agent resources**: The source skill and generated portable Agent Skills
  and Claude mirrors now use one managed, drift-checked installation flow.

### Documentation

- **Hardening documentation**: Updated the guide, spec, language design references, and
  development workflow to describe the paired runtime and release boundary accurately.

**Full commit history**:
[v0.2.2 … v0.3.0](https://github.com/jlevy/softschema/compare/v0.2.2...v0.3.0)

## v0.2.2—2026-06-15

### Features

- **`softschema prime` command**: Prints the full agent context (the skill operating
  rules plus the bundled docs index), so an agent can restore context without the source
  checkout. Byte-identical across the Python and TypeScript CLIs.

### Fixes

- **CLI error boundary no longer masks internal bugs**: The user-error boundary now
  excludes bug-indicator exception types (Python `TypeError`/`KeyError`; JavaScript
  `TypeError`/`RangeError`/`ReferenceError`), so a programmer bug surfaces as a
  traceback instead of a clean exit 2. In the TypeScript CLI every per-command handler
  routes through one shared boundary (`reportUserError`), so a bug thrown deep inside a
  command — not just one that reaches the top-level guard — crashes rather than being
  reported as exit 2. Adds an explicit `UsageError` class and documents the 0/1/2
  exit-code contract.
- **Supply-chain cool-off config**: The `[tool.uv]` cutoff used a date-only string that
  uv could not parse; it now uses RFC3339 timestamps with a pinned global cutoff, so the
  exception applies to local resolution and the lockfile stays stable.
- **Canonical number rendering (`ss-wbnm`)**: A whole-valued number now renders in
  canonical form — no trailing fraction and no exponent below 1e21 (`2.0` becomes `2`,
  `1.0e16` becomes `10000000000000000`) — in error records, synthesized messages, and
  the echoed `values` block.
  JavaScript emits this form natively; the Python side converts its whole-valued floats
  to match, so validation output is byte-identical for every number an implementation
  represents exactly (the IEEE-754 safe-integer range).
  A non-round integer-valued magnitude at or beyond 2^53 stays runtime-specific and is
  out of scope.

### Refactoring

- **Shared mapping guard**: Consolidated four near-duplicate object guards into one
  `isMapping` helper (TypeScript).
- **Preserve original `docs` error**: The `docs` command reports the underlying failure
  rather than a generic message, matching the Python CLI.
- **Removed redundant error handling**: Dropped a redundant inner `try/except` in the
  Python `compile` command.

### Documentation

- **PyPI-focused Python README**: `packages/python/README.md` is now a short PyPI entry
  point instead of a second full README.
- **Added `CHANGELOG.md`** following the release-notes guidelines.

**Full commit history**:
[v0.2.1 … v0.2.2](https://github.com/jlevy/softschema/compare/v0.2.1...v0.2.2)

## v0.2.1—2026-06-15

### Fixes

- **ESM library entrypoint and CLI main check**: Fixed the ESM entrypoint and CLI main
  guard so the library loads correctly in ESM consumers (#16)

### Documentation

- **Documentation-guidelines pass**: Standardized repo docs to follow
  common-doc-guidelines
- **Review cleanups**: Minor cleanups from code review

**Full commit history**:
[v0.2.0 … v0.2.1](https://github.com/jlevy/softschema/compare/v0.2.0...v0.2.1)

## v0.2.0—2026-06-11

### Features

- **Contract-ID grammar enforcement**: Contract IDs now follow an enforced shape
  (`[namespace:]Name[/version]`)
- **`softschema.schema` binding**: Artifacts can declare their compiled schema path in
  the `softschema:` block for self-describing validation
- **Self-describing artifacts**: Artifacts with a `softschema:` block validate with no
  CLI flags

### Refactoring

- **Error-kind renames**: Validation error kinds renamed for clarity and consistency

**Full commit history**:
[v0.1.4 … v0.2.0](https://github.com/jlevy/softschema/compare/v0.1.4...v0.2.0)

## v0.1.4

Maintenance and packaging fixes.

## v0.1.3

Maintenance and packaging fixes.

## v0.1.2

Maintenance and packaging fixes.

## v0.1.1

Maintenance and packaging fixes.

## v0.1.0

Initial release.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
