"""The committed skill mirrors must stay in sync with the source skill.

This is the drift test the cli-agent-skill-patterns guideline calls for under the
"commit and dogfood" model: regenerate the install payload from
``skills/softschema/SKILL.md`` and fail if either committed mirror differs. The skill
uses the exact ecosystem pins from release metadata; the mirrors compare byte-for-byte
against the reviewed source emission.
"""

from __future__ import annotations

from pathlib import Path

from softschema.cli import SKILL_DO_NOT_EDIT_MARKER, SKILL_INSTALL_TARGETS
from softschema.skill_installer import install_skill_payload

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "skills/softschema/SKILL.md"


def test_committed_skill_mirrors_match_source() -> None:
    expected = install_skill_payload(SOURCE.read_text(encoding="utf-8"), SKILL_DO_NOT_EDIT_MARKER)
    for relative in SKILL_INSTALL_TARGETS:
        mirror = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert mirror == expected, (
            f"{relative} drifted from skills/softschema/SKILL.md; "
            "re-run `softschema skill --install` and commit"
        )


def test_committed_skill_mirrors_are_identical() -> None:
    contents = {(REPO_ROOT / rel).read_text(encoding="utf-8") for rel in SKILL_INSTALL_TARGETS}
    assert len(contents) == 1, "the .agents and .claude skill mirrors must be byte-identical"
