# Security Policy

softschema validates files that may come from untrusted repositories, but not every
input associated with a validation run is inert.
This policy separates safe data paths from operations that execute trusted code or write
agent configuration.

## Report a Vulnerability Privately

Use
[GitHub private vulnerability reporting](https://github.com/jlevy/softschema/security/advisories/new).
Include the affected package and version, the smallest reproducible input, the observed
impact, and any suggested mitigation.
Do not open a public issue for an undisclosed vulnerability or include secrets, private
documents, or credentials in a report.

Maintainers will acknowledge a complete report, investigate affected release lines, and
coordinate disclosure.
Acknowledgment and remediation times depend on severity and reproducibility; this
project does not promise a fixed service-level agreement.

## Supported Releases

| Release | Security status |
| --- | --- |
| Current source branch | Pre-release development; not a published security update |
| 0.2.2 | Latest published release; known boundary limitations below |
| Earlier releases | Unsupported |

Version 0.3.0 is the planned consolidated security and compatibility release.
Until it is published and its artifacts are verified, do not describe source-branch
fixes as an available package update.

## Trust Boundaries

- **Artifact YAML and compiled JSON Schema are untrusted data.** Current development
  validation applies bounded portable-YAML checks and performs no implicit network or
  filesystem reference retrieval.
  Explicitly supplied library resources are already loaded data, not permission to
  fetch.
- **Markdown body prose is inert to softschema.** The validator does not parse body
  tables, execute code blocks, or treat prose as structured values.
  A separate Markdown, MDX, notebook, or renderer tool may have a different trust model.
- **Pydantic and Zod models are trusted code.** `--model`, Python imports, and Node/Bun
  module imports execute local code with the caller’s permissions.
  Do not load a model from an untrusted checkout.
  Prefer a reviewed compiled schema for untrusted input.
- **Schema paths and artifact paths are local inputs.** Resolve them under the host’s
  own containment policy.
  Validation does not make an arbitrary checkout trustworthy.
- **Agent skills are executable influence.** Review a skill before installing it.
  `skill --install` has explicit scope, ownership preflight, dry-run, containment, and
  non-clobbering rules in current development code; it is not a privilege boundary.
- **Extensions are data.** Format-1 extension values never authorize imports, plugins,
  retrieval, or validation behavior.

## Published 0.2.2 Boundary Limitations

Treat 0.2.2 as unsuitable for hostile validation or unattended skill installation unless
the host supplies compensating controls:

- Python structural validation may retrieve a remote `$ref`.
- YAML parsing does not enforce the complete portable resource budget or representation
  restrictions developed for 0.3.
- Malformed schemas may escape the stable result boundary.
- bundled docs or skills may be shadowed by colliding consumer-repository files in some
  installed execution paths.
- skill installation lacks the complete explicit-scope, ownership, rollback, and repair
  policy developed for 0.3.
- cross-runtime YAML, regex, format, and deterministic-JSON edge behavior is narrower
  than the 0.3 conformance contract.

For 0.2.2, keep schemas local and reviewed, reject non-fragment references before
validation, enforce input size limits outside softschema, run from a trusted directory,
and install skills only into a reviewed disposable target.
The preferred remediation is to upgrade after 0.3.0 is published and verified, then
follow the [0.3 migration guide](docs/migration-0.3.md).

## Release Security

Release artifacts are built once, checked against an external manifest, and published
through protected environments and trusted publishers.
Registry authentication and post-publish verification are release gates; repository
workflow files alone do not prove that live PyPI or npm publisher configuration is
correct. Candidate package versions are separate from source bootstrap pins.
Root quickstarts and agent skills continue to advertise the last dual-registry-verified
stable pair until an exact post-publish follow-up advances them; registry package pages
describe the artifact version they contain.

See
[Supply-Chain Security](https://github.com/jlevy/softschema/blob/main/SUPPLY-CHAIN-SECURITY.md)
for dependency and build controls and
[Publishing](https://github.com/jlevy/softschema/blob/main/docs/publishing.md) for
maintainer operations.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
