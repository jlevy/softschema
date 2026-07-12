"""Every DOC_TOPICS entry must resolve via _read_resource without raising.

This guards against drift between the DOC_TOPICS registry and the
wheel force-include / dev-repo file tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from softschema.cli import DOC_TOPICS, ResourceTopic, _read_resource


@pytest.mark.parametrize(("name", "topic"), sorted(DOC_TOPICS.items()), ids=sorted(DOC_TOPICS))
def test_doc_topic_resolves(name: str, topic: ResourceTopic) -> None:
    content = _read_resource(topic.path)
    assert isinstance(content, str)
    assert len(content) > 0, f"DOC_TOPICS[{name!r}] resolved but was empty"


def test_consumer_checkout_cannot_shadow_source_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collision = tmp_path / "docs/softschema-guide.md"
    collision.parent.mkdir()
    collision.write_text("COLLISION\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='consumer'\n")
    monkeypatch.chdir(tmp_path)
    content = _read_resource("docs/softschema-guide.md")
    assert "# softschema Guide" in content
    assert "COLLISION" not in content


def test_doc_topics_are_bundled_in_the_wheel() -> None:
    """Every DOC_TOPICS path must be covered by the wheel force-include map.

    The dev-fallback in `_read_resource` makes the resolve test above pass even when a
    path is missing from the wheel bundle (the `typescript-design` topic shipped broken
    this way once). Parsing the force-include map catches that class without building a
    wheel: a topic path is covered when it equals a force-include source or sits under a
    force-included directory (e.g. `skills/...` under the `skills` entry).
    """
    import tomllib

    repo_root = Path(__file__).resolve().parents[3]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    sources = list(pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"].keys())

    def covered(path: str) -> bool:
        return any(path == src or path.startswith(f"{src}/") for src in sources)

    missing = sorted(topic.path for topic in DOC_TOPICS.values() if not covered(topic.path))
    assert not missing, f"DOC_TOPICS paths absent from wheel force-include: {missing}"
