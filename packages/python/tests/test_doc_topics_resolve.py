"""Every DOC_TOPICS entry must resolve via _read_resource without raising.

This guards against drift between the DOC_TOPICS registry and the
wheel force-include / dev-repo file tree.
"""

from __future__ import annotations

import pytest

from softschema.cli import DOC_TOPICS, ResourceTopic, _read_resource


@pytest.mark.parametrize("name,topic", sorted(DOC_TOPICS.items()), ids=sorted(DOC_TOPICS))
def test_doc_topic_resolves(name: str, topic: ResourceTopic) -> None:
    content = _read_resource(topic.path)
    assert isinstance(content, str)
    assert len(content) > 0, f"DOC_TOPICS[{name!r}] resolved but was empty"
