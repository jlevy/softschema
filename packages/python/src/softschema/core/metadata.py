"""Portable artifact metadata vocabulary."""

from __future__ import annotations

from enum import StrEnum

ARTIFACT_FORMAT_VERSION = "1"


class SchemaStatus(StrEnum):
    """How strongly a project treats a soft schema at a boundary."""

    soft = "soft"
    permissive = "permissive"
    enforced = "enforced"


class SchemaProfile(StrEnum):
    """Storage shape for an artifact."""

    frontmatter_md = "frontmatter-md"
    pure_yaml = "pure-yaml"
