"""Shared-contract and failure-boundary tests for ``skill --install``."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from softschema.cli import SKILL_DO_NOT_EDIT_MARKER
from softschema.skill_installer import (
    AGENT_TARGETS,
    BACKUP_SUFFIX,
    KNOWN_PRIOR_EMISSION_SHA256,
    LOCK_NAME,
    MAX_MANAGED_SKILL_BYTES,
    MAX_SKILL_LOCK_BYTES,
    STAGE_SUFFIX,
    InstallRequest,
    SkillInstallUsageError,
    _acquire_lock,
    _release_lock,
    execute_skill_install,
    format_install_plan_text,
    install_skill_payload,
    plan_skill_install,
    resolve_targets,
)
from tests.yaml_fixtures import load_yaml_fixture

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFORMANCE = REPO_ROOT / "conformance/skill-installer"
SOURCE_SKILL = REPO_ROOT / "skills/softschema/SKILL.md"
PRIOR_EMISSION = CONFORMANCE / "prior-emission-v0.1.1.md"
VERSION = "test-version"


def rendered_skill() -> str:
    return SOURCE_SKILL.read_text(encoding="utf-8")


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / ".git").mkdir()
    return path


def run_install(
    request: InstallRequest,
    *,
    cwd: Path,
    home: Path,
    env: dict[str, str] | None = None,
    fault: Callable[[str], None] | None = None,
) -> tuple[int, dict[str, Any]]:
    return execute_skill_install(
        request,
        rendered_skill=rendered_skill(),
        marker=SKILL_DO_NOT_EDIT_MARKER,
        package_version=VERSION,
        cwd=cwd,
        home=home,
        env=env or {},
        fault_injector=fault,
    )


def test_agent_targets_match_shared_target_table() -> None:
    fixture = load_yaml_fixture(CONFORMANCE / "agent-targets-v1.yaml")
    actual = [
        {
            "selector": target.selector,
            "project_root": target.project_root.as_posix(),
            "personal_root": target.personal_root.as_posix(),
            "home_override": target.home_override,
            "override_root": (
                target.override_root.as_posix() if target.override_root is not None else None
            ),
        }
        for target in AGENT_TARGETS
    ]
    assert fixture["version"] == "agent-targets-v1"
    assert fixture["implicit_project_agents"] == ["codex", "claude"]
    assert actual == fixture["agents"]


def test_known_prior_digest_allowlist_matches_shared_fixture() -> None:
    fixture = load_yaml_fixture(CONFORMANCE / "known-prior-emissions-v1.yaml")
    assert fixture["version"] == "known-prior-emissions-v1"
    assert {item["sha256"] for item in fixture["emissions"]} == set(KNOWN_PRIOR_EMISSION_SHA256)


def test_implicit_project_dry_run_matches_shared_golden(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    nested = repo / "src/deep"
    nested.mkdir(parents=True)

    code, report, _planned = plan_skill_install(
        InstallRequest(dry_run=True),
        rendered_skill=rendered_skill(),
        marker=SKILL_DO_NOT_EDIT_MARKER,
        package_version=VERSION,
        cwd=nested,
        home=tmp_path / "home",
        env={},
    )

    expected_text = (CONFORMANCE / "project-dry-run.golden.yaml").read_text()
    expected = YAML(typ="safe").load(
        expected_text.replace("<version>", VERSION).replace("<repo>", repo.as_posix())
    )
    normalized_report = json.loads(json.dumps(report))
    normalized_report["base_dir"] = Path(normalized_report["base_dir"]).as_posix()
    for file in normalized_report["files"]:
        file["base_dir"] = Path(file["base_dir"]).as_posix()
        file["path"] = Path(file["path"]).as_posix()
        file["resolved_path"] = Path(file["resolved_path"]).as_posix()
    assert code == 0
    assert normalized_report == expected
    assert not (repo / ".agents").exists()
    assert not (repo / ".claude").exists()
    assert not (repo / LOCK_NAME).exists()


def test_implicit_install_preserves_repo_root_behavior(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    nested = repo / "nested"
    nested.mkdir()

    code, report = run_install(InstallRequest(), cwd=nested, home=tmp_path / "home")

    assert code == 0
    assert report["base_dir"] == str(repo)
    assert [file["status"] for file in report["files"]] == ["created", "created"]  # type: ignore[index]
    assert (repo / ".agents/skills/softschema/SKILL.md").exists()
    assert (repo / ".claude/skills/softschema/SKILL.md").exists()

    second_code, second_report = run_install(InstallRequest(), cwd=nested, home=tmp_path / "home")
    assert second_code == 0
    assert all(file["status"] == "unchanged" for file in second_report["files"])  # type: ignore[union-attr]


def test_ambiguous_home_root_and_outside_repo_are_refused(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    with pytest.raises(SkillInstallUsageError, match="ambiguous outside a Git repository"):
        resolve_targets(InstallRequest(), cwd=tmp_path, home=home, env={})
    with pytest.raises(SkillInstallUsageError, match="user home"):
        resolve_targets(
            InstallRequest(project=True, no_repo_check=True, directory=home),
            cwd=tmp_path,
            home=home,
            env={},
        )
    with pytest.raises(SkillInstallUsageError, match="filesystem root"):
        resolve_targets(
            InstallRequest(
                project=True,
                no_repo_check=True,
                directory=Path(tmp_path.anchor),
            ),
            cwd=tmp_path,
            home=home,
            env={},
        )
    with pytest.raises(SkillInstallUsageError, match="not inside a Git repository"):
        resolve_targets(
            InstallRequest(project=True, directory=tmp_path / "plain"),
            cwd=tmp_path,
            home=home,
            env={},
        )


def test_explicit_project_outside_git_requires_confirmation_and_dry_run_is_pure(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "not-created"
    code, report = run_install(
        InstallRequest(
            project=True,
            directory=destination,
            no_repo_check=True,
            dry_run=True,
            agents=("cursor",),
        ),
        cwd=tmp_path,
        home=tmp_path / "home",
    )
    assert code == 0
    assert report["scope"] == "project"
    assert report["files"][0]["resolved_path"] == str(  # type: ignore[index]
        destination / ".cursor/skills/softschema/SKILL.md"
    )
    assert not destination.exists()


def test_worktree_and_submodule_git_files_are_roots(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: ../repo/.git/worktrees/w\n")
    submodule = worktree / "vendor/module"
    submodule.mkdir(parents=True)
    (submodule / ".git").write_text("gitdir: ../../.git/modules/module\n")

    _scope, worktree_base, _targets = resolve_targets(
        InstallRequest(), cwd=worktree / "vendor", home=tmp_path / "home", env={}
    )
    _scope, submodule_base, _targets = resolve_targets(
        InstallRequest(), cwd=submodule, home=tmp_path / "home", env={}
    )
    assert worktree_base == worktree
    assert submodule_base == submodule


def test_symlink_parent_must_not_escape_selected_base(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / ".cursor").symlink_to(outside, target_is_directory=True)

    with pytest.raises(SkillInstallUsageError, match="escapes its selected base"):
        resolve_targets(
            InstallRequest(agents=("cursor",)),
            cwd=repo,
            home=tmp_path / "home",
            env={},
        )


def test_global_agent_matrix_and_home_overrides(tmp_path: Path) -> None:
    home = tmp_path / "home"
    claude_home = tmp_path / "claude-config"
    gemini_home = tmp_path / "gemini-home"
    copilot_home = tmp_path / "copilot-home"
    env = {
        "CLAUDE_CONFIG_DIR": str(claude_home),
        "GEMINI_CLI_HOME": str(gemini_home),
        "COPILOT_HOME": str(copilot_home),
        "CODEX_HOME": str(tmp_path / "ignored-codex"),
        "OPENCODE_CONFIG": str(tmp_path / "ignored-opencode.json"),
        "CLINE_DATA_DIR": str(tmp_path / "ignored-cline"),
    }
    _scope, primary, targets = resolve_targets(
        InstallRequest(global_scope=True, all_agents=True, dry_run=True),
        cwd=tmp_path,
        home=home,
        env=env,
    )
    destinations = {target.agents[0]: target.target for target in targets}
    assert primary == home
    assert destinations == {
        "codex": home / ".agents/skills/softschema/SKILL.md",
        "claude": claude_home / "skills/softschema/SKILL.md",
        "gemini": gemini_home / ".gemini/skills/softschema/SKILL.md",
        "copilot": copilot_home / "skills/softschema/SKILL.md",
        "cursor": home / ".cursor/skills/softschema/SKILL.md",
        "windsurf": home / ".codeium/windsurf/skills/softschema/SKILL.md",
        "opencode": home / ".config/opencode/skills/softschema/SKILL.md",
        "cline": home / ".cline/skills/softschema/SKILL.md",
        "roo": home / ".roo/skills/softschema/SKILL.md",
    }


def test_converged_global_destinations_are_deduplicated_stably(tmp_path: Path) -> None:
    home = tmp_path / "home"
    env = {"CLAUDE_CONFIG_DIR": str(home / ".agents")}
    first = resolve_targets(
        InstallRequest(global_scope=True, agents=("claude", "codex")),
        cwd=tmp_path,
        home=home,
        env=env,
    )[2]
    second = resolve_targets(
        InstallRequest(global_scope=True, agents=("codex", "claude")),
        cwd=tmp_path,
        home=home,
        env=env,
    )[2]
    assert first == second
    assert len(first) == 1
    assert first[0].agents == ("claude", "codex")
    assert first[0].target == home / ".agents/skills/softschema/SKILL.md"


@pytest.mark.parametrize(
    ("install_request", "message"),
    [
        (InstallRequest(global_scope=True), "requires --agent"),
        (InstallRequest(project=True, global_scope=True), "mutually exclusive"),
        (InstallRequest(directory=Path("elsewhere")), "requires explicit --project"),
        (InstallRequest(project=True, agents=("aider",)), "unsupported agent target"),
        (InstallRequest(project=True, agents=("unknown",)), "unknown agent target"),
    ],
)
def test_invalid_selector_and_scope_combinations(
    tmp_path: Path, install_request: InstallRequest, message: str
) -> None:
    with pytest.raises(SkillInstallUsageError, match=message):
        resolve_targets(install_request, cwd=tmp_path, home=tmp_path / "home", env={})


def test_global_override_must_be_absolute_normalized_and_non_root(tmp_path: Path) -> None:
    request = InstallRequest(global_scope=True, agents=("claude",))
    with pytest.raises(SkillInstallUsageError, match="absolute normalized"):
        resolve_targets(
            request,
            cwd=tmp_path,
            home=tmp_path / "home",
            env={"CLAUDE_CONFIG_DIR": "relative"},
        )
    with pytest.raises(SkillInstallUsageError, match="filesystem root"):
        resolve_targets(
            request,
            cwd=tmp_path,
            home=tmp_path / "home",
            env={"CLAUDE_CONFIG_DIR": tmp_path.anchor},
        )


def test_preflight_aborts_all_targets_for_unmanaged_modified_and_newer_files(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "repo")
    codex = repo / ".agents/skills/softschema/SKILL.md"
    codex.parent.mkdir(parents=True)
    cases = {
        "unmanaged": "user-owned\n",
        "modified-or-unknown-managed": install_skill_payload(
            rendered_skill(), SKILL_DO_NOT_EDIT_MARKER
        )
        + "local edit\n",
        "newer-managed": install_skill_payload(rendered_skill(), SKILL_DO_NOT_EDIT_MARKER).replace(
            "format=f01", "format=f99"
        ),
    }
    for ownership, content in cases.items():
        codex.write_text(content)
        code, report = run_install(InstallRequest(dry_run=True), cwd=repo, home=tmp_path / "home")
        assert code == 1
        assert report["files"][0]["ownership"] == ownership  # type: ignore[index]
        assert report["files"][0]["action"] == "conflict"  # type: ignore[index]
        assert not (repo / ".claude").exists()


def test_known_prior_emission_is_updated_byte_exactly(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    prior = PRIOR_EMISSION.read_bytes()
    assert __import__("hashlib").sha256(prior).hexdigest() in KNOWN_PRIOR_EMISSION_SHA256
    target.write_bytes(prior)

    code, report = run_install(InstallRequest(agents=("codex",)), cwd=repo, home=tmp_path / "home")
    assert code == 0
    assert report["files"][0]["ownership"] == "managed-prior"  # type: ignore[index]
    assert report["files"][0]["status"] == "updated"  # type: ignore[index]
    assert target.read_text() == install_skill_payload(rendered_skill(), SKILL_DO_NOT_EDIT_MARKER)


def test_active_lock_is_a_non_mutating_conflict(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    lock = _acquire_lock(repo)
    try:
        code, report = run_install(
            InstallRequest(agents=("codex",), dry_run=True),
            cwd=repo,
            home=tmp_path / "home",
        )
        assert (repo / LOCK_NAME).exists()
    finally:
        _release_lock(lock)
    assert code == 1
    assert report["files"][0]["ownership"] == "lock-conflict"  # type: ignore[index]
    assert not (repo / ".agents").exists()


def test_unrecognized_lock_file_is_never_deleted(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    lock_path = repo / LOCK_NAME
    lock_path.write_text("user-owned\n")

    code, report = run_install(
        InstallRequest(agents=("codex",), dry_run=True),
        cwd=repo,
        home=tmp_path / "home",
    )
    assert code == 1
    assert report["files"][0]["ownership"] == "lock-conflict"  # type: ignore[index]
    assert lock_path.read_text() == "user-owned\n"


@pytest.mark.parametrize("dry_run", [True, False])
def test_oversized_sparse_lock_is_a_non_mutating_conflict(tmp_path: Path, dry_run: bool) -> None:
    repo = make_repo(tmp_path / "repo")
    lock_path = repo / LOCK_NAME
    with lock_path.open("wb") as stream:
        stream.truncate(MAX_SKILL_LOCK_BYTES + 1)

    code, report = run_install(
        InstallRequest(agents=("codex",), dry_run=dry_run),
        cwd=repo,
        home=tmp_path / "home",
    )

    assert code == 1
    assert report["files"][0]["ownership"] == "lock-conflict"  # type: ignore[index]
    assert lock_path.stat().st_size == MAX_SKILL_LOCK_BYTES + 1
    assert not (repo / ".agents").exists()


def test_concurrent_installer_observes_the_live_process_lock(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    script = f"""
import time
from pathlib import Path
from softschema.cli import SKILL_DO_NOT_EDIT_MARKER
from softschema.skill_installer import InstallRequest, execute_skill_install

