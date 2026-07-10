---
name: e2e-testing
description: >-
  The end-to-end release validation path for softschema: repository gates,
  conformance and parity, installed-package smoke tests, the README quickstart,
  safe agent-skill installation, and bounded post-publish verification.
---
# End-to-End Testing Runbook

This runbook connects repository tests to the boundaries users actually cross: an
installed wheel or npm tarball, copied documentation, agent configuration, and public
registry bytes.
Record which phases ran; do not turn an unexecuted command into a release
claim.

Run Phases 1–4 after changes to the CLI, public API, packaging, bundled resources,
examples, or agent instructions.
Run all phases for a release candidate.

## What CI Covers

[`ci.yml`](../.github/workflows/ci.yml) currently enforces:

- Python lint, type checks, unit tests across the supported Python range, and a
  hash-constrained wheel build.
- TypeScript formatting, type checks, tests with coverage, build, and `publint`.
- Python, Node, and Bun golden runs plus a direct Python↔TypeScript byte diff.
- The draft conformance corpus under Python, Node, and Bun.
- Frozen dependency audits.
- One immutable wheel, sdist, npm tarball, and consumer lock smoked across Linux, macOS,
  and Windows at runtime bounds.

Manual checks still matter for commands copied literally from the README, skill
installation into a disposable repository, live release controls, and public registry
propagation.

## Phase 1: Repository Gates

Start from the repository root with the locked dependencies installed.
The release workflow uses its own pinned tool versions; use those pins when reproducing
a release failure.

```bash
uv run python devtools/lint.py --check
uv run pytest
uv build --build-constraint build-constraints.txt --require-hashes

cd packages/typescript
bun run typecheck
bun run lint:ci
bun test --coverage
bun run build
bun run publint
cd ../..
```

Validate the machine-readable public claims, generated agent shims, conformance closure,
every implementation adapter, goldens, and the direct parity invariant:

```bash
uv run python devtools/public_claims.py --check --json
uv run python devtools/sync_agent_instructions.py --check
uv run python conformance/run.py --check-only --json
uv run python conformance/run.py --implementation all --json

SOFTSCHEMA_IMPL=py bash tests/golden/run.sh
SOFTSCHEMA_IMPL=ts bash tests/golden/run.sh
SOFTSCHEMA_IMPL=ts-bun bash tests/golden/run.sh
bash tests/golden/cross-impl-diff.sh
```

Success means every command exits zero.
Treat current counts as recorded observations, not hard-coded release facts: investigate
any unexpected drop in tests, declared schemas, ready cases, suites, or vectors.

Markdown formatting is a separate clean-tree gate.
Run `make format-check` only from a clean working tree because it executes the formatter
and then regenerates embedded sections, skill mirrors, and native agent adapters before
checking for a diff.
The corpus layout and parity rules are in [Golden Tests](../tests/golden/README.md) and
[Development](development.md).

## Phase 2: Installed Artifacts and Bundled Resources

Source-checkout imports do not prove package correctness.
Build once, then use the artifact driver to inspect and execute the wheel, sdist, npm
tarball, and locked npm consumer from unrelated directories:

```bash
uv run python devtools/installed_artifact_smoke.py
```

The driver rejects missing or internal files, mismatched release/build metadata, mutable
install resolution, lifecycle-script execution, broken entry points, and resource reads
that accidentally fall back to the checkout.

Also inspect the installed docs inventory.
Both CLIs must report the same topic list, and every public topic below must resolve
from package data rather than the current directory:

```bash
softschema docs --list --json
for topic in guide spec api agent-compatibility migration-0.3 security changelog \
  example-model example-model-ts example-host example-host-ts; do
  softschema docs "$topic" >/dev/null
done
softschema skill --brief >/dev/null
```

Run the same commands through the installed npm entry point.
In the repository, `packages/python/tests/test_public_documentation.py` and
`packages/typescript/test/doc-topics-resolve.test.ts` keep topic names, links, package
manifests, and bundled resources aligned.

## Phase 3: README Quickstart as Written

The README uses exact published pins.
Run both blocks verbatim from an empty directory, then compare their output bytes:

```bash
tmp="$(mktemp -d)"
mkdir "$tmp/python" "$tmp/typescript"

cd "$tmp/python"
uvx --from 'softschema==0.2.2' softschema docs example-artifact > spirited-away.md
uvx --from 'softschema==0.2.2' softschema docs example-schema > movie-page.schema.yaml
uvx --from 'softschema==0.2.2' softschema validate spirited-away.md

cd "$tmp/typescript"
npx --yes softschema@0.2.2 docs example-artifact > spirited-away.md
npx --yes softschema@0.2.2 docs example-schema > movie-page.schema.yaml
npx --yes softschema@0.2.2 validate spirited-away.md

cmp "$tmp/python/spirited-away.md" "$tmp/typescript/spirited-away.md"
cmp "$tmp/python/movie-page.schema.yaml" "$tmp/typescript/movie-page.schema.yaml"
```

