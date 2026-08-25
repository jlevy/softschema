#!/bin/bash
# Install dev dependencies and the lefthook-managed git hooks.
# Runs on SessionStart, remote sessions only.
#
# Why this exists: the repo's formatting contract lives in the pre-commit hook
# (lefthook.yml -> `make format` -> flowmark + regenerate the softschema:generated
# sections + reinstall the skill mirrors). A fresh remote container has no
# node_modules and no .git/hooks, so that hook is inert and an agent can commit
# Markdown the pipeline would have reformatted — or, worse, run flowmark by hand
# without the regeneration step and break the generated-section drift test.
# Installing the hooks makes the contract enforce itself here the same way it
# does on a developer's machine.
#
# `make install` also gets the Python venv, the root Node tooling, and the
# TypeScript package deps in place, which is what the test suites and linters
# need. The container image is cached after this completes, so the cost is paid
# once rather than per session.
#
# Local checkouts are skipped: developers run `make hooks-install` themselves,
# and this should not silently rewrite their git hooks.

set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
    exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

# Idempotent: lefthook rewrites the same hook files, uv/npm/bun all no-op when
# the lockfiles already match. Safe to re-run on resume and clear.
if make hooks-install; then
    echo "[dev-env] Dependencies and git hooks installed."
    echo "[dev-env] Markdown is formatted by the pre-commit hook; run 'make format' rather than flowmark directly."
    exit 0
fi

# Non-fatal by design. A network blip should degrade the session, not block it:
# the suites can still be run explicitly, and the reminder below is the fallback
# for the one thing the hook would have caught automatically.
echo "[dev-env] WARNING: 'make hooks-install' failed; git hooks are NOT active."
echo "[dev-env] Format Markdown with 'make format' before committing (never 'flowmark --auto .'"
echo "[dev-env] on its own — it skips regenerating the softschema:generated sections)."
exit 0
