"""Build, inspect, install, and smoke-test the exact publishable artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPESCRIPT = ROOT / "packages" / "typescript"
METADATA_NAMES = ("release-metadata.json", "build-metadata.json")


class SmokeError(RuntimeError):
    """An artifact inventory, install, or runtime smoke failure."""


def _run(arguments: list[str], *, cwd: Path) -> str:
    process = subprocess.run(
        arguments,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        command = " ".join(arguments)
        raise SmokeError(
            f"command failed ({process.returncode}): {command}\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    return process.stdout


def _one(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise SmokeError(f"expected one {pattern} in {directory}, found {matches}")
    return matches[0]


def _build(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "uv",
            "build",
            "--build-constraint",
            "build-constraints.txt",
            "--require-hashes",
            "--python",
            sys.executable,
            "--clear",
            "--no-create-gitignore",
            "--out-dir",
            str(directory),
        ],
        cwd=ROOT,
    )
    _run(["bun", "run", "build"], cwd=TYPESCRIPT)
    _run(
        [
            "npm",
            "pack",
            "--ignore-scripts",
            "--pack-destination",
            str(directory),
        ],
        cwd=TYPESCRIPT,
    )


def _tar_member_bytes(archive: tarfile.TarFile, suffix: str) -> bytes:
    matches = [member for member in archive.getmembers() if member.name.endswith(suffix)]
    if len(matches) != 1:
        raise SmokeError(f"expected one archive member ending in {suffix!r}")
    extracted = archive.extractfile(matches[0])
    if extracted is None:
        raise SmokeError(f"archive metadata member is not a regular file: {matches[0].name}")
    return extracted.read()


def _one_name(names: list[str], suffix: str) -> str:
    matches = [name for name in names if name.endswith(suffix)]
    if len(matches) != 1:
        raise SmokeError(f"expected one archive path ending in {suffix!r}")
    return matches[0]


def _metadata_version(text: str) -> str:
    match = re.search(r"(?m)^Version: ([^\r\n]+)$", text)
    if match is None:
        raise SmokeError("package metadata has no Version field")
    return match.group(1)


def _assert_inventory_and_metadata(
    wheel: Path,
    sdist: Path,
    npm: Path,
) -> None:
    source = {name: (ROOT / name).read_bytes() for name in METADATA_NAMES}
    release = json.loads(source["release-metadata.json"])
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        wheel_roots = {name.split("/", 1)[0] for name in wheel_names}
        if not all(
            root == "softschema" or (root.startswith("softschema-") and root.endswith(".dist-info"))
            for root in wheel_roots
        ):
            raise SmokeError(f"wheel contains unexpected top-level paths: {sorted(wheel_roots)}")
        for name in METADATA_NAMES:
            actual = archive.read(f"softschema/resources/{name}")
            if actual != source[name]:
                raise SmokeError(f"wheel embeds different {name} bytes")
        metadata_name = _one_name(wheel_names, ".dist-info/METADATA")
        wheel_version = _metadata_version(archive.read(metadata_name).decode("utf-8"))

    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
        allowed_sdist_roots = {
            ".gitignore",
            "AGENTS.md",
            "LICENSE",
            "PKG-INFO",
            "README.md",
            "build-constraints.txt",
            "build-metadata.json",
            "build-requirements.in",
            "docs",
            "examples",
            "packages",
            "pyproject.toml",
            "release-metadata.json",
            "skills",
        }
        content_roots = {
            parts[1] for name in names if len(parts := name.split("/")) > 1 and parts[1]
        }
        unexpected = content_roots - allowed_sdist_roots
        if unexpected:
            raise SmokeError(f"sdist contains unexpected top-level paths: {sorted(unexpected)}")
        for name in METADATA_NAMES:
            if _tar_member_bytes(archive, f"/{name}") != source[name]:
                raise SmokeError(f"sdist embeds different {name} bytes")
        sdist_version = _metadata_version(_tar_member_bytes(archive, "/PKG-INFO").decode("utf-8"))

    with tarfile.open(npm, "r:gz") as archive:
        names = archive.getnames()
        allowed_roots = {
            "package/LICENSE",
            "package/README.md",
            "package/dist",
            "package/package.json",
            "package/resources",
        }
        for name in names:
            root = "/".join(name.split("/")[:2])
            if root not in allowed_roots:
                raise SmokeError(f"npm tarball contains unexpected path: {name}")
        for name in METADATA_NAMES:
            actual = _tar_member_bytes(archive, f"/resources/{name}")
            if actual != source[name]:
                raise SmokeError(f"npm tarball embeds different {name} bytes")
        npm_manifest = json.loads(_tar_member_bytes(archive, "/package.json"))

    if wheel_version != sdist_version:
        raise SmokeError("wheel and sdist versions differ")
    if npm_manifest.get("name") != release["packages"]["npm"]["name"]:
        raise SmokeError("npm tarball name differs from release metadata")
    if npm_manifest.get("version") != release["packages"]["npm"]["version"]:
        raise SmokeError("npm tarball version differs from release metadata")
    if release["release_state"] != "development":
        if wheel_version != release["packages"]["python"]["version"]:
            raise SmokeError("Python artifact version differs from release metadata")
        expected_names = set(release["expected_artifacts"])
        if not {wheel.name, sdist.name, npm.name}.issubset(expected_names):
            raise SmokeError("package filenames differ from expected release artifacts")


def _venv_python(directory: Path) -> Path:
    if os.name == "nt":
        return directory / "Scripts" / "python.exe"
    return directory / "bin" / "python"


def _smoke_python(wheel: Path, consumer: Path) -> None:
    environment = consumer / "python-env"
    _run(["uv", "venv", "--python", sys.executable, str(environment)], cwd=consumer)
    python = _venv_python(environment)
    _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--no-build",
            "--no-cache",
            "--exclude-newer",
            "2026-06-02T00:00:00Z",
            "--exclude-newer-package",
            "strif=2026-06-03T00:00:00Z",
            str(wheel),
        ],
        cwd=consumer,
    )
    _run(
        [
            str(python),
            str(ROOT / "devtools" / "verify_installed_wheel.py"),
            str(wheel),
        ],
        cwd=consumer,
    )
    import_location = _run(
        [str(python), "-c", "import softschema; print(softschema.__file__)"], cwd=consumer
    ).strip()
    if str(environment.resolve()) not in str(Path(import_location).resolve()):
        raise SmokeError("Python import resolved outside the isolated environment")
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    for executable_name in ("softschema", "softschema-py"):
        executable = scripts / executable_name
        if os.name == "nt":
            executable = executable.with_suffix(".exe")
        output = _run([str(executable), "docs", "--list", "--json"], cwd=consumer)
        topics = json.loads(output)
        if not isinstance(topics, dict) or not isinstance(topics.get("topics"), list):
            raise SmokeError(f"installed {executable_name} did not emit a JSON topic list")
    for topic, source_path in (
        ("example-artifact", "examples/movie_page/spirited-away.md"),
        ("guide", "docs/softschema-guide.md"),
        ("skill", "skills/softschema/SKILL.md"),
    ):
        output = _run([str(python), "-m", "softschema.cli", "docs", topic], cwd=consumer)
        if output.encode() != (ROOT / source_path).read_bytes():
            raise SmokeError(f"installed Python {topic} bytes differ from source")
    for name in METADATA_NAMES:
        code = (
            "from importlib.resources import files; "
            f"print(files('softschema').joinpath('resources/{name}').read_text(), end='')"
        )
        if _run([str(python), "-c", code], cwd=consumer).encode() != (ROOT / name).read_bytes():
            raise SmokeError(f"installed Python package has different {name} bytes")


def _smoke_npm(npm: Path, consumer: Path) -> None:
    npm_consumer = consumer / "npm-consumer"
    npm_consumer.mkdir()
    _run(
        [
            "npm",
            "install",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            "--before=2026-06-02T00:00:00Z",
            str(npm),
        ],
        cwd=npm_consumer,
    )
    cli = npm_consumer / "node_modules" / "softschema" / "dist" / "cli.js"
    bin_directory = npm_consumer / "node_modules" / ".bin"
    for executable_name in ("softschema", "softschema-ts"):
        executable = bin_directory / executable_name
        command = [str(executable)]
        if os.name == "nt":
            command = ["cmd.exe", "/d", "/s", "/c", str(executable.with_suffix(".cmd"))]
        output = _run([*command, "docs", "--list", "--json"], cwd=consumer)
        topics = json.loads(output)
        if not isinstance(topics, dict) or not isinstance(topics.get("topics"), list):
            raise SmokeError(f"installed npm {executable_name} did not emit a JSON topic list")
    _run(["node", "--input-type=module", "--eval", "await import('softschema')"], cwd=npm_consumer)
    resolved = _run(
        ["node", "--input-type=module", "--eval", "console.log(import.meta.resolve('softschema'))"],
        cwd=npm_consumer,
    ).strip()
    if "node_modules/softschema/" not in resolved.replace("\\", "/"):
        raise SmokeError("npm import resolved outside the isolated consumer")
    for topic, source_path in (
        ("example-artifact", "examples/movie_page/spirited-away.md"),
        ("guide", "docs/softschema-guide.md"),
        ("skill", "skills/softschema/SKILL.md"),
    ):
        output = _run(["node", str(cli), "docs", topic], cwd=consumer)
        if output.encode() != (ROOT / source_path).read_bytes():
            raise SmokeError(f"installed npm {topic} bytes differ from source")
    if shutil.which("bun") is not None:
        bun_output = _run(["bun", str(cli), "docs", "--list", "--json"], cwd=consumer)
        if not isinstance(json.loads(bun_output).get("topics"), list):
            raise SmokeError("installed npm CLI failed under Bun")
    for name in METADATA_NAMES:
        installed = npm_consumer / "node_modules" / "softschema" / "resources" / name
        if installed.read_bytes() != (ROOT / name).read_bytes():
            raise SmokeError(f"installed npm package has different {name} bytes")


def smoke(directory: Path) -> dict[str, str]:
    """Inspect and execute exactly one wheel, sdist, and npm tarball."""
    wheel = _one(directory, "*.whl")
    sdist = _one(directory, "softschema-*.tar.gz")
    npm = _one(directory, "*.tgz")
    _assert_inventory_and_metadata(wheel, sdist, npm)
    with tempfile.TemporaryDirectory(prefix="softschema-adversarial-") as temporary:
        consumer = Path(temporary) / "unrelated" / "deep" / "cwd"
        consumer.mkdir(parents=True)
        sentinel = "MALICIOUS CONSUMER SENTINEL\n"
        for relative in ("docs/softschema-guide.md", "skills/softschema/SKILL.md"):
            path = consumer / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(sentinel, encoding="utf-8")
        _smoke_python(wheel, consumer)
        _smoke_npm(npm, consumer)
    return {"npm": npm.name, "sdist": sdist.name, "wheel": wheel.name}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        help="Smoke an existing directory; without this flag, build into a temporary directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.artifacts is not None:
        result = smoke(args.artifacts.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="softschema-artifacts-") as temporary:
            directory = Path(temporary)
            _build(directory)
            result = smoke(directory)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
