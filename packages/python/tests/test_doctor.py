"""`doctor`: which runners the caller has, and the prefix it recommends.

Each scenario lays fake executables out under `tmp_path` and injects the search path
and the path softschema runs from, so no test depends on what is installed. The
TypeScript suite (`packages/typescript/test/doctor.test.ts`) runs the same scenarios and
expects the same reports.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

import softschema.cli as cli
from softschema import yaml_parser_mode
from softschema._portable import yaml_parser_reason
from softschema.cli import main as softschema_main

# The layouts `uvx` and `npx` really create: each prepends the throwaway environment's
# bin directory to the PATH of the softschema it starts.
UVX_ENV = Path(".cache/uv/archive-v0/V9O-H0OPJjiVa81e")
UVX_BIN = UVX_ENV / "bin"
UVX_MODULE = UVX_ENV / "lib/python3.14/site-packages/softschema/cli.py"
NPX_ENV = Path(".npm/_npx/be80e5187394a449/node_modules")
NPX_BIN = NPX_ENV / ".bin"
NPX_MODULE = NPX_ENV / "softschema/dist/cli.js"
INSTALLED_BIN = Path("usr/local/bin")
TOOLS_BIN = Path("opt/tools/bin")
SOURCE_MODULE = Path("src/softschema/cli.py")


def _executable(directory: Path, name: str) -> Path:
    """Create a file `name` in `directory` that PATH lookup accepts as an executable.

    On Windows `shutil.which` finds commands through `PATHEXT`, which spells `.EXE`.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (f"{name}.EXE" if sys.platform == "win32" else name)
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _search_path(root: Path, *dirs: Path) -> str:
    return os.pathsep.join(str(root / d) for d in dirs)


def _report(root: Path, running: Path, *dirs: Path) -> dict[str, object]:
    return cli._doctor_report(
        path_value=_search_path(root, *dirs), running_path=str(root / running)
    )


def _runners(**paths: Path | None) -> list[dict[str, object]]:
    return [
        {"name": name, "available": path is not None, "path": str(path) if path else None}
        for name, path in paths.items()
    ]


def test_installed_softschema_on_path_is_recommended(tmp_path: Path) -> None:
    softschema = _executable(tmp_path / INSTALLED_BIN, "softschema")
    uvx = _executable(tmp_path / TOOLS_BIN, "uvx")
    npx = _executable(tmp_path / TOOLS_BIN, "npx")

    report = _report(tmp_path, SOURCE_MODULE, INSTALLED_BIN, TOOLS_BIN)

    assert report["runners"] == _runners(softschema=softschema, uvx=uvx, npx=npx)
    assert report["recommended_invocation"] == "softschema"


def test_uvx_environment_recommends_uvx_not_its_own_softschema(tmp_path: Path) -> None:
    _executable(tmp_path / UVX_BIN, "softschema")
    uvx = _executable(tmp_path / TOOLS_BIN, "uvx")
    npx = _executable(tmp_path / TOOLS_BIN, "npx")

    report = _report(tmp_path, UVX_MODULE, UVX_BIN, TOOLS_BIN)

    assert report["runners"] == _runners(softschema=None, uvx=uvx, npx=npx)
    assert report["recommended_invocation"] == "uvx softschema@latest"


def test_npx_cache_recommends_npx_not_its_own_softschema(tmp_path: Path) -> None:
    _executable(tmp_path / NPX_BIN, "softschema")
    uvx = _executable(tmp_path / TOOLS_BIN, "uvx")
    npx = _executable(tmp_path / TOOLS_BIN, "npx")

    report = _report(tmp_path, NPX_MODULE, NPX_BIN, TOOLS_BIN)

    # The runner that started softschema wins over the skill's uvx-first fallback.
    assert report["runners"] == _runners(softschema=None, uvx=uvx, npx=npx)
    assert report["recommended_invocation"] == "npx -y softschema@latest"


