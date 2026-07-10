"""Runtime-neutral source spans for parsed portable values."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, TypeAlias

JsonPathSegment: TypeAlias = str | int
SourceAnchor: TypeAlias = Literal["key", "value"]


@dataclass(frozen=True, order=True)
class SourcePoint:
    """One-based Unicode-code-point position in decoded source text."""

    line: int
    column: int

    def __post_init__(self) -> None:
        if self.line < 1 or self.column < 1:
            raise ValueError("source points must use positive one-based coordinates")


@dataclass(frozen=True)
class SourceSpan:
    """Half-open source span with an exclusive end point."""

    start: SourcePoint
    end: SourcePoint

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("source span end must not precede its start")


@dataclass(frozen=True)
class NodeSource:
    """Source spans for a value node and its mapping key, when one exists."""

    value: SourceSpan
    key: SourceSpan | None = None


@dataclass(frozen=True, init=False)
class SourceMap:
    """Immutable RFC 6901 pointer-to-source index with ancestor fallback."""

    nodes: Mapping[str, NodeSource]

    def __init__(
        self,
        entries: Mapping[str, NodeSource] | Iterable[tuple[str, NodeSource]] = (),
    ) -> None:
        copied = dict(entries.items() if isinstance(entries, Mapping) else entries)
        object.__setattr__(self, "nodes", MappingProxyType(copied))

    @classmethod
    def empty(cls) -> SourceMap:
        """Return an empty source map."""
        return cls()

    def node(self, pointer: str) -> NodeSource | None:
        """Return the exact mapped node for an RFC 6901 pointer."""
        return self.nodes.get(pointer)

    def span(
        self,
        pointer: str,
        *,
        anchor: SourceAnchor = "value",
        nearest: bool = True,
    ) -> SourceSpan | None:
        """Resolve a trusted internal pointer, optionally using its nearest ancestor."""
        candidate = pointer
        exact = True
        while True:
            node = self.nodes.get(candidate)
            if node is not None:
                if exact and anchor == "key" and node.key is not None:
                    return node.key
                return node.value
            if not nearest or candidate == "":
                return None
            candidate = candidate.rpartition("/")[0]
            exact = False

    def project(self, prefix: Sequence[JsonPathSegment]) -> SourceMap:
        """Rebase a mapped subtree so ``prefix`` becomes the projected root."""
        prefix_pointer = json_pointer(prefix)
        if prefix_pointer == "":
            return self
        projected: dict[str, NodeSource] = {}
        child_prefix = f"{prefix_pointer}/"
        for pointer, node in self.nodes.items():
            if pointer == prefix_pointer:
                projected[""] = node
            elif pointer.startswith(child_prefix):
                projected[pointer[len(prefix_pointer) :]] = node
        return SourceMap(projected)


def json_pointer(path: Sequence[JsonPathSegment]) -> str:
    """Render path segments as an RFC 6901 JSON Pointer."""
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in path)
