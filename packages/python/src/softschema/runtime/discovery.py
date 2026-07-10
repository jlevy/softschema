"""Deterministic filesystem discovery for batch artifact validation."""

from __future__ import annotations

import json
import ntpath
import os
import posixpath
import re
import stat as stat_module
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from typing import Literal, Protocol, TypeAlias

DiscoveryProfile: TypeAlias = Literal["frontmatter-md", "pure-yaml"]
DiscoveryPathFlavor: TypeAlias = Literal["posix", "windows"]
DiscoveryFileKind: TypeAlias = Literal["file", "directory", "symlink", "other"]
DiscoveryInputReason: TypeAlias = Literal[
    "not_found",
    "unreadable",
    "directory_requires_recursive",
    "no_matches",
    "discovery_limit",
]
GlobPatternReason: TypeAlias = Literal[
    "empty",
    "absolute",
    "drive_qualified",
    "backslash",
    "dot_segment",
    "unterminated_class",
    "partial_globstar",
]

_PROFILE_EXTENSIONS: dict[DiscoveryProfile, tuple[str, ...]] = {
    "frontmatter-md": (".md", ".markdown"),
    "pure-yaml": (".yaml", ".yml"),
}
_INPUT_MESSAGES: dict[DiscoveryInputReason, str] = {
    "not_found": "artifact path does not exist",
    "unreadable": "artifact path cannot be read",
    "directory_requires_recursive": "artifact directory requires --recursive",
    "no_matches": "artifact directory contains no matching files",
    "discovery_limit": "artifact discovery limit exceeded",
}
_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")

# Per-operand traversal limits bound untrusted directory trees identically in both runtimes.
DISCOVERY_MAX_DEPTH = 64
DISCOVERY_MAX_ENTRIES = 100_000


class GlobPatternError(ValueError):
    """A pattern falls outside the shared portable discovery-glob grammar."""

    reason: GlobPatternReason
    pattern: str

    def __init__(self, pattern: str, reason: GlobPatternReason) -> None:
        self.pattern = pattern
        self.reason = reason
        super().__init__(f"invalid glob {json.dumps(pattern, ensure_ascii=False)}: {reason}")


