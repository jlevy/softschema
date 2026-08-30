from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rich import get_console, reconfigure
from rich import print as rprint

SRC_PATHS = [
    "packages/python/src",
    "packages/python/tests",
    "devtools",
    "examples",
    # The golden-corpus runner is Python too, and is exactly the kind of script that
    # rots unnoticed: nothing imports it, so only CI would ever find a mistake in it.
    "tests/golden/run_golden_tests.py",
]
DOC_PATHS = [
    "README.md",
    "AGENTS.md",
    "docs",
    "examples",
    "skills",
    "packages/python/README.md",
    "packages/typescript",
]
DOC_FOOTER = (
    "<!-- This document follows common-doc-guidelines.md.\n"
    "See github.com/jlevy/practical-prose and review guidelines before editing.\n-->\n"
)
DOC_FOOTER_PATHS = [
    Path("README.md"),
    Path("AGENTS.md"),
    Path("docs"),
    Path("examples/movie_page/README.md"),
    Path("packages/python/README.md"),
    Path("packages/typescript/README.md"),
    Path("skills"),
]

reconfigure(emoji=not get_console().options.legacy_windows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run linting and formatting.")
    parser.add_argument("--check", action="store_true", help="Check only, without modifying files.")
    args = parser.parse_args()

    errcount = 0
    if args.check:
        errcount += run(["codespell", *SRC_PATHS, *DOC_PATHS])
        errcount += run(["ruff", "check", *SRC_PATHS])
        errcount += run(["ruff", "format", "--check", *SRC_PATHS])
    else:
        errcount += run(["codespell", "--write-changes", *SRC_PATHS, *DOC_PATHS])
        errcount += run(["ruff", "check", "--fix", *SRC_PATHS])
        errcount += run(["ruff", "format", *SRC_PATHS])
    errcount += run(["basedpyright", *SRC_PATHS])
    errcount += check_doc_footers()
    errcount += check_retired_surface()

    if errcount:
        rprint(f"[bold red]Lint failed with {errcount} failing command(s).[/bold red]")
    else:
        rprint("[bold green]Lint passed.[/bold green]")
    return errcount


def check_doc_footers() -> int:
    rprint()
    rprint("[bold green]>> check doc footers[/bold green]")
    missing = [path for path in iter_doc_footer_files() if not has_doc_footer(path)]
    if missing:
        for path in missing:
            rprint(f"[bold red]Missing doc footer:[/bold red] {path}")
        return 1
    return 0


RETIRED_SURFACE = ("--check-repair", "checkRepair", "check_repair")  # retired-surface-ok
"""The retired repair flags, replaced by the `repair` command in the v0.8.0 line.
Never released under those names.

Grepped for rather than trusted to be gone, because the surface reached 20-odd files
across source, tests, docs, the agent skill, its two generated mirrors, and the bundled
TypeScript resource copies. A stale mention in any generated artifact is invisible to
review and would send an agent to a flag that no longer parses.
"""

RETIRED_SURFACE_MARKER = "retired-surface-ok"
"""Opt-out for a line that must name a retired flag: the tests asserting it is gone.

Honored on the offending line or the one above it, because a formatter decides where a
comment ends up — biome moves a trailing comment onto its own line when the statement is
near the width limit — and an opt-out that a reformat silently voids is worse than none.
"""

RETIRED_SURFACE_EXEMPT_DIRS = (Path("docs/project/reviews"), Path("docs/project/specs"))
"""Records of what was true when written. Rewriting them would falsify the history."""


def check_retired_surface() -> int:
    rprint()
    rprint("[bold green]>> check retired CLI surface[/bold green]")
    hits: list[str] = []
    for path in _iter_tracked_text_files():
        if any(path.is_relative_to(exempt) for exempt in RETIRED_SURFACE_EXEMPT_DIRS):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, 1):
            previous = lines[number - 2] if number >= 2 else ""
            if RETIRED_SURFACE_MARKER in line or RETIRED_SURFACE_MARKER in previous:
                continue
            if any(name in line for name in RETIRED_SURFACE):
                hits.append(f"{path}:{number}: {line.strip()[:96]}")
    if hits:
        rprint("[bold red]Retired CLI surface still referenced:[/bold red]")
        for hit in hits:
            rprint(f"  {hit}")
        rprint(
            "Use `repair`, `repair --dry-run`, or `repair --check`. A line that must name "
            f"the old flag (a test asserting its removal) carries `{RETIRED_SURFACE_MARKER}`."
        )
        return 1
    return 0


def _iter_tracked_text_files() -> list[Path]:
    """Every git-tracked file, so generated mirrors and resource copies are covered too."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z"], text=True, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [Path(name) for name in listed.split("\0") if name]


def has_doc_footer(path: Path) -> bool:
    return path.read_text(encoding="utf-8").endswith(DOC_FOOTER)


def iter_doc_footer_files() -> list[Path]:
    files: list[Path] = []
    for path in DOC_FOOTER_PATHS:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return files


def run(cmd: list[str]) -> int:
    rprint()
    rprint(f"[bold green]>> {' '.join(cmd)}[/bold green]")
    try:
        subprocess.run(cmd, text=True, check=True)
    except KeyboardInterrupt:
        rprint("[yellow]Keyboard interrupt - cancelled.[/yellow]")
        return 1
    except subprocess.CalledProcessError as exc:
        rprint(f"[bold red]Error: {exc}[/bold red]")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
