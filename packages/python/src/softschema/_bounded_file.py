"""Bounded reads for untrusted artifact and schema files."""

from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from softschema.core.value_domain import PortableValueError

_LIMIT_SENTINEL_BYTES = 1
_READ_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class BoundedFileExpectation:
    """Canonical file authorization captured before a bounded read."""

    canonical_path: Path
    device: int
    inode: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def from_stat(
        cls,
        canonical_path: Path,
        value: os.stat_result,
    ) -> BoundedFileExpectation:
        """Bind a canonical path to the identity returned by ``stat``."""
        return cls(
            canonical_path,
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    def matches(self, value: os.stat_result) -> bool:
        """Return whether ``value`` is the file authorized by this binding."""
        return (
            self.inode != 0
            and value.st_ino != 0
            and (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )
            == (
                self.device,
                self.inode,
                self.size,
                self.modified_ns,
                self.changed_ns,
            )
        )


@dataclass(frozen=True)
class BoundedFileRead:
    """Bytes plus the canonical identity that supplied them."""

    data: bytes
    expectation: BoundedFileExpectation


def _file_flags() -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    return flags


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _stale_path_error(path: Path) -> OSError:
    return OSError(
        getattr(errno, "ESTALE", errno.EAGAIN),
        "bounded input changed before it could be opened",
        path,
    )


def resolve_file_path(path: Path, *, strict: bool = True) -> Path:
    """Resolve a path and normalize pre-3.13 symlink-loop failures to ``OSError``."""
    try:
        return path.resolve(strict=strict)
    except RuntimeError as exc:
        raise OSError(errno.ELOOP, "too many symbolic links", path) from exc


def _open_canonical_regular_file(
    requested_path: Path,
    source_path: Path,
    source_stat: os.stat_result,
) -> tuple[int, os.stat_result]:
    supports_openat = (
        os.name != "nt"
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )
    if supports_openat:
        parts = source_path.parts
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory_descriptor: int | None = None
        try:
            directory_descriptor = os.open(parts[0], directory_flags)
            for component in parts[1:-1]:
                child_descriptor = os.open(
                    component,
                    directory_flags,
                    dir_fd=directory_descriptor,
                )
                os.close(directory_descriptor)
                directory_descriptor = child_descriptor
            fresh_stat = os.stat(
                parts[-1],
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            if not stat.S_ISREG(fresh_stat.st_mode) or _identity(fresh_stat) != _identity(
                source_stat
            ):
                raise _stale_path_error(requested_path)
            descriptor = os.open(
                parts[-1],
                _file_flags(),
                dir_fd=directory_descriptor,
            )
            try:
                opened_stat = os.fstat(descriptor)
                if not stat.S_ISREG(opened_stat.st_mode) or _identity(opened_stat) != _identity(
                    fresh_stat
                ):
                    raise _stale_path_error(requested_path)
            except BaseException:
                os.close(descriptor)
                raise
            return descriptor, opened_stat
        finally:
            if directory_descriptor is not None:
                os.close(directory_descriptor)

    # Platforms without descriptor-relative traversal cannot pin each parent
    # component during open. Re-resolve around the descriptor open and compare the
    # final identity; callers carrying a prior authorization must also pass
    # ``expected`` to :func:`read_bounded_bytes`.
    if resolve_file_path(requested_path) != source_path:
        raise _stale_path_error(requested_path)
    descriptor = os.open(source_path, _file_flags())
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode) or _identity(opened_stat) != _identity(
            source_stat
        ):
            raise _stale_path_error(requested_path)
        if resolve_file_path(requested_path) != source_path:
            raise _stale_path_error(requested_path)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor, opened_stat


def read_bounded_file(
    path: Path,
    max_bytes: int,
    *,
    expected: BoundedFileExpectation | None = None,
) -> BoundedFileRead:
    """Read one identity-stable regular file without blocking on special nodes.

    ``expected`` carries an authorization decision made by a caller such as the
    metadata-schema resolver. The read must still resolve to that exact canonical
    path and device/inode pair, closing the gap between policy evaluation and open.
    """
    source_path = resolve_file_path(path)
    if expected is not None and source_path != expected.canonical_path:
        raise _stale_path_error(path)
    source_stat = source_path.lstat()
    if stat.S_ISDIR(source_stat.st_mode):
        raise IsADirectoryError(errno.EISDIR, "bounded input is a directory", path)
    if not stat.S_ISREG(source_stat.st_mode):
        raise OSError(errno.EINVAL, "bounded input must be a regular file", path)
    # A zero inode cannot carry the stable file identity this API promises. This is
    # intentionally fail-closed on filesystems that do not expose one; callers must
    # use a platform-specific stable-ID implementation rather than silently weakening
    # the authorization boundary.
    if source_stat.st_ino == 0:
        raise _stale_path_error(path)
    if source_stat.st_size > max_bytes:
        raise PortableValueError("maximum resource size exceeded")
    if expected is not None and not expected.matches(source_stat):
        raise _stale_path_error(path)
    # A persistent parent substitution between the first resolution and the identity
    # capture is rejected. A transient substitution yields an identity mismatch when
    # the descriptor is opened below.
    if resolve_file_path(path) != source_path:
        raise _stale_path_error(path)
    source_expectation = BoundedFileExpectation.from_stat(source_path, source_stat)
    descriptor, opened_stat = _open_canonical_regular_file(path, source_path, source_stat)
    try:
        # Windows can expose timestamps with different representations through path
        # and descriptor stat calls. Compare each interface only with itself: path
        # snapshots authorize the name, while descriptor snapshots stabilize bytes.
        if opened_stat.st_size != source_stat.st_size:
            raise _stale_path_error(path)
        fresh_source_stat = source_path.lstat()
        if not source_expectation.matches(fresh_source_stat):
            raise _stale_path_error(path)
        if resolve_file_path(path) != source_path:
            raise _stale_path_error(path)
        limit = max_bytes + _LIMIT_SENTINEL_BYTES
        capacity = max(1, min(limit, opened_stat.st_size + _LIMIT_SENTINEL_BYTES))
        buffer = bytearray(capacity)
        total = 0
        while total < capacity:
            chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, capacity - total))
            if not chunk:
                break
            buffer[total : total + len(chunk)] = chunk
            total += len(chunk)
        encoded = bytes(buffer[:total])
        final_stat = os.fstat(descriptor)
        # Windows exposes creation time through st_ctime_ns on the supported Python
        # versions, so an in-place write can restore mtime without changing any stat
        # field available here. Re-read the same descriptor and compare bytes to reject
        # torn ordinary races. This is still not an atomic snapshot against a hostile
        # writer deliberately coordinating both passes (documented below).
        if os.name == "nt" and total == opened_stat.st_size:
            os.lseek(descriptor, 0, os.SEEK_SET)
            verified = 0
            while verified < total:
                chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, total - verified))
                if not chunk or chunk != encoded[verified : verified + len(chunk)]:
                    raise _stale_path_error(path)
                verified += len(chunk)
            final_stat = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        _identity(final_stat) != _identity(opened_stat)
        or final_stat.st_size != opened_stat.st_size
        or final_stat.st_mtime_ns != opened_stat.st_mtime_ns
        or final_stat.st_ctime_ns != opened_stat.st_ctime_ns
        or total != opened_stat.st_size
    ):
        raise _stale_path_error(path)
    final_source_stat = source_path.lstat()
    if not source_expectation.matches(final_source_stat) or resolve_file_path(path) != source_path:
        raise _stale_path_error(path)
    if len(encoded) > max_bytes:
        raise PortableValueError("maximum resource size exceeded")
    return BoundedFileRead(
        data=encoded,
        expectation=source_expectation,
    )


def read_bounded_bytes(
    path: Path,
    max_bytes: int,
    *,
    expected: BoundedFileExpectation | None = None,
) -> bytes:
    """Read bytes through :func:`read_bounded_file`."""
    return read_bounded_file(path, max_bytes, expected=expected).data
