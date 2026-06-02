"""The committed skill mirrors must stay in sync with the source skill.

This is the drift test the cli-agent-skill-patterns guideline calls for under the
"commit and dogfood" model: regenerate the install payload from
``skills/softschema/SKILL.md`` and fail if either committed mirror differs. It tolerates
the version pin (dev builds vs the release pin) by rendering with the mirror's own pinned
version, so it catches *content* drift — exactly the failure that previously left the
mirrors pinned to a stale version.
"""

from __future__ import annotations

import re
from pathlib import Path

from softschema.cli import SKILL_INSTALL_TARGETS, _install_skill_payload

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "skills/softschema/SKILL.md"


def test_committed_skill_mirrors_match_source() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for relative in SKILL_INSTALL_TARGETS:
        mirror_path = REPO_ROOT / relative
        mirror = mirror_path.read_text(encoding="utf-8")
        match = re.search(r"softschema@(\S+)", mirror)
        assert match is not None, f"{relative} has no pinned version"
        version = match.group(1)
        expected = _install_skill_payload(source.replace("<version>", version))
        assert mirror == expected, (
            f"{relative} drifted from skills/softschema/SKILL.md; "
            "re-run `softschema skill --install` (at the release version) and commit"
        )


def test_committed_skill_mirrors_are_identical() -> None:
    contents = {(REPO_ROOT / rel).read_text(encoding="utf-8") for rel in SKILL_INSTALL_TARGETS}
    assert len(contents) == 1, "the .agents and .claude skill mirrors must be byte-identical"
