"""Enforce the portable-core and compatibility-adapter dependency boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

from softschema import infer_envelope_key, validate_artifact, validate_contract_id
from softschema.core import (
    infer_envelope_key as core_infer_envelope_key,
)
from softschema.core import (
    validate_contract_id as core_validate_contract_id,
)
from softschema.runtime import validate_artifact as runtime_validate_artifact

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "softschema"
FORBIDDEN_CORE_IMPORTS = frozenset(
    {
        "argparse",
        "frontmatter_format",
        "importlib",
        "jsonschema",
        "os",
        "pathlib",
        "pydantic",
        "referencing",
        "ruamel",
        "socket",
        "strif",
        "subprocess",
        "sys",
        "tempfile",
        "yaml",
    }
)
FORBIDDEN_CORE_MODULES = frozenset({"urllib.request"})


def _local_module_path(module: str) -> Path | None:
    if module == "softschema":
        return PACKAGE_ROOT / "__init__.py"
    if not module.startswith("softschema."):
        return None
    relative = module.removeprefix("softschema.").replace(".", "/")
    package = PACKAGE_ROOT / relative / "__init__.py"
    if package.is_file():
        return package
    source = PACKAGE_ROOT / f"{relative}.py"
    return source if source.is_file() else None


def _containing_package(path: Path) -> list[str]:
    relative = path.relative_to(PACKAGE_ROOT)
    return list(relative.parent.parts)


def _runtime_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module is not None:
                imports.append(node.module)
            elif node.level > 0:
                package = _containing_package(path)
                keep = len(package) - (node.level - 1)
                prefix = ["softschema", *package[:keep]]
                if node.module is not None:
                    imports.append(".".join([*prefix, node.module]))
                else:
                    for alias in node.names:
                        candidate = ".".join([*prefix, alias.name])
                        if _local_module_path(candidate) is not None:
                            imports.append(candidate)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"__import__", "eval", "exec", "open"}
        ):
            raise AssertionError(f"dynamic import or evaluation in portable core: {path}")
    return imports


def test_portable_core_has_no_runtime_or_cli_dependency() -> None:
    pending = [PACKAGE_ROOT / "core" / "__init__.py"]
    visited: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        for module in _runtime_imports(path):
            root = module.split(".", 1)[0]
            assert root not in FORBIDDEN_CORE_IMPORTS, (
                f"portable core transitively imports adapter dependency {module!r} via {path}"
            )
            assert module not in FORBIDDEN_CORE_MODULES, (
                f"portable core transitively imports adapter dependency {module!r} via {path}"
            )
            local = _local_module_path(module)
            if local is not None:
                pending.append(local)

    assert visited > {PACKAGE_ROOT / "core" / "__init__.py"}


def test_package_root_keeps_core_object_identity() -> None:
    assert validate_contract_id is core_validate_contract_id
    assert infer_envelope_key is core_infer_envelope_key
    assert validate_artifact is runtime_validate_artifact
