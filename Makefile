# Makefile for easy development workflows.
# GitHub Actions call uv directly; this is for local convenience.

.DEFAULT_GOAL := default

.PHONY: default install hooks-install format format-check lint lint-check test upgrade build clean

# Pinned for stability — bump deliberately. flowmark-rs is a first-party package
# (github.com/jlevy/flowmark); the --exclude-newer-package exception admits the pinned
# release past the repo's supply-chain cool-off, mirroring the strif handling in
# pyproject.toml and the practical-prose repo. Bump the version and the date together.
FLOWMARK_VERSION := 0.3.1
FLOWMARK := uvx --exclude-newer-package 'flowmark-rs=2026-06-02' flowmark-rs@$(FLOWMARK_VERSION)

default: install format lint test

# One-time local setup: Python deps, the root Node tooling that powers the git hooks
# (lefthook), and the TypeScript package deps (so the biome pre-commit hook resolves a
# lockfile-backed local binary instead of fetching one). GitHub Actions call uv / bun /
# npx directly, not this Makefile.
install:
	uv sync --all-extras
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
	uv run softschema generate examples/movie_page/README.md
	uv run softschema skill --install

# CI-mode Markdown check: run the FULL format pipeline, then fail if it would
# change anything. flowmark-rs has no native --check, so we approximate via git
# diff. This must run the same steps as `format` (flowmark + regenerate the
# derived sections + reinstall the skill mirrors), not flowmark alone: flowmark
# adds blank lines around the block elements inside softschema:generated markers
# that the generator does not emit, so a flowmark-only check reports false drift
# on an otherwise-canonical tree. Requires a clean working tree before running.
format-check:
	$(FLOWMARK) --auto .
	uv run softschema generate examples/movie_page/README.md
	uv run softschema skill --install
	@git diff --exit-code -- '*.md' || \
	  (echo "Markdown formatting drift; run 'make format' and commit." && exit 1)

lint:
	uv run python devtools/lint.py

lint-check:
	uv run python devtools/lint.py --check

test:
	uv run pytest

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
