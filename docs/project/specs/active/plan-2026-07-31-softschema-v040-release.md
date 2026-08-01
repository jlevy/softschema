---
title: softschema v0.4.0 Release
description: Implementation-ready plan for the paired Python and TypeScript release
author: Codex, with maintainer direction from Joshua Levy
---
# Release: softschema v0.4.0

**Date:** 2026-07-31 (last updated 2026-07-31)

**Author:** Codex, with maintainer direction from Joshua Levy

**Status:** In progress

**Tracking:** release epic `ss-fyvp`; audit `ss-jrrg`; release notes `ss-quvj`;
validation `ss-1ey5`; `frontmatter-format` adoption `ss-2p2l`; publication `ss-m443`;
formatter isolation `ss-5sh9`; related-format consistency `ss-lsw0`

## Overview

Release the portable YAML timestamp work merged in PR
[#23](https://github.com/jlevy/softschema/pull/23) as softschema v0.4.0 for PyPI and
npm.
The release also adopts the first-party `frontmatter-format` v0.4.0 dependency after
that version is published and its source and package delta are reviewed.

This is a paired minor release: both softschema implementations ship as v0.4.0 from the
same Git tag. The release PR is the immutable review and CI gate; the tag points to its
merge commit; the GitHub release triggers the existing build-once OIDC workflow.

## Release Scope

The public change from v0.3.0 is intentionally narrow:

- YAML date- and timestamp-shaped scalars decode as strings in both implementations,
  including bare dates that v0.3.0 rejected.
- Corresponding Pydantic temporal fields and Zod ISO string helpers compile to the same
  format-only canonical schema and digest.
- The bundled skill, guide, spec, and language design docs explain the portable string
  boundary and where structural and semantic validation belong.
- The Python package requires `frontmatter-format>=0.4.0`, subject to the release gate
  below. The TypeScript package has no corresponding dependency.

Release bookkeeping, completed-plan archival, isolated formatter tooling, and
publishing-runbook corrections are included because they make the release auditable.
They do not add product behavior.

## Resolved Design and Compatibility Decisions

Every decision needed to publish is settled:

- **Version:** v0.4.0 is the correct minor release.
  Timestamp decoding changes the accepted artifact set and temporal schema compilation
  changes generated output.
- **Paired packages:** PyPI `softschema` and npm `softschema` release together at
  exactly `0.4.0`. A partial version bump is not supported.
- **Artifact format:** no format-version field, compatibility mode, or rewrite command
  is added. Contract IDs remain the artifact payload identity.
- **Migration:** existing quoted and unquoted date-shaped values stay strings.
  Users validate their corpus; they do not rewrite artifacts.
- **Generated schemas:** Zod users regenerate committed schemas.
  A one-time digest change is expected where compiler-intrinsic ISO patterns disappear.
- **Structural validation:** JSON Schema `format` remains annotation-only.
  A consumer that needs portable structural rejection authors an explicit `pattern` or
  another ordinary assertion.
- **Semantic validation:** Pydantic and Zod models own calendar-aware meaning.
  Their temporal accept sets need not be identical, so projects requiring identical
  meaning align and test both models.
- **Result values:** parsers and validation results return strings.
  Host-native temporal objects are an explicit post-validation application concern.
- **Dependency policy:** `frontmatter-format` v0.4.0 is first-party and is exempt from
  the normal release-age cool-off.
  The exception is recorded with the exact release timestamp in local and CI uv
  configuration.
- **Dependency compatibility:** softschema adopts v0.4.0 as its minimum and does not
  carry a v0.3 compatibility range.
  This minor release is the clean upgrade boundary.
- **Related-format boundary:** `frontmatter-format` remains a general YAML/frontmatter
  library whose readers accept timestamp types.
  softschema owns the stricter artifact parser and uses that dependency only for
  compiled-schema writing.
  The upstream alias-free writer and softschema’s timestamp-string parser are compatible
  but independent v0.4 changes.
- **Agent resources:** managed project skill mirrors are refreshed after upgrading.

No other public API, CLI, or artifact-format break is planned.

## Documentation Ownership

The documentation update follows the repository’s common-doc rules and keeps each fact
in one authoritative place:

| Document | Responsibility for v0.4.0 |
| --- | --- |
| `CHANGELOG.md` | User-facing release summary and executable upgrade sequence |
| `docs/softschema-guide.md` | Adoption rationale, examples, and timestamp migration guidance |
| `docs/softschema-spec.md` | Exact portable scalar and annotation-only `format` rules |
| Language design docs | Runtime-specific parser, compiler, and semantic-model details |
| `skills/softschema/SKILL.md` | Concise agent operating guidance, mirrored by the CLI |
| `docs/publishing.md` | Maintainer release, recovery, and registry process |
| This plan and its review | Internal decisions, gates, and validation evidence |

The README remains a short subset of the guide.
The release does not need another README explanation or a duplicate standalone migration
document.

## `frontmatter-format` v0.4.0 Gate

Complete every item after the upstream release exists and before the softschema release
PR is finalized:

1. Confirm the `v0.4.0` tag, GitHub release, and PyPI artifact identify the same source
   commit and version.
2. Review `v0.3.0...v0.4.0`, its release notes, dependency graph, supported Python
   versions, and the `new_yaml` API used by softschema.
3. Run the upstream tests or relevant source checks from the tagged checkout when the
   repository provides them.
4. Set `frontmatter-format>=0.4.0`, update `uv.lock`, and record the release timestamp
   in `[tool.uv].exclude-newer-package`.
5. Re-pass the same exception in every CI `uv sync` command because the global
   `UV_EXCLUDE_NEWER` environment override replaces the project exception map.
6. Run focused compiler/writer tests before the complete release matrix.

The gate fails if v0.4.0 changes or removes the writer contract softschema consumes,
adds an unacceptable dependency, drops a supported Python version, or cannot be resolved
reproducibly.
Because every release decision must be resolved, a gate failure is fixed in
softschema or upstream before publication; it is not deferred past v0.4.0.

## Validation Plan

Run the complete [end-to-end testing runbook](../../../e2e-testing.runbook.md) against
the final dependency lock and release tree:

1. Lint, typecheck, Python tests, TypeScript tests and coverage, both builds, and
   `publint`.
2. Golden corpora under Python, Node, and Bun, plus the direct cross-implementation
   parity comparison.
3. Markdown formatting and generated-resource drift checks.
4. Clean wheel and npm-tarball installs outside the checkout.
5. The README quickstart as written under both implementations.
6. Project-scope skill installation into a scratch Git repository.
7. Release-candidate checksum, version, contents, and installed-artifact checks in CI.
8. After publication, exact-version registry checks and the published Python quickstart.

The release review records command results, counts, artifact names and hashes, CI and
publish URLs, registry versions, and smoke-test output.

## Release Procedure

1. Complete dependency-independent release notes, planning, versioning, documentation,
   and preliminary validation.
2. Wait for and pass the `frontmatter-format` gate; update and freeze the final lock.
3. Run the full local validation and package smokes against that final tree.
4. Review the aggregate `v0.3.0...HEAD` diff and record the senior release decision.
5. Commit and push the release branch, open the release PR, and wait for every required
   check. Merge only the tested tree.
6. Update local `main`, confirm a clean worktree, and create annotated tag `v0.4.0` on
   the release PR merge commit.
7. Create GitHub release `softschema 0.4.0` from the changelog content.
   Its release event triggers trusted publication to PyPI and npm.
8. Watch the publication workflow through both registry jobs, then run the post-publish
   checks.
9. Record final evidence and close and sync all release beads.

## Failure Recovery

- **Before tagging:** correct the release branch and rerun the complete affected gates.
- **Tag created, release not created:** do not move the tag.
  If the tagged tree is wrong, abandon v0.4.0 and fix forward with v0.4.1.
- **One registry job fails:** preserve the tag, release, and successful publication;
  rerun only failed workflow jobs so they reuse the checksummed release candidate.
- **Registry propagation delay:** confirm the registry API and simple index separately,
  then retry the exact-version smoke with refreshed indexes.
- **Published artifact defect:** registry versions and tags are immutable.
  Document the issue and publish a corrected patch release; never replace v0.4.0 bytes.

## Completion Criteria

- The dependency gate and every local and CI validation gate pass on the final tree.
- The release PR is merged and `v0.4.0` points to its merge commit.
- The GitHub release and both registry versions are public and mutually consistent.
- Clean external installs report `softschema 0.4.0`, and the published quickstart
  validates successfully.
- The release review contains the complete evidence record.
- All release beads are closed and synchronized.

## Open Questions

None. The upstream release is a sequencing gate, not an unresolved design decision.

## References

- [Portable YAML Timestamp Strings](../done/plan-2026-07-31-portable-yaml-timestamps.md)
- [softschema Guide](../../../softschema-guide.md)
- [softschema Spec](../../../softschema-spec.md)
- [Publishing](../../../publishing.md)
- [End-to-End Testing Runbook](../../../e2e-testing.runbook.md)
- [Changelog](../../../../CHANGELOG.md)
- [GitHub issue #22](https://github.com/jlevy/softschema/issues/22)
- [Merged implementation PR #23](https://github.com/jlevy/softschema/pull/23)
- tbd `common-doc-guidelines`
- tbd `release-notes-guidelines`
- tbd `backward-compatibility-rules`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
