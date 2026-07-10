#!/usr/bin/env python3
"""Generate or check deterministic native instruction adapters from AGENTS.md."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOOTER = (
    "<!-- This document follows common-doc-guidelines.md.\n"
    "See github.com/jlevy/practical-prose and review guidelines before editing.\n"
    "-->\n"
)
COPILOT_MARKER = (
    "<!-- DO NOT EDIT: generated from AGENTS.md by devtools/sync_agent_instructions.py. -->\n\n"
)
MARKDOWN_LINK_DESTINATION = re.compile(
    r"(?P<prefix>!?\[[^\]\n]*\]\()"
    r"(?P<destination><[^>\n]+>|[^)\s]+)"
)
URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _rewrite_copilot_links(markdown: str) -> str:
    """Make repository-root-relative links work from the .github adapter."""

    def replace(match: re.Match[str]) -> str:
        destination = match.group("destination")
        wrapped = destination.startswith("<") and destination.endswith(">")
        target = destination[1:-1] if wrapped else destination
        if target.startswith(("#", "/", "../")) or URI_SCHEME.match(target):
            return match.group(0)
        rewritten = f"../{target}"
        if wrapped:
            rewritten = f"<{rewritten}>"
        return f"{match.group('prefix')}{rewritten}"

    return MARKDOWN_LINK_DESTINATION.sub(replace, markdown)


def expected_files() -> dict[Path, str]:
    """Return every generated adapter and its exact expected bytes."""
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    return {
        ROOT / "CLAUDE.md": f"@AGENTS.md\n\n{FOOTER}",
        ROOT / "GEMINI.md": f"@./AGENTS.md\n\n{FOOTER}",
        ROOT / ".github/copilot-instructions.md": (
            f"{COPILOT_MARKER}{_rewrite_copilot_links(agents)}"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing (default writes generated adapters)",
    )
    args = parser.parse_args(argv)

    drift: list[Path] = []
    for path, expected in expected_files().items():
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        if actual == expected:
            continue
        drift.append(path)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")

    if args.check and drift:
        for path in drift:
            print(f"agent instruction adapter drift: {path.relative_to(ROOT)}", file=sys.stderr)
        return 1
    if not args.check:
        action = "updated" if drift else "current"
        print(f"agent instruction adapters {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
