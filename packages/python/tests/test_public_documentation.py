"""Executable contracts for public documentation and agent instruction surfaces."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[3]
FOOTER = (
    "<!-- This document follows common-doc-guidelines.md.\n"
    "See github.com/jlevy/practical-prose and review guidelines before editing.\n"
    "-->\n"
)
PUBLIC_MARKDOWN = (
    ROOT / "README.md",
    ROOT / "SECURITY.md",
    ROOT / "CHANGELOG.md",
    ROOT / "docs/api.md",
    ROOT / "docs/agent-compatibility.md",
    ROOT / "docs/development.md",
    ROOT / "docs/e2e-testing.runbook.md",
    ROOT / "docs/installation.md",
    ROOT / "docs/migration-0.3.md",
    ROOT / "docs/publishing.md",
    ROOT / "docs/softschema-guide.md",
    ROOT / "docs/softschema-python-design.md",
    ROOT / "docs/softschema-spec.md",
    ROOT / "docs/softschema-typescript-design.md",
    ROOT / "examples/movie_page/README.md",
    ROOT / "packages/python/README.md",
    ROOT / "packages/typescript/README.md",
    ROOT / "skills/softschema/SKILL.md",
    ROOT / "tests/golden/README.md",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def test_public_docs_have_one_exact_footer() -> None:
    for path in PUBLIC_MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert text.count(FOOTER) == 1, path
        assert text.endswith(FOOTER), path


def test_readme_is_a_short_first_visitor_page() -> None:
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    assert 100 <= len(lines) <= 180


@pytest.mark.parametrize("path", PUBLIC_MARKDOWN)
def test_public_doc_local_links_resolve(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    missing: list[str] = []
    for raw_target in LINK_RE.findall(text):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if target.startswith(("#", "http://", "https://", "mailto:", "?:")):
            continue
        relative = unquote(target.split("#", 1)[0])
        if relative and not (path.parent / relative).resolve().exists():
            missing.append(target)
    assert missing == [], f"{path}: unresolved links {missing}"


def test_registry_readmes_use_absolute_public_links() -> None:
    for path in (ROOT / "packages/python/README.md", ROOT / "packages/typescript/README.md"):
        text = path.read_text(encoding="utf-8")
        targets = [
            target.strip().split(maxsplit=1)[0].strip("<>") for target in LINK_RE.findall(text)
        ]
        assert targets, path
        assert all(target.startswith(("https://", "#")) for target in targets), (path, targets)


def test_generated_agent_instruction_shims_are_current() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "devtools/sync_agent_instructions.py"), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_generated_copilot_instruction_links_resolve_from_github_directory() -> None:
    path = ROOT / ".github/copilot-instructions.md"
    text = path.read_text(encoding="utf-8")
    missing: list[str] = []
    for raw_target in LINK_RE.findall(text):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if target.startswith(("#", "http://", "https://", "mailto:", "?:")):
            continue
        relative = unquote(target.split("#", 1)[0])
        if relative and not (path.parent / relative).resolve().exists():
            missing.append(target)
    assert missing == [], f"{path}: unresolved links {missing}"


def test_public_claim_markers_match_authoritative_metadata() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "devtools/public_claims.py"), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_agent_compatibility_is_evidence_calibrated_and_complete() -> None:
    text = (ROOT / "docs/agent-compatibility.md").read_text(encoding="utf-8")
    for product in (
        "Codex",
        "Claude Code",
        "Gemini CLI",
        "GitHub Copilot",
        "Cursor",
        "Windsurf",
        "OpenCode",
        "Aider",
        "Cline",
        "Roo Code",
    ):
        assert product in text
    for evidence_label in ("Documented", "Observed", "Not observed"):
        assert evidence_label in text


def test_movie_example_has_paired_python_and_typescript_sources() -> None:
    for relative in (
        "model.py",
        "model.ts",
        "host_integration.py",
        "host_integration.ts",
    ):
        assert (ROOT / "examples/movie_page" / relative).is_file()


def test_public_docs_do_not_reintroduce_known_stale_examples() -> None:
    for path in PUBLIC_MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert "softschema==0.2.0" not in text, path
        assert "softschema@0.2.0" not in text, path
        assert "softschema validate “" not in text, path


def test_typescript_api_examples_use_public_option_shapes() -> None:
    text = (ROOT / "docs/api.md").read_text(encoding="utf-8")
    assert 'resources: {\n    "https://example.com/schemas/address/v1": addressSchema,' in text
    assert "validationLimits: { maxResourceBytes: 16 * 1024 * 1024 }" in text
    assert "resources: new Map(" not in text
    assert "maxInputBytes" not in text


def test_spec_records_portable_unicode_and_frontmatter_fence_rules() -> None:
    text = (ROOT / "docs/softschema-spec.md").read_text(encoding="utf-8")
    prose = " ".join(text.split())
    assert "Literal U+0085 (NEXT LINE), U+2028 (LINE SEPARATOR), and U+2029" in prose
    assert "escaped forms in double-quoted YAML" in prose
    assert "frontmatter fence scanner recognizes only LF, CR, and CRLF line breaks" in prose
    assert "optional ASCII space or tab" in prose
    assert "U+0085, U+2028, and U+2029 cannot create or terminate a fence" in prose


def test_compiler_owned_root_annotation_is_documented_at_public_boundaries() -> None:
    spec = " ".join((ROOT / "docs/softschema-spec.md").read_text(encoding="utf-8").split())
    api = " ".join((ROOT / "docs/api.md").read_text(encoding="utf-8").split())
    migration = " ".join((ROOT / "docs/migration-0.3.md").read_text(encoding="utf-8").split())
    assert "Root `x-softschema` is reserved compiler output" in spec
    assert "The root `x-softschema` block is compiler-owned" in api
    assert "Remove any model-supplied root `x-softschema` block" in migration
