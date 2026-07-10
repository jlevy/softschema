"""Verify that the active Python environment contains one exact wheel's bytes."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from email.parser import BytesParser
from importlib import import_module, metadata
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

ROOT = Path(__file__).resolve().parents[1]


class WheelVerificationError(RuntimeError):
    """The installed distribution does not match the claimed wheel."""


def _normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _one(values: list[str], suffix: str) -> str:
    matches = [value for value in values if value.endswith(suffix)]
    if len(matches) != 1:
        raise WheelVerificationError(
            f"expected one wheel path ending in {suffix!r}, found {matches}"
        )
    return matches[0]


def _safe_wheel_path(value: str) -> PurePosixPath:
    components = value.split("/")
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or "\x00" in value
        or any(component in {"", ".", ".."} for component in components)
        or re.fullmatch(r"[A-Za-z]:", components[0]) is not None
        or path.is_absolute()
    ):
        raise WheelVerificationError(f"wheel RECORD contains unsafe path: {value!r}")
    return path


def _sha256_urlsafe(content: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()


def _file_url_path(value: str) -> Path:
    parsed = urlparse(value)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
        raise WheelVerificationError(f"direct_url.json does not name a local wheel: {value!r}")
    local = url2pathname(unquote(parsed.path))
    if os.name == "nt" and local.startswith("/") and len(local) > 2 and local[2] == ":":
        local = local[1:]
    return Path(local)


def verify_installed_wheel(
    wheel: Path,
    *,
    distribution_name: str = "softschema",
    module_name: str = "softschema",
) -> dict[str, str | int]:
    """Verify installed metadata, provenance, import location, and every wheel digest."""
    wheel = wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise WheelVerificationError(f"wheel does not exist: {wheel}")

    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise WheelVerificationError("wheel contains duplicate archive paths")
        record_name = _one(names, ".dist-info/RECORD")
        metadata_name = _one(names, ".dist-info/METADATA")
        message = BytesParser().parsebytes(archive.read(metadata_name))
        wheel_project = message.get("Name")
        wheel_version = message.get("Version")
        if not wheel_project or not wheel_version:
            raise WheelVerificationError("wheel METADATA is missing Name or Version")
        if _normalized_name(wheel_project) != _normalized_name(distribution_name):
            raise WheelVerificationError(
                f"wheel contains {wheel_project!r}, expected {distribution_name!r}"
            )
        rows = list(csv.reader(io.StringIO(archive.read(record_name).decode("utf-8"))))
        archive_files = {name for name in names if not name.endswith("/")}
        record_files = {row[0] for row in rows if len(row) == 3}
        if archive_files != record_files:
            raise WheelVerificationError("wheel file inventory differs from its RECORD")

        expected: list[tuple[PurePosixPath, str, int]] = []
        for row in rows:
            if len(row) != 3:
                raise WheelVerificationError(f"wheel RECORD row has {len(row)} columns")
            path_text, digest, size_text = row
            path = _safe_wheel_path(path_text)
            if path_text == record_name:
                if digest or size_text:
                    raise WheelVerificationError("wheel RECORD must not hash itself")
                continue
            if not digest.startswith("sha256=") or not size_text.isdecimal():
                raise WheelVerificationError(f"wheel RECORD lacks a SHA-256 digest: {path_text}")
            expected.append((path, digest.removeprefix("sha256="), int(size_text)))

    try:
        installed = metadata.distribution(distribution_name)
    except metadata.PackageNotFoundError as exc:
        raise WheelVerificationError(f"distribution is not installed: {distribution_name}") from exc
    installed_version = installed.version
    if installed_version != wheel_version:
        raise WheelVerificationError(
            f"installed version {installed_version!r} differs from wheel {wheel_version!r}"
        )

    direct_url_text = installed.read_text("direct_url.json")
    if direct_url_text is None:
        raise WheelVerificationError("installed distribution has no direct_url.json")
    try:
        direct_url = json.loads(direct_url_text)
        installed_from = _file_url_path(direct_url["url"]).resolve()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise WheelVerificationError("installed direct_url.json is invalid") from exc
    if installed_from != wheel:
        raise WheelVerificationError(
            f"installed from {installed_from}, expected the exact wheel {wheel}"
        )

    prefix = Path(sys.prefix).resolve()
    verified = 0
    for path, digest, size in expected:
        target = Path(str(installed.locate_file(str(path)))).resolve()
        if not target.is_relative_to(prefix) or not target.is_file():
            raise WheelVerificationError(f"installed wheel path is missing or unsafe: {path}")
        content = target.read_bytes()
        if len(content) != size or _sha256_urlsafe(content) != digest:
            raise WheelVerificationError(f"installed bytes differ from wheel RECORD: {path}")
        verified += 1

    source_root = (ROOT / "packages" / "python" / "src").resolve()
    imported = import_module(module_name)
    import_file = getattr(imported, "__file__", None)
    if not isinstance(import_file, str):
        raise WheelVerificationError(f"module has no concrete import path: {module_name}")
    import_path = Path(import_file).resolve()
    if not import_path.is_relative_to(prefix):
        raise WheelVerificationError(
            f"module imported outside the active environment: {import_path}"
        )
    if import_path.is_relative_to(source_root):
        raise WheelVerificationError(f"module imported from the source checkout: {import_path}")

    return {
        "distribution": distribution_name,
        "files_verified": verified,
        "import_path": str(import_path),
        "version": installed_version,
        "wheel": str(wheel),
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--distribution", default="softschema")
    parser.add_argument("--module", default="softschema")
    args = parser.parse_args(argv)
    try:
        report = verify_installed_wheel(
            args.wheel,
            distribution_name=args.distribution,
            module_name=args.module,
        )
    except (OSError, ValueError, zipfile.BadZipFile, WheelVerificationError) as exc:
        print(f"wheel verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
