# Makefile for easy development workflows.
# GitHub Actions call uv directly; this is for local convenience.

.DEFAULT_GOAL := default

.PHONY: default install lint lint-check test upgrade build clean

default: install lint test

install:
	uv sync --all-extras

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