ready = Path({str(ready)!r})
release = Path({str(release)!r})
def hold(boundary):
    if boundary.startswith('after-lock:'):
        ready.write_text('ready')
        while not release.exists():
            time.sleep(0.01)

code, _report = execute_skill_install(
    InstallRequest(agents=('codex',)),
    rendered_skill=Path({str(SOURCE_SKILL)!r}).read_text(),
    marker=SKILL_DO_NOT_EDIT_MARKER,
    package_version='test-version',
    cwd=Path({str(repo)!r}),
    home=Path({str(home)!r}),
    env={{}},
    fault_injector=hold,
)
raise SystemExit(code)
"""
    child = subprocess.Popen(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), child.stderr.read().decode() if child.stderr is not None else ""
        code, report = run_install(InstallRequest(agents=("codex",)), cwd=repo, home=home)
        assert code == 1
        assert report["files"][0]["ownership"] == "lock-conflict"  # type: ignore[index]
    finally:
        release.write_text("release")
        stdout, stderr = child.communicate(timeout=10)
    assert child.returncode == 0, (stdout.decode(), stderr.decode())


@pytest.mark.parametrize("blocker", ["target-directory", "parent-file"])
def test_path_blockers_are_exit_one_conflicts(tmp_path: Path, blocker: str) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    if blocker == "target-directory":
        target.mkdir(parents=True)
    else:
        (repo / ".agents").write_text("not a directory\n")

    code, report = run_install(
        InstallRequest(agents=("codex",), dry_run=True),
        cwd=repo,
        home=tmp_path / "home",
    )
    assert code == 1
    assert report["files"][0]["ownership"] == "path-conflict"  # type: ignore[index]


@pytest.mark.parametrize(
    ("suffix", "ownership"),
    [
        ("", "path-conflict"),
        (STAGE_SUFFIX, "residue-conflict"),
        (BACKUP_SUFFIX, "residue-conflict"),
    ],
)
@pytest.mark.parametrize("dry_run", [True, False])
def test_oversized_managed_skill_nodes_are_non_mutating_conflicts(
    tmp_path: Path,
    suffix: str,
    ownership: str,
    dry_run: bool,
) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    hostile = target.with_name(target.name + suffix)
    with hostile.open("wb") as stream:
        stream.truncate(MAX_MANAGED_SKILL_BYTES + 1)

    code, report = run_install(
        InstallRequest(agents=("codex",), dry_run=dry_run),
        cwd=repo,
        home=tmp_path / "home",
    )

    assert code == 1
    assert report["files"][0]["ownership"] == ownership  # type: ignore[index]
    assert report["files"][0]["action"] == "conflict"  # type: ignore[index]
    assert hostile.stat().st_size == MAX_MANAGED_SKILL_BYTES + 1
    assert not (repo / LOCK_NAME).exists()
    if suffix:
        assert not target.exists()


@pytest.mark.parametrize(
    ("suffix", "ownership"),
    [
        ("", "path-conflict"),
        (STAGE_SUFFIX, "residue-conflict"),
        (BACKUP_SUFFIX, "residue-conflict"),
    ],
)
def test_managed_skill_symlinks_are_non_mutating_dry_run_conflicts(
    tmp_path: Path, suffix: str, ownership: str
) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    outside = repo / "user-owned.md"
    outside.write_text("user-owned\n")
    hostile = target.with_name(target.name + suffix)
    try:
        hostile.symlink_to(outside)
    except OSError:
        pytest.skip("platform does not permit test symlinks")

    code, report = run_install(
        InstallRequest(agents=("codex",), dry_run=True),
        cwd=repo,
        home=tmp_path / "home",
    )

    assert code == 1
    assert report["files"][0]["ownership"] == ownership  # type: ignore[index]
    assert hostile.is_symlink()
    assert outside.read_text() == "user-owned\n"
    assert not (repo / LOCK_NAME).exists()


def test_managed_skill_replacement_between_inspection_and_open_is_a_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    original = PRIOR_EMISSION.read_bytes()
    target.write_bytes(original)
    replacement = tmp_path / "replacement.md"
    replacement.write_bytes(b"x" * len(original))
    displaced = tmp_path / "displaced.md"
    real_open = os.open
    replaced = False

    def replace_then_open(
        path: os.PathLike[str] | str,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replaced
        if Path(path) == target and not replaced:
            replaced = True
            target.replace(displaced)
            replacement.replace(target)
        if dir_fd is None:
            return real_open(path, flags, mode)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_then_open)
    code, report = run_install(
        InstallRequest(agents=("codex",), dry_run=True),
        cwd=repo,
        home=tmp_path / "home",
    )

    assert code == 1
    assert report["files"][0]["ownership"] == "path-conflict"  # type: ignore[index]
    assert target.read_bytes() == b"x" * len(original)
    assert displaced.read_bytes() == original
    assert not (repo / LOCK_NAME).exists()


def test_locks_are_acquired_in_sorted_base_order(tmp_path: Path) -> None:
    home = tmp_path / "z-home"
    claude = tmp_path / "a-claude"
    seen: list[str] = []

    def fault(boundary: str) -> None:
        if boundary.startswith("after-lock:"):
            seen.append(boundary.removeprefix("after-lock:"))

    code, _report = run_install(
        InstallRequest(global_scope=True, agents=("codex", "claude")),
        cwd=tmp_path,
        home=home,
        env={"CLAUDE_CONFIG_DIR": str(claude)},
        fault=fault,
    )
    assert code == 0
    assert seen == sorted([str(home), str(claude)])


def test_revalidation_catches_a_change_after_lock(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"

    def fault(boundary: str) -> None:
        if boundary.startswith("after-lock:"):
            target.parent.mkdir(parents=True)
            target.write_text("raced\n")

    code, report = run_install(
        InstallRequest(agents=("codex",)),
        cwd=repo,
        home=tmp_path / "home",
        fault=fault,
    )
    assert code == 1
    assert report["files"][0]["ownership"] == "unmanaged"  # type: ignore[index]
    assert report["files"][0]["action"] == "conflict"  # type: ignore[index]
    assert target.read_text() == "raced\n"


@pytest.mark.parametrize(
    ("boundary_prefix", "fail_on"),
    [
        ("after-stage:", 1),
        ("after-stage:", 2),
        ("after-replace:", 1),
        ("after-replace:", 2),
    ],
)
def test_recoverable_failure_rolls_back_all_targets_and_residue(
    tmp_path: Path, boundary_prefix: str, fail_on: int
) -> None:
    repo = make_repo(tmp_path / "repo")
    calls = 0

    def fault(boundary: str) -> None:
        nonlocal calls
        if boundary.startswith(boundary_prefix):
            calls += 1
            if calls == fail_on:
                raise OSError("injected failure")

    with pytest.raises(OSError, match="rolled back"):
        run_install(InstallRequest(), cwd=repo, home=tmp_path / "home", fault=fault)
    for relative in (
        ".agents/skills/softschema/SKILL.md",
        ".claude/skills/softschema/SKILL.md",
    ):
        target = repo / relative
        assert not target.exists()
        assert not target.with_name(target.name + STAGE_SUFFIX).exists()
        assert not target.with_name(target.name + BACKUP_SUFFIX).exists()
    assert not (repo / LOCK_NAME).exists()


@pytest.mark.parametrize(
    "boundary",
    [
        "after-lock:",
        "after-revalidate",
        "after-stage-all",
        "after-pre-replace-revalidate",
        "before-cleanup",
    ],
)
def test_transaction_control_boundary_failures_roll_back_cleanly(
    tmp_path: Path, boundary: str
) -> None:
    repo = make_repo(tmp_path / "repo")

    def fault(observed: str) -> None:
        if observed.startswith(boundary):
            raise OSError("injected control-boundary failure")

    with pytest.raises(OSError, match="rolled back"):
        run_install(InstallRequest(), cwd=repo, home=tmp_path / "home", fault=fault)
    assert not (repo / ".agents").exists()
    assert not (repo / ".claude").exists()
    assert not (repo / LOCK_NAME).exists()


def test_failure_after_backup_restores_the_prior_emission(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    prior = PRIOR_EMISSION.read_bytes()
    target.write_bytes(prior)

    def fault(boundary: str) -> None:
        if boundary.startswith("after-backup:"):
            raise OSError("injected backup-boundary failure")

    with pytest.raises(OSError, match="rolled back"):
        run_install(
            InstallRequest(agents=("codex",)),
            cwd=repo,
            home=tmp_path / "home",
            fault=fault,
        )
    assert target.read_bytes() == prior
    assert not target.with_name(target.name + STAGE_SUFFIX).exists()
    assert not target.with_name(target.name + BACKUP_SUFFIX).exists()
    assert not (repo / LOCK_NAME).exists()


def test_pre_replace_revalidation_preserves_a_raced_user_file(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"

    def fault(boundary: str) -> None:
        if boundary == "after-stage-all":
            target.write_text("raced after staging\n")

    code, report = run_install(
        InstallRequest(agents=("codex",)),
        cwd=repo,
        home=tmp_path / "home",
        fault=fault,
    )
    assert code == 1
    assert report["files"][0]["ownership"] == "unmanaged"  # type: ignore[index]
    assert target.read_text() == "raced after staging\n"
    assert not target.with_name(target.name + STAGE_SUFFIX).exists()
    assert not (repo / LOCK_NAME).exists()


def test_committed_cleanup_failure_leaves_repairable_not_rolled_back_state(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "repo")
    targets = [
        repo / ".agents/skills/softschema/SKILL.md",
        repo / ".claude/skills/softschema/SKILL.md",
    ]
    prior = PRIOR_EMISSION.read_bytes()
    for target in targets:
        target.parent.mkdir(parents=True)
        target.write_bytes(prior)
    calls = 0

    def fault(boundary: str) -> None:
        nonlocal calls
        if boundary.startswith("after-backup-cleanup:"):
            calls += 1
            if calls == 1:
                raise OSError("injected cleanup failure")

    with pytest.raises(OSError, match="committed but cleanup left recoverable residue"):
        run_install(InstallRequest(), cwd=repo, home=tmp_path / "home", fault=fault)
    desired = install_skill_payload(rendered_skill(), SKILL_DO_NOT_EDIT_MARKER)
    assert all(target.read_text() == desired for target in targets)
    assert sum(target.with_name(target.name + BACKUP_SUFFIX).exists() for target in targets) == 1

    code, _report = run_install(InstallRequest(), cwd=repo, home=tmp_path / "home")
    assert code == 0
    assert all(not target.with_name(target.name + BACKUP_SUFFIX).exists() for target in targets)


def test_process_kill_residue_is_repaired_idempotently(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(PRIOR_EMISSION.read_bytes())
    script = f"""
