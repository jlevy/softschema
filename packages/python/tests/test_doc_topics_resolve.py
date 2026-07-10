"""Every DOC_TOPICS entry must resolve via _read_resource without raising.

This guards against drift between the DOC_TOPICS registry and the
wheel force-include / dev-repo file tree.
"""

from __future__ import annotations

from importlib import resources as importlib_resources
from pathlib import Path

import pytest

import softschema.cli as cli
from softschema.cli import DOC_TOPICS, ResourceTopic, _read_resource


@pytest.mark.parametrize(("name", "topic"), sorted(DOC_TOPICS.items()), ids=sorted(DOC_TOPICS))
def test_doc_topic_resolves(name: str, topic: ResourceTopic) -> None:
    content = _read_resource(topic.path)
    assert isinstance(content, str)
    assert len(content) > 0, f"DOC_TOPICS[{name!r}] resolved but was empty"


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


def test_installed_lookup_ignores_consumer_repository_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An installed CLI must not load agent instructions from its consumer repo."""
    relative = "skills/softschema/SKILL.md"
    consumer = tmp_path / "consumer"
    fake_module = consumer / ".venv/lib/python3.14/site-packages/softschema/cli.py"
    fake_module.parent.mkdir(parents=True)
    fake_module.write_text("# installed softschema module\n", encoding="utf-8")

    # This shape satisfied the old ancestor-walk heuristic and redirected the installed
    # CLI to the consumer-controlled skill.
    (consumer / "pyproject.toml").write_text("[project]\nname = 'consumer'\n", encoding="utf-8")
    (consumer / "docs").mkdir()
    shadow = consumer / relative
    shadow.parent.mkdir(parents=True)
    shadow.write_text("MALICIOUS CONSUMER SKILL\n", encoding="utf-8")

    package_root = tmp_path / "installed-package"
    bundled = package_root / "resources" / relative
    bundled.parent.mkdir(parents=True)
    bundled.write_text("BUNDLED SOFTSCHEMA SKILL\n", encoding="utf-8")

    monkeypatch.setattr(cli, "__file__", str(fake_module))
    monkeypatch.setattr(importlib_resources, "files", lambda _package: package_root)

    assert cli._read_resource(relative) == "BUNDLED SOFTSCHEMA SKILL\n"


def test_exact_source_checkout_prefers_live_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editable checkout runs keep reading the reviewed source resource."""
    relative = "skills/softschema/SKILL.md"
    package_root = tmp_path / "installed-package"
    bundled = package_root / "resources" / relative
    bundled.parent.mkdir(parents=True)
    bundled.write_text("STALE BUNDLED SKILL\n", encoding="utf-8")
    monkeypatch.setattr(importlib_resources, "files", lambda _package: package_root)

    repository = Path(__file__).resolve().parents[3]
    monkeypatch.setattr(
        cli,
        "__file__",
        str(repository / "packages/python/src/softschema/cli.py"),
    )
    expected = repository / relative
    assert cli._read_resource(relative) == expected.read_text(encoding="utf-8")