class DiscoveryUsageError(ValueError):
    """A discovery request combines options that cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class DiscoveryFileInfo:
    """Filesystem metadata required for kind checks and stable identity."""

    kind: DiscoveryFileKind
    device: int | None
    inode: int | None


class DiscoveryFileSystem(Protocol):
    """Injectable filesystem operations used by discovery."""

    def lstat(self, path: str) -> DiscoveryFileInfo: ...

    def stat(self, path: str) -> DiscoveryFileInfo: ...

    def read_directory(self, path: str, limit: int) -> Sequence[str]: ...

    def realpath(self, path: str) -> str: ...


def _file_info(result: os.stat_result) -> DiscoveryFileInfo:
    mode = result.st_mode
    if stat_module.S_ISREG(mode):
        kind: DiscoveryFileKind = "file"
    elif stat_module.S_ISDIR(mode):
        kind = "directory"
    elif stat_module.S_ISLNK(mode):
        kind = "symlink"
    else:
        kind = "other"
    return DiscoveryFileInfo(kind=kind, device=result.st_dev, inode=result.st_ino)


class NativeDiscoveryFileSystem:
    """Native synchronous filesystem adapter."""

    def lstat(self, path: str) -> DiscoveryFileInfo:
        return _file_info(os.lstat(path))

    def stat(self, path: str) -> DiscoveryFileInfo:
        return _file_info(os.stat(path))

    def read_directory(self, path: str, limit: int) -> tuple[str, ...]:
        if limit < 1:
            raise ValueError("directory read limit must be positive")
        names: list[str] = []
        with os.scandir(path) as entries:
            for entry in entries:
                names.append(entry.name)
                if len(names) == limit:
                    break
        return tuple(names)

    def realpath(self, path: str) -> str:
        return os.path.realpath(path, strict=True)


@dataclass(frozen=True, slots=True)
class _LiteralToken:
    value: str


@dataclass(frozen=True, slots=True)
class _AnyToken:
    pass


@dataclass(frozen=True, slots=True)
class _StarToken:
    pass


@dataclass(frozen=True, slots=True)
class _ClassToken:
    negated: bool
    ranges: tuple[tuple[int, int], ...]

    def matches(self, value: str) -> bool:
        code_point = ord(value)
        contained = any(start <= code_point <= end for start, end in self.ranges)
        return not contained if self.negated else contained


_SegmentToken: TypeAlias = _LiteralToken | _AnyToken | _StarToken | _ClassToken
_GlobSegment: TypeAlias = Literal["**"] | tuple[_SegmentToken, ...]


def _parse_class(pattern: str, segment: str, start: int) -> tuple[_ClassToken, int]:
    end = segment.find("]", start + 1)
    if end == -1:
        raise GlobPatternError(pattern, "unterminated_class")
    content = list(segment[start + 1 : end])
    negated = bool(content and content[0] == "!")
    if negated:
        content = content[1:]
    ranges: list[tuple[int, int]] = []
    index = 0
    while index < len(content):
        if index + 2 < len(content) and content[index + 1] == "-":
            first = ord(content[index])
            last = ord(content[index + 2])
            if first <= last:
                ranges.append((first, last))
            else:
                ranges.extend(((first, first), (ord("-"), ord("-")), (last, last)))
            index += 3
        else:
            value = ord(content[index])
            ranges.append((value, value))
            index += 1
    return _ClassToken(negated=negated, ranges=tuple(ranges)), end + 1


def _parse_segment(pattern: str, segment: str) -> _GlobSegment:
    if segment == "**":
        return "**"
    if "**" in segment:
        raise GlobPatternError(pattern, "partial_globstar")
    tokens: list[_SegmentToken] = []
    index = 0
    while index < len(segment):
        value = segment[index]
        if value == "*":
            tokens.append(_StarToken())
            index += 1
        elif value == "?":
            tokens.append(_AnyToken())
            index += 1
        elif value == "[":
            token, index = _parse_class(pattern, segment, index)
            tokens.append(token)
        else:
            tokens.append(_LiteralToken(value))
            index += 1
    return tuple(tokens)


def _validate_glob(pattern: str) -> None:
    if pattern == "":
        raise GlobPatternError(pattern, "empty")
    if pattern.startswith("/"):
        raise GlobPatternError(pattern, "absolute")
    if _DRIVE_PATTERN.match(pattern):
        raise GlobPatternError(pattern, "drive_qualified")
    if "\\" in pattern:
        raise GlobPatternError(pattern, "backslash")
    if any(segment in {".", ".."} for segment in pattern.split("/")):
        raise GlobPatternError(pattern, "dot_segment")


def _valid_candidate_path(path: str) -> bool:
    if path == "" or path.startswith("/") or "\\" in path or _DRIVE_PATTERN.match(path):
        return False
    segments = path.split("/")
    return all(segment not in {"", ".", ".."} for segment in segments)


def _match_segment(tokens: tuple[_SegmentToken, ...], value: str) -> bool:
    code_points = tuple(value)

    @cache
    def match(token_index: int, value_index: int) -> bool:
        if token_index == len(tokens):
            return value_index == len(code_points)
        token = tokens[token_index]
        if isinstance(token, _StarToken):
            return match(token_index + 1, value_index) or (
                value_index < len(code_points) and match(token_index, value_index + 1)
            )
        if value_index == len(code_points):
            return False
        if isinstance(token, _AnyToken):
            return match(token_index + 1, value_index + 1)
        if isinstance(token, _LiteralToken):
            return token.value == code_points[value_index] and match(
                token_index + 1, value_index + 1
            )
        return token.matches(code_points[value_index]) and match(token_index + 1, value_index + 1)

    return match(0, 0)


@dataclass(frozen=True, slots=True)
class CompiledGlob:
    """Compiled shared glob with complete-segment globstar semantics."""

    pattern: str
    _segments: tuple[_GlobSegment, ...] = field(repr=False)

    @classmethod
    def compile(cls, pattern: str) -> CompiledGlob:
        """Validate and compile one invocation pattern."""
        _validate_glob(pattern)
        return cls(
            pattern=pattern,
            _segments=tuple(_parse_segment(pattern, part) for part in pattern.split("/")),
        )

    def matches(self, path: str) -> bool:
        """Match one normalized operand-relative path case-sensitively."""
        if not _valid_candidate_path(path):
            return False
        path_segments = tuple(path.split("/"))

        @cache
        def match(pattern_index: int, path_index: int) -> bool:
            if pattern_index == len(self._segments):
                return path_index == len(path_segments)
            segment = self._segments[pattern_index]
            if segment == "**":
                return match(pattern_index + 1, path_index) or (
                    path_index < len(path_segments) and match(pattern_index, path_index + 1)
                )
            return (
                path_index < len(path_segments)
                and _match_segment(segment, path_segments[path_index])
                and match(pattern_index + 1, path_index + 1)
            )

        return match(0, 0)


@dataclass(frozen=True, slots=True)
class DiscoveryRequest:
    """Complete deterministic artifact-discovery request."""

    operands: tuple[str, ...]
    recursive: bool
    profile: DiscoveryProfile
    includes: tuple[str, ...]
    excludes: tuple[str, ...]
    invocation_directory: str
    path_flavor: DiscoveryPathFlavor


@dataclass(frozen=True, slots=True)
class DiscoveredArtifact:
    """One readable file spelling selected for later validation."""

    path: str
    display_path: str
    kind: Literal["artifact"] = field(default="artifact", init=False)


@dataclass(frozen=True, slots=True)
class DiscoveryInputError:
    """Stable input failure found while inspecting one operand group."""

    reason: DiscoveryInputReason
    message: str
    source: str
    kind: Literal["input_error"] = field(default="input_error", init=False)


DiscoveryEntry: TypeAlias = DiscoveredArtifact | DiscoveryInputError


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Ordered artifacts and input failures across all operand groups."""

    entries: tuple[DiscoveryEntry, ...]


