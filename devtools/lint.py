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
    "conformance",
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
    Path("conformance/README.md"),
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
