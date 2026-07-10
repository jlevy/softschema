"""Tests for the CI wheel-install attestation boundary."""

from __future__ import annotations

import base64
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

import devtools.verify_installed_wheel as verifier


def _record_digest(content: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=")
    return digest.decode()


def test_installed_bytes_are_verified_before_package_code_is_imported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "demo-1.0.0-py3-none-any.whl"
    metadata = b"Metadata-Version: 2.1\nName: demo\nVersion: 1.0.0\n\n"
    files = {
        "demo/__init__.py": b"VALUE = 'reviewed'\n",
        "demo-1.0.0.dist-info/METADATA": metadata,
    }
    record_name = "demo-1.0.0.dist-info/RECORD"
    record = "".join(
        f"{name},sha256={_record_digest(content)},{len(content)}\n"
        for name, content in files.items()
    )
    record += f"{record_name},,\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr(record_name, record)

    prefix = tmp_path / "environment"
    site_packages = prefix / "site-packages"
    for name, content in files.items():
        target = site_packages / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (site_packages / "demo" / "__init__.py").write_text(
        "raise RuntimeError('must not execute')\n", encoding="utf-8"
    )

    class FakeDistribution:
        version = "1.0.0"

        @staticmethod
        def read_text(name: str) -> str | None:
            if name == "direct_url.json":
                return json.dumps({"url": wheel.resolve().as_uri()})
            return None

        @staticmethod
        def locate_file(path: str) -> Path:
            return site_packages / path

    imported = False

    def unexpected_import(_name: str) -> Any:
        nonlocal imported
        imported = True
        raise AssertionError("tampered package code was imported before verification")

    monkeypatch.setattr(
        "devtools.verify_installed_wheel.metadata.distribution",
        lambda _name: FakeDistribution(),
    )
    monkeypatch.setattr("devtools.verify_installed_wheel.sys.prefix", str(prefix))
    monkeypatch.setattr(verifier, "import_module", unexpected_import)

    with pytest.raises(verifier.WheelVerificationError, match="installed bytes differ"):
        verifier.verify_installed_wheel(
            wheel,
            distribution_name="demo",
            module_name="demo",
        )
    assert imported is False
