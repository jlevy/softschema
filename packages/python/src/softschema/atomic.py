"""Atomic text file writes.

A crash mid-write must never leave a half-written sidecar or document on disk,
so writers stage to a temp file in the same directory and ``os.replace`` it into
place (atomic on POSIX and Windows). Shared by the schema compiler and the
generated-section regenerator.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def write_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