@dataclass(frozen=True, slots=True)
class _Candidate:
    path: str
    display_path: str
    info: DiscoveryFileInfo


@dataclass(frozen=True, slots=True)
class _DirectoryWork:
    path: str
    info: DiscoveryFileInfo
    depth: int


_GroupEntry: TypeAlias = _Candidate | DiscoveryInputError
_Identity: TypeAlias = tuple[Literal["file_id"], int, int] | tuple[Literal["realpath"], str]


@dataclass(frozen=True, slots=True)
class _PathOperations:
    flavor: DiscoveryPathFlavor

    @property
    def module(self):
        return ntpath if self.flavor == "windows" else posixpath

    def absolute(self, path: str, cwd: str) -> str:
        module = self.module
        if self.flavor == "windows":
            drive, tail = ntpath.splitdrive(path)
            if drive and tail.startswith(("\\", "/")):
                return ntpath.normpath(path)
            if not drive and path.startswith(("\\", "/")):
                cwd_drive, _ = ntpath.splitdrive(cwd)
                return ntpath.normpath(ntpath.join(cwd_drive + "\\", path.lstrip("\\/")))
            if drive:
                cwd_drive, _ = ntpath.splitdrive(cwd)
                if drive.lower() == cwd_drive.lower():
                    return ntpath.normpath(ntpath.join(cwd, tail))
                # A request carries one invocation directory, not Windows' hidden
                # per-drive current directories. Resolve another drive from its root
                # so injected and native adapters stay deterministic.
                tail_without_root = tail.lstrip("\\/")
                return ntpath.normpath(f"{drive}\\{tail_without_root}")
        if module.isabs(path):
            return module.normpath(path)
        return module.normpath(module.join(cwd, path))

    def join(self, parent: str, child: str) -> str:
        return self.module.normpath(self.module.join(parent, child))

    def relative(self, path: str, start: str) -> str:
        return self.module.relpath(path, start)

    def normalize(self, path: str) -> str:
        return self.module.normpath(path)

    def display(self, path: str, cwd: str) -> str:
        try:
            relative = self.relative(path, cwd)
        except ValueError:
            relative = None
        separator = "\\" if self.flavor == "windows" else "/"
        if relative is not None and relative != ".." and not relative.startswith(f"..{separator}"):
            return relative.replace("\\", "/")
        return path.replace("\\", "/")


def _input_error(reason: DiscoveryInputReason, source: str) -> DiscoveryInputError:
    return DiscoveryInputError(reason=reason, message=_INPUT_MESSAGES[reason], source=source)


def _reason_from_exception(error: OSError) -> DiscoveryInputReason:
    return (
        "not_found" if isinstance(error, (FileNotFoundError, NotADirectoryError)) else "unreadable"
    )