import os
from pathlib import Path
from softschema.cli import SKILL_DO_NOT_EDIT_MARKER
from softschema.skill_installer import InstallRequest, execute_skill_install

def crash(boundary):
    if boundary.startswith('after-backup:'):
        os._exit(73)

execute_skill_install(
    InstallRequest(agents=('codex',)),
    rendered_skill=Path({str(SOURCE_SKILL)!r}).read_text(),
    marker=SKILL_DO_NOT_EDIT_MARKER,
    package_version='test-version',
    cwd=Path({str(repo)!r}),
    home=Path({str(home)!r}),
    env={{}},
    fault_injector=crash,
)
"""
    killed = subprocess.run([sys.executable, "-c", script], check=False)
    assert killed.returncode == 73
    assert not target.exists()
    assert target.with_name(target.name + BACKUP_SUFFIX).exists()
    assert target.with_name(target.name + STAGE_SUFFIX).exists()
    assert (repo / LOCK_NAME).exists()

    code, _report = run_install(InstallRequest(agents=("codex",)), cwd=repo, home=home)
    assert code == 0
    assert target.read_text() == install_skill_payload(rendered_skill(), SKILL_DO_NOT_EDIT_MARKER)
    assert not target.with_name(target.name + BACKUP_SUFFIX).exists()
    assert not target.with_name(target.name + STAGE_SUFFIX).exists()
    assert not (repo / LOCK_NAME).exists()

    second_code, second_report = run_install(InstallRequest(agents=("codex",)), cwd=repo, home=home)
    assert second_code == 0
    assert second_report["files"][0]["status"] == "unchanged"  # type: ignore[index]


def test_dry_run_does_not_repair_existing_recoverable_residue(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    backup = target.with_name(target.name + BACKUP_SUFFIX)
    stage = target.with_name(target.name + STAGE_SUFFIX)
    backup.write_bytes(PRIOR_EMISSION.read_bytes())
    stage.write_text(install_skill_payload(rendered_skill(), SKILL_DO_NOT_EDIT_MARKER))

    code, _report = run_install(
        InstallRequest(agents=("codex",), dry_run=True),
        cwd=repo,
        home=tmp_path / "home",
    )
    assert code == 0
    assert not target.exists()
    assert backup.read_bytes() == PRIOR_EMISSION.read_bytes()
    assert stage.exists()
    assert not (repo / LOCK_NAME).exists()


def test_oversized_stage_raced_into_repair_is_a_non_mutating_conflict(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    target = repo / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    backup = target.with_name(target.name + BACKUP_SUFFIX)
    stage = target.with_name(target.name + STAGE_SUFFIX)
    prior = PRIOR_EMISSION.read_bytes()
    backup.write_bytes(prior)
    stage.write_text(install_skill_payload(rendered_skill(), SKILL_DO_NOT_EDIT_MARKER))

    def race(boundary: str) -> None:
        if boundary == "after-revalidate":
            with stage.open("wb") as stream:
                stream.truncate(MAX_MANAGED_SKILL_BYTES + 1)

    code, report = run_install(
        InstallRequest(agents=("codex",)),
        cwd=repo,
        home=tmp_path / "home",
        fault=race,
    )

    assert code == 1
    assert report["files"][0]["ownership"] == "residue-conflict"  # type: ignore[index]
    assert not target.exists()
    assert backup.read_bytes() == prior
    assert stage.stat().st_size == MAX_MANAGED_SKILL_BYTES + 1
    assert not (repo / LOCK_NAME).exists()


def test_text_plan_is_stable_and_surfaces_canonical_destination(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    code, report = run_install(
        InstallRequest(dry_run=True, agents=("cursor",)),
        cwd=repo,
        home=tmp_path / "home",
    )
    assert code == 0
    assert format_install_plan_text(report) == (
        "softschema skill install (project, agent-targets-v1)\n"
        f"base: {repo}\n"
        "dry-run: yes\n"
        f"create    absent                      cursor       "
        f"{repo / '.cursor/skills/softschema/SKILL.md'}"
    )
