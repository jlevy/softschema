# Makefile for easy development workflows.
# GitHub Actions call uv directly; this is for local convenience.

.DEFAULT_GOAL := default

.PHONY: default install format format-check lint lint-check test upgrade build clean

# Pinned for stability — bump deliberately.
FLOWMARK := uvx flowmark-rs@0.2.6

default: install format lint test

install:
	uv sync --all-extras

# Auto-format all Markdown with flowmark-rs (semantic line breaks, smart quotes,
# safe cleanups). Pass `.` as the sole target so flowmark traverses the repo
# and honors .flowmarkignore + .gitignore. Flowmark-rs only reads
# .flowmarkignore relative to its target arg, so passing subdirs or globs
# bypasses it.
#
# After flowmark touches the prose, regenerate any softschema:generated
# sections so the marker bodies stay byte-identical to the canonical output
# (flowmark adds blank lines around block elements that the generator does
# not emit; without this step the generate drift test would fail after a
# format-only pass).
format:
	$(FLOWMARK) --auto .
	uv run softschema generate examples/movie_page/README.md

# CI-mode Markdown check: run flowmark, then fail if it would change anything.
# flowmark-rs has no native --check; we approximate via git diff. Requires a
# clean working tree (Markdown-wise) before running.
format-check:
	$(FLOWMARK) --auto .
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