def _code_point_key(value: str) -> tuple[int, ...]:
    return tuple(ord(character) for character in value)


def _group_sort_key(entry: _GroupEntry) -> tuple[tuple[int, ...], str, str]:
    display = entry.display_path if isinstance(entry, _Candidate) else entry.source
    kind = "artifact" if isinstance(entry, _Candidate) else entry.kind
    path = entry.path if isinstance(entry, _Candidate) else entry.source
    return _code_point_key(display), kind, path


def _eligible(
    relative_path: str,
    profile: DiscoveryProfile,
    includes: tuple[CompiledGlob, ...],
    excludes: tuple[CompiledGlob, ...],
) -> bool:
    if not relative_path.endswith(_PROFILE_EXTENSIONS[profile]):
        return False
    if includes and not any(pattern.matches(relative_path) for pattern in includes):
        return False
    return not any(pattern.matches(relative_path) for pattern in excludes)


def _discover_directory(
    root: str,
    root_info: DiscoveryFileInfo,
    request: DiscoveryRequest,
    operations: _PathOperations,
    filesystem: DiscoveryFileSystem,
    includes: tuple[CompiledGlob, ...],
    excludes: tuple[CompiledGlob, ...],
) -> tuple[list[_GroupEntry], bool]:
    entries: list[_GroupEntry] = []
    found_candidate_or_failure = False
    inspected_entries = 0
    budget_exceeded = False
    visited_directories: set[_Identity] = set()
    stack = [_DirectoryWork(path=root, info=root_info, depth=0)]

    while stack:
        work = stack.pop()
        display_directory = operations.display(work.path, request.invocation_directory)
        try:
            directory_identity = _identity(work.path, work.info, operations, filesystem)
        except OSError as error:
            found_candidate_or_failure = True
            entries.append(_input_error(_reason_from_exception(error), display_directory))
            continue
        if directory_identity in visited_directories:
            continue
        visited_directories.add(directory_identity)
        remaining_entries = DISCOVERY_MAX_ENTRIES - inspected_entries
        try:
            names = filesystem.read_directory(work.path, remaining_entries + 1)
        except OSError as error:
            found_candidate_or_failure = True
            entries.append(_input_error(_reason_from_exception(error), display_directory))
            continue
        if len(names) > remaining_entries:
            found_candidate_or_failure = True
            entries.append(_input_error("discovery_limit", display_directory))
            budget_exceeded = True
            stack.clear()
            continue
        names = sorted(names, key=_code_point_key)
        child_directories: list[_DirectoryWork] = []
        for name in names:
            child = operations.join(work.path, name)
            display = operations.display(child, request.invocation_directory)
            inspected_entries += 1
            relative = operations.relative(child, root).replace("\\", "/")
            try:
                info = filesystem.lstat(child)
            except OSError as error:
                found_candidate_or_failure = True
                entries.append(_input_error(_reason_from_exception(error), display))
                continue
            if info.kind == "symlink":
                continue
            if info.kind == "directory":
                child_depth = work.depth + 1
                if child_depth > DISCOVERY_MAX_DEPTH:
                    found_candidate_or_failure = True
                    entries.append(_input_error("discovery_limit", display))
                    budget_exceeded = True
                    break
                child_directories.append(_DirectoryWork(path=child, info=info, depth=child_depth))
                continue
            if not _eligible(relative, request.profile, includes, excludes):
                continue
            found_candidate_or_failure = True
            if info.kind == "file":
                entries.append(_Candidate(path=child, display_path=display, info=info))
            else:
                entries.append(_input_error("unreadable", display))
        if budget_exceeded:
            stack.clear()
        else:
            stack.extend(reversed(child_directories))
    if budget_exceeded:
        entries = [entry for entry in entries if isinstance(entry, DiscoveryInputError)]
    entries.sort(key=_group_sort_key)
    return entries, found_candidate_or_failure


def _identity(
    path: str,
    info: DiscoveryFileInfo,
    operations: _PathOperations,
    filesystem: DiscoveryFileSystem,
) -> _Identity:
    if info.device is not None and info.inode is not None and info.inode != 0:
        return "file_id", info.device, info.inode
    realpath = operations.normalize(filesystem.realpath(path))
    return "realpath", realpath


