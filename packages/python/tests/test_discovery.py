"""Shared-vector tests for deterministic runtime artifact discovery."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import cast

import pytest

from softschema.runtime.discovery import (
    DISCOVERY_MAX_DEPTH,
    DISCOVERY_MAX_ENTRIES,
    GLOB_MAX_INTERIOR_MATCH_COMPLEXITY,
    GLOB_MAX_INVOCATION_MATCH_WORK,
    GLOB_MAX_PATTERN_CODEPOINTS,
    GLOB_MAX_PATTERNS,
    GLOB_MAX_TOTAL_MATCH_COMPLEXITY,
    GLOB_MAX_TOTAL_PATTERN_CODEPOINTS,
    GLOB_MAX_TOTAL_TOKENS,
    CompiledGlob,
    DiscoveryFileInfo,
    DiscoveryFileKind,
    DiscoveryPathFlavor,
    DiscoveryProfile,
    DiscoveryRequest,
    DiscoveryUsageError,
    GlobPatternError,
    discover_artifacts,
)

ROOT = Path(__file__).parents[3]
BATCH_VECTORS = ROOT / "tests" / "batch"


def _load_json(name: str) -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((BATCH_VECTORS / name).read_text(encoding="utf-8")),
    )


def _expand_adversarial_glob(vector: dict[str, object]) -> tuple[str, str, str]:
    """Expand one compact shared stress vector into a pattern, match, and miss."""
    length = cast("int", vector["length"])
    shape = cast("str", vector["shape"])
    if shape == "question_segment":
        return (
            "?" * length + ".md",
            "a" * length + ".md",
            "a" * (length - 1) + ".md",
        )
    if shape == "leading_star_segment":
        return "*.md", "a" * length + ".md", "a" * length + ".txt"
    if shape == "star_required_suffix":
        return "*" + "?" * length, "a" * length, "a" * 64
    if shape == "repeated_globstar":
        return "/".join([*(["**"] * length), "target.md"]), "target.md", "other.md"
    repeated = ["x"] * length
    if shape == "literal_segments":
        return (
            "/".join([*repeated, "target.md"]),
            "/".join([*repeated, "target.md"]),
            "/".join([*repeated[:64], "other.md"]),
        )
    if shape == "leading_globstar":
        return (
            "**/target.md",
            "/".join([*repeated, "target.md"]),
            "/".join([*repeated, "other.md"]),
        )
    raise AssertionError(f"unknown adversarial glob shape: {shape}")


class VectorFileSystem:
    """In-memory filesystem boundary used identically by the Python and TS vectors."""

    def __init__(self, case: dict[str, object]) -> None:
        nodes = cast("list[dict[str, object]]", case["nodes"])
        failures = cast("list[dict[str, str]]", case["failures"])
        self.nodes = {cast("str", node["path"]): node for node in nodes}
        self.failures = {
            (failure["operation"], failure["path"]): failure["code"] for failure in failures
        }
        self.calls: list[tuple[str, str]] = []

    def _fail(self, operation: str, path: str) -> None:
        self.calls.append((operation, path))
        code = self.failures.get((operation, path))
        if code == "not_found":
            raise FileNotFoundError(path)
        if code == "unreadable":
            raise PermissionError(path)

    def _node(self, path: str) -> dict[str, object]:
        node = self.nodes.get(path)
        if node is None:
            raise FileNotFoundError(path)
        return node

    @staticmethod
    def _info(node: dict[str, object]) -> DiscoveryFileInfo:
        device = node.get("device")
        inode = node.get("inode")
        return DiscoveryFileInfo(
            kind=cast("DiscoveryFileKind", node["kind"]),
            device=None if device is None else int(cast("str", device)),
            inode=None if inode is None else int(cast("str", inode)),
        )

    def lstat(self, path: str) -> DiscoveryFileInfo:
        self._fail("lstat", path)
        return self._info(self._node(path))

    def stat(self, path: str) -> DiscoveryFileInfo:
        self._fail("stat", path)
        seen: set[str] = set()
        current = path
        while True:
            if current in seen:
                raise OSError("symlink loop")
            seen.add(current)
            node = self._node(current)
            if node["kind"] != "symlink":
                return self._info(node)
            current = cast("str", node["target"])

    def read_directory(self, path: str, limit: int) -> tuple[str, ...]:
        self._fail("read_directory", path)
        node = self._node(path)
        if node["kind"] != "directory":
            raise NotADirectoryError(path)
        return tuple(cast("list[str]", node.get("entries", []))[:limit])

    def realpath(self, path: str) -> str:
        self._fail("realpath", path)
        seen: set[str] = set()
        current = path
        while True:
            if current in seen:
                raise OSError("symlink loop")
            seen.add(current)
            node = self._node(current)
            configured = node.get("realpath")
            if configured is not None:
                return cast("str", configured)
            if node["kind"] != "symlink":
                return current
            current = cast("str", node["target"])


def _wide_entry_name(index: int, matching_index: int | None) -> str:
    extension = ".md" if index == matching_index else ".txt"
    return f"entry-{index:06d}{extension}"


class LimitVectorFileSystem:
    """Generate compact deep and wide shared-vector filesystems on demand."""

    root = "/work/root"

    def __init__(self, case: dict[str, object]) -> None:
        self.case = case
        self.reads: list[tuple[str, int, int]] = []

    def lstat(self, path: str) -> DiscoveryFileInfo:
        if path == "/work/after.md":
            return DiscoveryFileInfo(kind="file", device=32, inode=1)
        if path == self.root:
            return DiscoveryFileInfo(kind="directory", device=30, inode=1)
        relative = path.removeprefix(f"{self.root}/")
        if relative == path:
            raise FileNotFoundError(path)
        if self.case["shape"] == "depth":
            parts = relative.split("/")
            if parts[-1] in {"a-early.md", "leaf.md"}:
                return DiscoveryFileInfo(kind="file", device=30, inode=10_000)
            return DiscoveryFileInfo(kind="directory", device=30, inode=len(parts) + 1)
        name = relative.rsplit("/", 1)[-1]
        if "/" in relative or not name.startswith("entry-"):
            raise FileNotFoundError(path)
        index = int(name[6:12])
        return DiscoveryFileInfo(kind="file", device=31, inode=index + 1)

    def stat(self, path: str) -> DiscoveryFileInfo:
        return self.lstat(path)

    def read_directory(self, path: str, limit: int) -> tuple[str, ...]:
        if self.case["shape"] == "depth":
            relative = path.removeprefix(f"{self.root}/")
            depth = 0 if path == self.root else len(relative.split("/"))
            directory_depth = cast("int", self.case["directory_depth"])
            if depth < directory_depth:
                if depth == 0 and self.case.get("early_match") is True:
                    names = (f"d{depth:03d}", "a-early.md")
                else:
                    names = (f"d{depth:03d}",)
            else:
                names = ("leaf.md",)
            result = names[:limit]
        else:
            if path != self.root:
                raise NotADirectoryError(path)
            count = cast("int", self.case["entry_count"])
            matching_index = cast("int | None", self.case["matching_index"])
            materialized = min(count, limit)
            result = tuple(
                _wide_entry_name(count - offset - 1, matching_index)
                for offset in range(materialized)
            )
        self.reads.append((path, limit, len(result)))
        return result

    def realpath(self, path: str) -> str:
        return path


def _expected_limit_result(
    case: dict[str, object],
) -> list[dict[str, object]]:
    if case["shape"] == "depth":
        directory_depth = cast("int", case["directory_depth"])
        relative_directory = "/".join(f"d{index:03d}" for index in range(directory_depth))
        if case["expected"] == "artifact":
            relative = f"root/{relative_directory}/leaf.md"
            return [
                {
                    "path": f"/work/{relative}",
                    "display_path": relative,
                    "kind": "artifact",
                }
            ]
        source = f"root/{relative_directory}"
    else:
        matching_index = cast("int | None", case["matching_index"])
        if case["expected"] == "artifact":
            name = _wide_entry_name(cast("int", matching_index), matching_index)
            return [
                {
                    "path": f"/work/root/{name}",
                    "display_path": f"root/{name}",
                    "kind": "artifact",
                }
            ]
        source = "root"
    return [
        {
            "reason": "discovery_limit",
            "message": "artifact discovery limit exceeded",
            "source": source,
            "kind": "input_error",
        }
    ]


def test_shared_glob_vectors() -> None:
    vectors = _load_json("glob-vectors.json")
    assert vectors["limits"] == {
        "max_interior_match_complexity": GLOB_MAX_INTERIOR_MATCH_COMPLEXITY,
        "max_pattern_codepoints": GLOB_MAX_PATTERN_CODEPOINTS,
        "max_total_pattern_codepoints": GLOB_MAX_TOTAL_PATTERN_CODEPOINTS,
        "max_patterns": GLOB_MAX_PATTERNS,
        "max_total_tokens": GLOB_MAX_TOTAL_TOKENS,
        "max_total_match_complexity": GLOB_MAX_TOTAL_MATCH_COMPLEXITY,
        "max_invocation_match_work": GLOB_MAX_INVOCATION_MATCH_WORK,
    }
    for vector in cast("list[dict[str, object]]", vectors["valid"]):
        compiled = CompiledGlob.compile(cast("str", vector["pattern"]))
        for candidate in cast("list[str]", vector["matches"]):
            assert compiled.matches(candidate), f"{vector['id']}: {candidate}"
        for candidate in cast("list[str]", vector["misses"]):
            assert not compiled.matches(candidate), f"{vector['id']}: {candidate}"

    for vector in cast("list[dict[str, str]]", vectors["invalid"]):
        with pytest.raises(GlobPatternError) as caught:
            CompiledGlob.compile(vector["pattern"])
        assert caught.value.reason == vector["reason"]
        quoted = json.dumps(vector["pattern"], ensure_ascii=False)
        assert str(caught.value) == f"invalid glob {quoted}: {vector['reason']}"


def test_shared_adversarial_glob_vectors_do_not_recurse() -> None:
    vectors = _load_json("glob-vectors.json")
    for vector in cast("list[dict[str, object]]", vectors["adversarial"]):
        pattern, matching, missing = _expand_adversarial_glob(vector)
        compiled = CompiledGlob.compile(pattern)
        assert compiled.matches(matching), vector["id"]
        assert not compiled.matches(missing), vector["id"]


def test_glob_matcher_is_linear_for_unbounded_anchored_chunks() -> None:
    large_length = 200_000
    required_suffix = "?" * large_length
    compiled = CompiledGlob.compile(f"*{required_suffix}")

    assert compiled.matches("a" * large_length)
    assert compiled.matches("prefix" + "a" * large_length)
    assert not compiled.matches("a" * (large_length - 1))


def test_glob_matcher_bounds_interior_search_and_preserves_exact_matches() -> None:
    overlap_length = 20_000
    interior = "a" * (GLOB_MAX_INTERIOR_MATCH_COMPLEXITY - 1) + "b"
    compiled = CompiledGlob.compile(f"*{interior}*")

    assert compiled.matches("a" * overlap_length + "b")
    assert not compiled.matches("a" * overlap_length + "c")

    over_limit = "a" * (GLOB_MAX_INTERIOR_MATCH_COMPLEXITY + 1)
    with pytest.raises(GlobPatternError) as caught:
        CompiledGlob.compile(f"*{over_limit}*")
    assert caught.value.reason == "match_work_limit"

    normalized_class = CompiledGlob.compile(f"*[{over_limit}]*")
    assert normalized_class.matches("a")
    assert not normalized_class.matches("b")


def test_multi_star_glob_uses_earliest_exact_interior_matches() -> None:
    compiled = CompiledGlob.compile("start*a?c*[x-z]9*end")

    assert compiled.matches("start--abc--y9--end")
    assert compiled.matches("startaXcx9end")
    assert not compiled.matches("start--abc--w9--end")
    assert not compiled.matches("start--ab--y9--end")


def test_shared_filesystem_vectors() -> None:
    vectors = _load_json("filesystem-vectors.json")
    for case in cast("list[dict[str, object]]", vectors["cases"]):
        filesystem = VectorFileSystem(case)
        request = DiscoveryRequest(
            operands=tuple(cast("list[str]", case["operands"])),
            recursive=cast("bool", case["recursive"]),
            profile=cast("DiscoveryProfile", case["profile"]),
            includes=tuple(cast("list[str]", case["includes"])),
            excludes=tuple(cast("list[str]", case["excludes"])),
            invocation_directory=cast("str", case["cwd"]),
            path_flavor=cast("DiscoveryPathFlavor", case["platform"]),
        )
        result = discover_artifacts(request, filesystem=filesystem)
        assert [asdict(entry) for entry in result.entries] == case["expected"], case["id"]


def test_shared_discovery_limit_vectors() -> None:
    vectors = _load_json("discovery-limit-vectors.json")
    limits = cast("dict[str, int]", vectors["limits"])
    assert limits == {
        "max_depth": DISCOVERY_MAX_DEPTH,
        "max_entries": DISCOVERY_MAX_ENTRIES,
    }
    for case in cast("list[dict[str, object]]", vectors["cases"]):
        filesystem = LimitVectorFileSystem(case)
        result = discover_artifacts(
            DiscoveryRequest(
                operands=(
                    "root",
                    *(("after.md",) if case.get("following_operand") is True else ()),
                ),
                recursive=True,
                profile="frontmatter-md",
                includes=(),
                excludes=(),
                invocation_directory="/work",
                path_flavor="posix",
            ),
            filesystem=filesystem,
        )
        assert all(materialized <= requested for _, requested, materialized in filesystem.reads)
        if case["shape"] == "entries":
            expected_materialized = min(cast("int", case["entry_count"]), limits["max_entries"] + 1)
            assert filesystem.reads == [
                ("/work/root", limits["max_entries"] + 1, expected_materialized)
            ]
        expected = _expected_limit_result(case)
        if case.get("following_operand") is True:
            expected.append(
                {
                    "path": "/work/after.md",
                    "display_path": "after.md",
                    "kind": "artifact",
                }
            )
        assert [asdict(entry) for entry in result.entries] == expected, case["id"]


def test_request_validation_precedes_filesystem_access() -> None:
    case: dict[str, object] = {"nodes": [], "failures": []}
    filesystem = VectorFileSystem(case)
    with pytest.raises(DiscoveryUsageError, match="at least one operand"):
        discover_artifacts(
            DiscoveryRequest(
                operands=(),
                recursive=False,
                profile="frontmatter-md",
                includes=(),
                excludes=(),
                invocation_directory="/work",
                path_flavor="posix",
            ),
            filesystem=filesystem,
        )
    assert filesystem.calls == []

    with pytest.raises(GlobPatternError) as raw_limit:
        discover_artifacts(
            DiscoveryRequest(
                operands=("content",),
                recursive=True,
                profile="frontmatter-md",
                includes=("[" + "a" * GLOB_MAX_PATTERN_CODEPOINTS,),
                excludes=(),
                invocation_directory="/work",
                path_flavor="posix",
            ),
            filesystem=filesystem,
        )
    assert raw_limit.value.reason == "match_work_limit"
    assert filesystem.calls == []

    with pytest.raises(DiscoveryUsageError):
        discover_artifacts(
            DiscoveryRequest(
                operands=("content",),
                recursive=False,
                profile="frontmatter-md",
                includes=("*.md",),
                excludes=(),
                invocation_directory="/work",
                path_flavor="posix",
            ),
            filesystem=filesystem,
        )
    assert filesystem.calls == []

    with pytest.raises(GlobPatternError):
        discover_artifacts(
            DiscoveryRequest(
                operands=("content",),
                recursive=True,
                profile="frontmatter-md",
                includes=("bad**glob",),
                excludes=(),
                invocation_directory="/work",
                path_flavor="posix",
            ),
            filesystem=filesystem,
        )
    assert filesystem.calls == []

    with pytest.raises(GlobPatternError) as aggregate:
        discover_artifacts(
            DiscoveryRequest(
                operands=("content",),
                recursive=True,
                profile="frontmatter-md",
                includes=("*.md",) * (GLOB_MAX_PATTERNS + 1),
                excludes=(),
                invocation_directory="/work",
                path_flavor="posix",
            ),
            filesystem=filesystem,
        )
    assert aggregate.value.reason == "match_work_limit"
    assert filesystem.calls == []


def test_long_candidate_aggregate_glob_work_becomes_discovery_limit() -> None:
    name = "a" * 140_000 + ".md"
    filesystem = VectorFileSystem(
        {
            "nodes": [
                {
                    "path": "/work/root",
                    "kind": "directory",
                    "device": "1",
                    "inode": "1",
                    "entries": [name],
                },
                {
                    "path": f"/work/root/{name}",
                    "kind": "file",
                    "device": "1",
                    "inode": "2",
                },
            ],
            "failures": [],
        }
    )
    result = discover_artifacts(
        DiscoveryRequest(
            operands=("root",),
            recursive=True,
            profile="frontmatter-md",
            includes=("*z*",) * GLOB_MAX_PATTERNS,
            excludes=(),
            invocation_directory="/work",
            path_flavor="posix",
        ),
        filesystem=filesystem,
    )
    assert len(result.entries) == 1
    assert result.entries[0].kind == "input_error"
    assert result.entries[0].reason == "discovery_limit"


def test_native_filesystem_discovers_hidden_entries(tmp_path: Path) -> None:
    root = tmp_path / "content"
    root.mkdir()
    (root / ".hidden.md").write_text("hidden", encoding="utf-8")
    (root / "visible.markdown").write_text("visible", encoding="utf-8")
    (root / "ignored.yml").write_text("ignored", encoding="utf-8")

    result = discover_artifacts(
        DiscoveryRequest(
            operands=(str(root),),
            recursive=True,
            profile="frontmatter-md",
            includes=(),
            excludes=(),
            invocation_directory=str(tmp_path),
            path_flavor="windows" if os.name == "nt" else "posix",
        )
    )
    assert [entry.display_path for entry in result.entries if entry.kind == "artifact"] == [
        "content/.hidden.md",
        "content/visible.markdown",
    ]


def test_native_filesystem_deduplicates_hardlinks(tmp_path: Path) -> None:
    root = tmp_path / "content"
    root.mkdir()
    source = root / "source.md"
    source.write_text("source", encoding="utf-8")
    os.link(source, root / "alias.md")

    result = discover_artifacts(
        DiscoveryRequest(
            operands=(str(root),),
            recursive=True,
            profile="frontmatter-md",
            includes=(),
            excludes=(),
            invocation_directory=str(tmp_path),
            path_flavor="windows" if os.name == "nt" else "posix",
        )
    )
    assert [entry.display_path for entry in result.entries if entry.kind == "artifact"] == [
        "content/alias.md"
    ]


def test_native_not_a_directory_failure_is_not_found(tmp_path: Path) -> None:
    parent = tmp_path / "content.md"
    parent.write_text("content", encoding="utf-8")

    result = discover_artifacts(
        DiscoveryRequest(
            operands=(str(parent / "child.md"),),
            recursive=False,
            profile="frontmatter-md",
            includes=(),
            excludes=(),
            invocation_directory=str(tmp_path),
            path_flavor="windows" if os.name == "nt" else "posix",
        )
    )
    assert [asdict(entry) for entry in result.entries] == [
        {
            "reason": "not_found",
            "message": "artifact path does not exist",
            "source": "content.md/child.md",
            "kind": "input_error",
        }
    ]