def test_installed_softschema_wins_over_the_runner_that_started_it(tmp_path: Path) -> None:
    _executable(tmp_path / UVX_BIN, "softschema")
    softschema = _executable(tmp_path / INSTALLED_BIN, "softschema")
    uvx = _executable(tmp_path / TOOLS_BIN, "uvx")

    report = _report(tmp_path, UVX_MODULE, UVX_BIN, INSTALLED_BIN, TOOLS_BIN)

    assert report["runners"] == _runners(softschema=softschema, uvx=uvx, npx=None)
    assert report["recommended_invocation"] == "softschema"


def test_neither_installed_nor_ephemeral_falls_back_to_the_first_runner(tmp_path: Path) -> None:
    npx = _executable(tmp_path / TOOLS_BIN, "npx")

    report = _report(tmp_path, SOURCE_MODULE, TOOLS_BIN)

    assert report["runners"] == _runners(softschema=None, uvx=None, npx=npx)
    assert report["recommended_invocation"] == "npx -y softschema@latest"


@pytest.mark.parametrize(
    ("running", "expected"),
    [
        ("/root/.cache/uv/archive-v0/V9O-H0OPJjiVa81e/bin/softschema", "uvx softschema@latest"),
        ("/home/runner/_temp/setup-uv-cache/builds-v0/.tmpAbc/bin", "uvx softschema@latest"),
        ("/root/.cache/uv/environments-v2/0413/f9c7/bin/softschema", "uvx softschema@latest"),
        (r"C:\Users\me\AppData\Local\uv\cache\archive-v0\x\Scripts\softschema.exe", "uvx softschema@latest"),
        ("/root/.npm/_npx/be80e5187394a449/node_modules/softschema/dist/cli.js", "npx -y softschema@latest"),
        (r"C:\Users\me\AppData\Local\npm-cache\_npx\be80\node_modules\.bin\softschema.cmd", "npx -y softschema@latest"),
        ("/root/.local/share/uv/tools/softschema/bin/softschema", None),
        ("/home/me/archive-v0-notes/softschema/cli.py", None),
        ("/home/me/project/node_modules/softschema/dist/cli.js", None),
    ],
)  # fmt: skip
def test_ephemeral_runner_locations(running: str, expected: str | None) -> None:
    report = cli._doctor_report(path_value="", running_path=running)

    assert report["recommended_invocation"] == expected


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no execute bit")
def test_a_non_executable_or_directory_named_softschema_is_not_a_runner(tmp_path: Path) -> None:
    (tmp_path / "plain").mkdir()
    (tmp_path / "plain/softschema").write_text("", encoding="utf-8")
    (tmp_path / "dir/softschema").mkdir(parents=True)

    report = _report(tmp_path, SOURCE_MODULE, Path("plain"), Path("dir"))

    assert report["runners"] == _runners(softschema=None, uvx=None, npx=None)
    assert report["recommended_invocation"] is None


def test_doctor_json_reads_path_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    softschema = _executable(tmp_path / INSTALLED_BIN, "softschema")
    uvx = _executable(tmp_path / TOOLS_BIN, "uvx")
    monkeypatch.setenv("PATH", _search_path(tmp_path, INSTALLED_BIN, TOOLS_BIN))

    exit_code = softschema_main(["doctor", "--json"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "version": cli._installed_version(),
        "yaml_parser": yaml_parser_mode(),
        "yaml_parser_reason": yaml_parser_reason(),
        "runners": _runners(softschema=softschema, uvx=uvx, npx=None),
        "recommended_invocation": "softschema",
    }


def test_doctor_text_tells_user_how_to_recover_when_no_runner_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))

    exit_code = softschema_main(["doctor"])

    assert exit_code == 0
    assert capsys.readouterr().out == (
        f"softschema version: {cli._installed_version()}\n"
        f"yaml parser: {yaml_parser_mode()} ({yaml_parser_reason()})\n"
        "available runners:\n"
        "  softschema: no\n"
        "  uvx: no\n"
        "  npx: no\n"
        "recommended invocation: unavailable\n"
        "Install uv or Node, then retry.\n"
    )