def _append_candidate(
    candidate: _Candidate,
    entries: list[DiscoveryEntry],
    identities: set[_Identity],
    operations: _PathOperations,
    filesystem: DiscoveryFileSystem,
) -> None:
    try:
        identity = _identity(candidate.path, candidate.info, operations, filesystem)
    except OSError as error:
        entries.append(_input_error(_reason_from_exception(error), candidate.display_path))
        return
    if identity in identities:
        return
    identities.add(identity)
    entries.append(DiscoveredArtifact(path=candidate.path, display_path=candidate.display_path))


def _validate_request(
    request: DiscoveryRequest,
) -> tuple[tuple[CompiledGlob, ...], tuple[CompiledGlob, ...]]:
    if not request.operands:
        raise DiscoveryUsageError("artifact discovery requires at least one operand")
    if request.profile not in _PROFILE_EXTENSIONS:
        raise DiscoveryUsageError(f"invalid discovery profile: {request.profile}")
    if request.path_flavor not in {"posix", "windows"}:
        raise DiscoveryUsageError(f"invalid path flavor: {request.path_flavor}")
    if not request.recursive and (request.includes or request.excludes):
        raise DiscoveryUsageError("include and exclude patterns require recursive discovery")
    includes = tuple(CompiledGlob.compile(pattern) for pattern in request.includes)
    excludes = tuple(CompiledGlob.compile(pattern) for pattern in request.excludes)
    return includes, excludes


def discover_artifacts(
    request: DiscoveryRequest,
    filesystem: DiscoveryFileSystem | None = None,
) -> DiscoveryResult:
    """Discover files and stable input errors without following directory symlinks.

    Inspection and later filesystem operations are separate. A directory can be
    replaced between ``lstat`` and ``read_directory``, and an artifact can be replaced
    after ``lstat`` but before the caller reads it. This adapter therefore does not
    claim race-free no-follow semantics; callers must still handle read-time failures.
    Per-operand identity tracking and resource limits bound recursive traversal.
    """
    includes, excludes = _validate_request(request)
    operations = _PathOperations(request.path_flavor)
    if not operations.module.isabs(request.invocation_directory):
        raise DiscoveryUsageError("invocation directory must be absolute")
    native_filesystem = filesystem if filesystem is not None else NativeDiscoveryFileSystem()
    cwd = operations.normalize(request.invocation_directory)
    normalized_request = DiscoveryRequest(
        operands=request.operands,
        recursive=request.recursive,
        profile=request.profile,
        includes=request.includes,
        excludes=request.excludes,
        invocation_directory=cwd,
        path_flavor=request.path_flavor,
    )
    entries: list[DiscoveryEntry] = []
    identities: set[_Identity] = set()

    for operand in request.operands:
        path = operations.absolute(operand, cwd)
        display = operations.display(path, cwd)
        try:
            info = native_filesystem.lstat(path)
        except OSError as error:
            entries.append(_input_error(_reason_from_exception(error), display))
            continue
        if info.kind == "symlink":
            try:
                target_info = native_filesystem.stat(path)
            except OSError as error:
                entries.append(_input_error(_reason_from_exception(error), display))
                continue
            if target_info.kind != "file":
                entries.append(_input_error("unreadable", display))
                continue
            _append_candidate(
                _Candidate(path=path, display_path=display, info=target_info),
                entries,
                identities,
                operations,
                native_filesystem,
            )
            continue
        if info.kind == "file":
            _append_candidate(
                _Candidate(path=path, display_path=display, info=info),
                entries,
                identities,
                operations,
                native_filesystem,
            )
            continue
        if info.kind != "directory":
            entries.append(_input_error("unreadable", display))
            continue
        if not request.recursive:
            entries.append(_input_error("directory_requires_recursive", display))
            continue

        group, found_candidate_or_failure = _discover_directory(
            path,
            info,
            normalized_request,
            operations,
            native_filesystem,
            includes,
            excludes,
        )
        if not found_candidate_or_failure:
            entries.append(_input_error("no_matches", display))
            continue
        for item in group:
            if isinstance(item, DiscoveryInputError):
                entries.append(item)
            else:
                _append_candidate(item, entries, identities, operations, native_filesystem)

    return DiscoveryResult(entries=tuple(entries))
