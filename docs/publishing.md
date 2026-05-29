# Publishing

The package uses dynamic Git versioning via `uv-dynamic-versioning`: the wheel and sdist
versions are derived from the most recent `vX.Y.Z` Git tag.
Pushing a `vX.Y.Z` tag and creating a matching GitHub release triggers
[`publish.yml`](../.github/workflows/publish.yml), which builds and publishes the
package to PyPI via trusted publishing.

## Versioning Convention

- **Documentation pins to the next/current release**, not the most recently published
  one. As soon as `vX.Y.Z` is published, bump `uvx softschema@X.Y.(Z+1)` references in
  the README (and any other version-pinned docs) and commit that bump.
  This keeps a reader who copies a command from `main` running the version we are about
  to ship rather than the one we just shipped.
- The `<version>` token in [skills/softschema/SKILL.md](../skills/softschema/SKILL.md)
  is intentionally left as a template literal; the CLI substitutes it with the installed
  package version at runtime (in both `softschema skill` output and
  `softschema skill --install`). It does not need a per-release bump.
- Patch bumps (`0.1.Z`) cover docs-only changes and small additive features.
  Reserve minor bumps (`0.Y.0`) for changes that meaningfully shift the API or spec.

## PyPI Trusted Publishing

Configured once at the project level on PyPI:

- project name: `softschema`
- owner/repo: `jlevy/softschema`
- workflow: `publish.yml`

## Release Checklist

For each release of version `X.Y.Z`:

1. **Confirm doc-pinned versions match the planned tag.** The README example commands
   should already say `uvx softschema@X.Y.Z` from the previous release’s post-bump
   commit; if not, fix them first.

2. **Run the full local check sweep** (mirrors what CI runs):

   ```bash
   make format       # flowmark + `softschema generate`; never run raw flowmark
   make lint test    # ruff format, basedpyright, doc footers, pytest
   uv build          # builds dist/softschema-X.Y.Z.tar.gz and wheel
   ```

   Optionally smoke-test the built wheel in a clean venv to confirm the CLI loads and
   the bundled docs/skill are reachable.

3. **Commit and push** everything to `main` (working tree must be clean before tagging
   so the version derivation is unambiguous).

4. **Tag and push the tag:**

   ```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin vX.Y.Z
   ```

5. **Create the GitHub release** (this triggers the publish workflow):

   ```bash
   gh release create vX.Y.Z --title "softschema X.Y.Z" --notes "..."
   ```

6. **Watch the workflow** until it reports `Publish to PyPI` success:

   ```bash
   gh run watch <run-id> --exit-status
   ```

7. **Verify PyPI** has the new version, then smoke-test the published artifact:

   ```bash
   uvx --exclude-newer-package "softschema=$(date +%F)" \
     softschema@X.Y.Z --help
   ```

   (The `--exclude-newer-package` override is needed because the publish workflow sets
   `UV_EXCLUDE_NEWER` to a 14-day cool-off cutoff for supply-chain hygiene.
   Anyone consuming the freshly published version with that policy will see the same
   friction for ~14 days; this is intentional.)

8. **Bump doc pins to the next planned release** (`X.Y.(Z+1)` for the typical patch).
   Update `uvx softschema@X.Y.Z` → `uvx softschema@X.Y.(Z+1)` in the README; commit and
   push. This sets the stage so the next release’s checklist starts at step 1 with
   already-correct pins.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
