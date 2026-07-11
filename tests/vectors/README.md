# Shared Test Vectors

`hardening.yaml` is the sole cross-runtime structured behavior corpus.
Python and TypeScript tests read it directly.
Add a case only when both runtimes promise the same meaning; keep adapter-specific
filesystem, model, and package behavior in that adapter’s unit tests.

## Primary Owners

| Behavior | Primary owner |
| --- | --- |
| Artifact input classes and portable YAML values | `hardening.yaml` through each validation adapter |
| Local references, schema failures, format, and patterns | `hardening.yaml` through each structural validator |
| Canonicalization, enforcement, identity, annotations, `SchemaView`, and digests | `hardening.yaml` through the matching library adapter |
| Pydantic compilation and Python path behavior | Python unit tests |
| Zod compilation and TypeScript model loading | TypeScript unit tests |
| CLI output, streams, and exit classes | End-to-end tryscript goldens |
| Wheel and npm contents | One installed-package smoke per ecosystem |
| Cross-runtime compiled schema identity | One parity test |
| Bundled docs and skill mirrors | Installed-package smoke plus one mirror-drift test |

Unit tests may add one adapter integration assertion around a shared vector.
They do not restate the full input and expected output.
Goldens cover complete command journeys, not isolated library rules.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
