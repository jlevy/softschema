# Makefile for easy development workflows.
# GitHub Actions call uv directly; this is for local convenience.

.DEFAULT_GOAL := default

.PHONY: default install hooks-install format format-check lint lint-check test upgrade build clean

# Pinned for stability — bump deliberately. flowmark-rs is a first-party package
# (github.com/jlevy/flowmark); the --exclude-newer-package exception admits the pinned
# release past the repo's supply-chain cool-off, mirroring the strif handling in
# pyproject.toml and the practical-prose repo. --no-config prevents user-level uv
# settings from changing the project lock during formatting. Bump the version and the
# date together.
FLOWMARK_VERSION := 0.3.1
FLOWMARK := uvx --no-config --exclude-newer-package 'flowmark-rs=2026-06-02' flowmark-rs@$(FLOWMARK_VERSION)
# Generated-resource commands use the committed environment without resolving or
# inheriting user-level uv configuration.
UV_RUN := uv run --frozen --no-config
# A global UV_EXCLUDE_NEWER replaces pyproject's per-package map. Pin the complete
# reviewed boundary here so `make install` is frozen, ignores ambient config, and has
# the same exceptions as CI.
UV_SYNC := uv sync --all-extras --frozen --no-config \
	--exclude-newer 2026-06-02T00:00:00Z \
	--exclude-newer-package frontmatter-format=2026-08-01T01:26:20.316336Z \
	--exclude-newer-package strif=2026-06-03T00:00:00Z

default: install format lint test

# One-time local setup: Python deps, the root Node tooling that powers the git hooks
# (lefthook), and the TypeScript package deps (so the biome pre-commit hook resolves a
# lockfile-backed local binary instead of fetching one). GitHub Actions call uv / bun /
# npx directly, not this Makefile.
install:
	$(UV_SYNC)
	npm install --silent
	cd packages/typescript && bun install --frozen-lockfile

# Install the lefthook-managed git hooks (pre-commit: flowmark + ruff + biome).
# Run once after cloning. Bypass a hook for an emergency commit with --no-verify.
hooks-install: install
	npx --no-install lefthook install

# Auto-format all Markdown with flowmark-rs (semantic line breaks, smart quotes,
# safe cleanups). Pass `.` as the sole target so flowmark traverses the repo
# and honors .flowmarkignore + .gitignore. Flowmark-rs only reads
# .flowmarkignore relative to its target arg, so passing subdirs or globs
# bypasses it.
#
# After flowmark touches the prose, regenerate the derived artifacts so they stay
# byte-identical to their canonical source: (1) softschema:generated sections (flowmark
# adds blank lines around block elements the generator does not emit), and (2) the skill
# mirrors under .agents/ and .claude/, which are flowmark-ignored and so must be
# re-installed from the just-reflowed skills/softschema/SKILL.md. Without these steps the
# generate / skill-mirror drift tests fail after a format-only pass.
format:
	$(FLOWMARK) --auto .
	$(UV_RUN) softschema generate examples/movie_page/README.md
	$(UV_RUN) softschema skill --install --scope project --agent portable --agent claude

# CI-mode Markdown check: run the FULL format pipeline, then fail if it would
# change anything. flowmark-rs has no native --check, so we approximate via git
# diff. This must run the same steps as `format` (flowmark + regenerate the
# derived sections + reinstall the skill mirrors), not flowmark alone: flowmark
# adds blank lines around the block elements inside softschema:generated markers
# that the generator does not emit, so a flowmark-only check reports false drift
# on an otherwise-canonical tree. Requires a clean working tree before running.
format-check:
	$(FLOWMARK) --auto .
	$(UV_RUN) softschema generate examples/movie_page/README.md
	$(UV_RUN) softschema skill --install --scope project --agent portable --agent claude
	@git diff --exit-code -- '*.md' || \
	  (echo "Markdown formatting drift; run 'make format' and commit." && exit 1)

lint:
	$(UV_RUN) python devtools/lint.py

lint-check:
	$(UV_RUN) python devtools/lint.py --check

test:
	$(UV_RUN) pytest

upgrade:
	uv sync --upgrade --all-extras --dev

build:
	uv build

clean:
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .ruff_cache/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