Before a new version is public, repeat the same flow against the locally built wheel and
npm tarball from Phase 2. Do not replace README pins with a candidate that cannot be
resolved from its advertised registry.

The artifact names `movie-page.schema.yaml`; changing that filename correctly produces
`schema_missing`. Keep the artifact and schema together when reproducing the
zero-configuration validation path.

## Phase 4: Safe Agent-Skill Bootstrap

Exercise capability discovery, a no-write plan, installation, and an idempotent second
run in a disposable Git repository:

```bash
tmp="$(mktemp -d)"
git -C "$tmp" init -q
cd "$tmp"

softschema doctor --json
softschema skill --install --project --all-agents --dry-run --text
softschema skill --install --project --all-agents --text
softschema skill --install --project --all-agents --text
```

The dry run must describe the same nine native destinations as the write.
The first write reports `created`; the second reports `unchanged`. Inspect at least the
portable and Claude copies and confirm their managed payloads match the bundled skill.

Prove that unmanaged content is never clobbered in a second scratch repository:

```bash
conflict="$(mktemp -d)"
git -C "$conflict" init -q
mkdir -p "$conflict/.agents/skills/softschema"
printf 'user-owned\n' > "$conflict/.agents/skills/softschema/SKILL.md"

if softschema skill --install --project --dir "$conflict" --dry-run --text; then
  echo "expected an ownership conflict" >&2
  exit 1
fi
test "$(cat "$conflict/.agents/skills/softschema/SKILL.md")" = user-owned
```

Live discovery and activation are product-specific checks.
Record the product and version actually exercised and preserve `Not observed` where no
representative product run occurred; installing a file is not proof that a host
activated it.

## Phase 5: Protected Release and Registry Verification

[`publish.yml`](../.github/workflows/publish.yml) is a resumable state machine driven by
the external release manifest and `devtools/release_state.py`:

Before pushing a release tag, verify that repository-level immutable releases are
enabled:

```bash
gh api -H 'X-GitHub-Api-Version: 2026-03-10' \
  repos/jlevy/softschema/immutable-releases --jq .enabled
```

The result must be `true`. This is an administrator-owned repository prerequisite, not
something the release workflow enables.
The workflow checks it before its first GitHub release mutation and again immediately
before publishing the final draft.

Also re-read the `github-release` environment and its deployment policies:

```bash
gh api -H 'X-GitHub-Api-Version: 2026-03-10' \
  repos/jlevy/softschema/environments/github-release
gh api -H 'X-GitHub-Api-Version: 2026-03-10' \
  repos/jlevy/softschema/environments/github-release/deployment-branch-policies
```

It must exist before the tag run, require a reviewer, disallow administrator bypass, and
restrict deployments to `v*` tags.
A workflow reference alone is not evidence that those protections exist.

1. Preflight builds and freezes one candidate; smoke installs those exact bytes.
2. A protected tag may create or reuse a GitHub draft, require its exact asset
   inventory, and attest the primary manifest subjects.
3. Registry classifiers label the manifest-selected PyPI and npm subjects as absent,
   complete, partial where supported, or conflicting.
   Conflicting bytes fail closed; only missing exact subjects are eligible for
   publication.
4. Bounded verification requires registry digests, channels, and provenance for the
   frozen subjects.
5. Only after both registries verify does the workflow publish the existing GitHub draft
   and require the published release to be immutable.
   It never rebuilds or silently replaces an asset.

A manual `workflow_dispatch` runs build and smoke only.
It never creates a release or publishes to either registry.
Therefore it is an infrastructure check, not a protected tag rehearsal.

After the protected-tag workflow succeeds, independently resolve the public packages
from outside the checkout.
A new PyPI version is inside the repository’s 14-day cool-off, so use a full current
timestamp and refresh the index:

```bash
cd /tmp
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
uvx --refresh --exclude-newer-package "softschema=$ts" \
  --from 'softschema==X.Y.Z' softschema --version
npx --yes softschema@X.Y.Z --version
```

Then rerun the Phase 3 quickstart with `X.Y.Z`. Registry propagation is bounded in the
workflow but can still lag at a client CDN edge; retry only after confirming the
workflow’s digest and provenance gates passed.
Never accept a same-version byte mismatch as propagation.

## Record the Result

For a release-sized change, record the commit, toolchain versions, phase coverage,
test/conformance summaries, parity result, installed-artifact result, agent products
actually observed, and public version checks in the dated review or release record.
Separate automated evidence, manual evidence, and unavailable external state.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
