"""Safe, cross-agent installation for the bundled softschema skill.

The installer deliberately separates read-only planning from mutation.  Both the
Python and TypeScript implementations implement the same ``agent-targets-v1``
contract and emit the same plan fields.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

TARGET_TABLE_VERSION = "agent-targets-v1"
MANAGED_FORMAT = "f01"
LOCK_NAME = ".softschema-skill-install.lock"
STAGE_SUFFIX = ".softschema-stage"
BACKUP_SUFFIX = ".softschema-backup"

# These are byte-exact reviewed release or release-candidate installer emissions. A
# stamped file is not enough: only an allowlisted digest (or the current desired bytes)
# may be replaced. Additive history is intentional so upgrades do not become clobbers.
KNOWN_PRIOR_EMISSION_SHA256: frozenset[str] = frozenset(
    {
        "554bf881da03dbf3c36a2c7444d7ef469d38783ba2c27c7b2e035e4b233339c0",
        "a0ab855baa1a65a32f09636536991f55a72115c6f9aa6ab51de6db2ee1c6eba6",
        "5123905a93350417abbb702d74fd9b5d92684199560c27694426326e8e8e1f43",
        "ff9ffe0e8aa3f79951a475cf6f4378e17783041fab47687615d037c93c4ee98c",
        "63fb27814dfad5ad8ea090c1879bb13d861915bd7084a5774b543ba16bd06fc5",
        "58dce894b18dabdbd6cf44b38c6db0413f848a44a3d44a6e7b794e95bd3c298a",
    }
)

MANAGED_MARKER_RE = re.compile(
    rb"<!-- DO NOT EDIT format=f(?P<format>[0-9]+): written by "
    rb"`softschema skill --install`\.\n"
)


@dataclass(frozen=True)
class AgentTarget:
    selector: str
    project_root: Path
    personal_root: Path
    home_override: str | None = None
    override_root: Path | None = None


AGENT_TARGETS: tuple[AgentTarget, ...] = (
    AgentTarget("codex", Path(".agents/skills"), Path(".agents/skills")),
    AgentTarget(
        "claude",
        Path(".claude/skills"),
        Path(".claude/skills"),
        "CLAUDE_CONFIG_DIR",
        Path("skills"),
    ),
    AgentTarget(
        "gemini",
        Path(".gemini/skills"),
        Path(".gemini/skills"),
        "GEMINI_CLI_HOME",
        Path(".gemini/skills"),
    ),
    AgentTarget(
        "copilot",
        Path(".github/skills"),
        Path(".copilot/skills"),
        "COPILOT_HOME",
        Path("skills"),
    ),
    AgentTarget("cursor", Path(".cursor/skills"), Path(".cursor/skills")),
    AgentTarget("windsurf", Path(".windsurf/skills"), Path(".codeium/windsurf/skills")),
    AgentTarget("opencode", Path(".opencode/skills"), Path(".config/opencode/skills")),
    AgentTarget("cline", Path(".cline/skills"), Path(".cline/skills")),
    AgentTarget("roo", Path(".roo/skills"), Path(".roo/skills")),
)
AGENT_TARGETS_BY_NAME: Mapping[str, AgentTarget] = {
    target.selector: target for target in AGENT_TARGETS
}
IMPLICIT_PROJECT_AGENTS: tuple[str, ...] = ("codex", "claude")


class SkillInstallUsageError(ValueError):
    """An invalid or unsafe installer invocation (exit 2 at the CLI boundary)."""


class SkillInstallExecutionError(OSError):
    """A recoverable install operation failed after rollback."""


@dataclass(frozen=True)
class InstallRequest:
    project: bool = False
    global_scope: bool = False
    directory: Path | None = None
    agents: tuple[str, ...] = ()
    all_agents: bool = False
    no_repo_check: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class ResolvedTarget:
    agents: tuple[str, ...]
    base_dir: Path
    relative_path: Path
    target: Path


@dataclass(frozen=True)
class Inspection:
    ownership: str
    managed_format: str | None
    prior_digest: str | None
    action: Literal["create", "update", "unchanged", "conflict"]
    status: Literal["created", "updated", "unchanged", "conflict"]
    fingerprint: tuple[str, str | None]
    effective_content: bytes | None
    residue: Literal["none", "discard-stage", "restore-backup", "discard-backup"]


@dataclass(frozen=True)
class PlannedTarget:
    resolved: ResolvedTarget
    inspection: Inspection


@dataclass(frozen=True)
class _HeldLock:
    path: Path
    inode: int


FaultInjector = Callable[[str], None]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _utf8_sort_key(value: str | Path) -> bytes:
    return str(value).encode("utf-8", errors="surrogatepass")


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def _actual_home(home: Path | None) -> Path:
    candidate = Path.home() if home is None else home
    return candidate.expanduser().resolve(strict=False)


def _find_git_root(start: Path) -> Path | None:
    """Return the nearest worktree/submodule root; ``.git`` may be a file or dir."""
    canonical = start.resolve(strict=False)
    probe = canonical if canonical.is_dir() else canonical.parent
    for candidate in (probe, *probe.parents):
        if (candidate / ".git").exists():
            return candidate.resolve(strict=False)
    return None


def _require_safe_base(base: Path, *, home: Path, scope: str) -> Path:
    canonical = base.resolve(strict=False)
    if canonical.parent == canonical:
        raise SkillInstallUsageError(f"{scope} install base must not be the filesystem root")
    if scope == "project" and canonical == home:
        raise SkillInstallUsageError("project install base must not be the user home directory")
    return canonical


def _selector_names(request: InstallRequest, scope: str) -> tuple[str, ...]:
    if request.agents and request.all_agents:
        raise SkillInstallUsageError("--agent and --all-agents are mutually exclusive")
    if scope == "global" and not request.agents and not request.all_agents:
        raise SkillInstallUsageError("--global requires --agent NAME or --all-agents")
    raw = (
        tuple(target.selector for target in AGENT_TARGETS) if request.all_agents else request.agents
    )
    if not raw:
        raw = IMPLICIT_PROJECT_AGENTS
    names: list[str] = []
    for name in raw:
        normalized = name.strip().lower()
        if normalized == "aider":
            raise SkillInstallUsageError(
                "unsupported agent target 'aider': aider has no documented native Agent "
                "Skills target; use its read: compatibility recipe"
            )
        if normalized not in AGENT_TARGETS_BY_NAME:
            choices = ", ".join(target.selector for target in AGENT_TARGETS)
            raise SkillInstallUsageError(
                f"unknown agent target {name!r}; supported targets: {choices}"
            )
        if normalized not in names:
            names.append(normalized)
    selected = set(names)
    return tuple(target.selector for target in AGENT_TARGETS if target.selector in selected)


def resolve_targets(
    request: InstallRequest,
    *,
    cwd: Path,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[str, Path, tuple[ResolvedTarget, ...]]:
    """Resolve scope and destinations without mutating the filesystem."""
    if request.project and request.global_scope:
        raise SkillInstallUsageError("--project and --global are mutually exclusive")
    if request.directory is not None and not request.project:
        raise SkillInstallUsageError("--dir requires explicit --project")
    if request.global_scope and request.directory is not None:
        raise SkillInstallUsageError("--global and --dir are mutually exclusive")
    if request.no_repo_check and not request.project:
        raise SkillInstallUsageError("--no-repo-check requires explicit --project")

    process_home = _actual_home(home)
    environment = os.environ if env is None else env
    scope = "global" if request.global_scope else "project"
    selectors = _selector_names(request, scope)

    targets: list[ResolvedTarget] = []
    if scope == "project":
        requested = (request.directory or cwd).expanduser().resolve(strict=False)
        git_root = _find_git_root(requested)
        if git_root is None and not request.no_repo_check:
            if not request.project:
                raise SkillInstallUsageError(
                    "skill install scope is ambiguous outside a Git repository; pass "
                    "--project --no-repo-check --dir PATH or --global with agent selectors"
                )
            raise SkillInstallUsageError(
                "project install target is not inside a Git repository; pass "
                "--no-repo-check to confirm this destination"
            )
        base = _require_safe_base(git_root or requested, home=process_home, scope=scope)
        for selector in selectors:
            definition = AGENT_TARGETS_BY_NAME[selector]
            relative = definition.project_root / "softschema" / "SKILL.md"
            targets.append(ResolvedTarget((selector,), base, relative, base / relative))
        primary_base = base
    else:
        primary_base = _require_safe_base(process_home, home=process_home, scope=scope)
        for selector in selectors:
            definition = AGENT_TARGETS_BY_NAME[selector]
            override_value = (
                environment.get(definition.home_override)
                if definition.home_override is not None
                else None
            )
            if override_value:
                override = Path(override_value)
                if not override.is_absolute():
                    raise SkillInstallUsageError(
                        f"{definition.home_override} must be an absolute normalized path"
                    )
                if os.path.normpath(override_value) != override_value:
                    raise SkillInstallUsageError(
                        f"{definition.home_override} must be an absolute normalized path"
                    )
                base = _require_safe_base(
                    override.resolve(strict=False), home=process_home, scope=scope
                )
                root = definition.override_root
                if root is None:
                    raise AssertionError("agent target override is missing its root")
            else:
                base = primary_base
                root = definition.personal_root
            relative = root / "softschema" / "SKILL.md"
            targets.append(ResolvedTarget((selector,), base, relative, base / relative))

    # Resolve destination aliases before writing and emit each canonical destination once.
    deduplicated: dict[Path, ResolvedTarget] = {}
    for target in targets:
        canonical_target = target.target.resolve(strict=False)
        if not _is_relative_to(canonical_target, target.base_dir):
            raise SkillInstallUsageError(
                f"target path escapes its selected base through a symlink: {target.target}"
            )
        existing = deduplicated.get(canonical_target)
        if existing is None:
            deduplicated[canonical_target] = target
        else:
            deduplicated[canonical_target] = replace(
                existing, agents=tuple(sorted({*existing.agents, *target.agents}))
            )
    ordered = tuple(
        sorted(
            deduplicated.values(),
            key=lambda item: (
                _utf8_sort_key(item.base_dir),
                _utf8_sort_key(item.relative_path),
            ),
        )
    )
    return scope, primary_base, ordered


def _path_conflict(ownership: str, detail: str) -> Inspection:
    return Inspection(
        ownership,
        None,
        None,
        "conflict",
        "conflict",
        ("path", detail),
        None,
        "none",
    )


def _managed_format(content: bytes) -> int | None:
    match = MANAGED_MARKER_RE.search(content)
    return int(match.group("format")) if match is not None else None


def _classify_content(content: bytes | None, desired: bytes) -> Inspection:
    if content is None:
        return Inspection("absent", None, None, "create", "created", ("absent", None), None, "none")

    digest = sha256_bytes(content)
    digest_field = f"sha256:{digest}"
    managed = _managed_format(content)
    if content == desired:
        return Inspection(
            "managed",
            MANAGED_FORMAT,
            digest_field,
            "unchanged",
            "unchanged",
            ("file", digest),
            content,
            "none",
        )
    if digest in KNOWN_PRIOR_EMISSION_SHA256:
        return Inspection(
            "managed-prior",
            f"f{managed:02d}" if managed is not None else None,
            digest_field,
            "update",
            "updated",
            ("file", digest),
            content,
            "none",
        )
    if managed is None:
        ownership = "unmanaged"
    elif managed > int(MANAGED_FORMAT[1:]):
        ownership = "newer-managed"
    elif managed != int(MANAGED_FORMAT[1:]):
        ownership = "unknown-managed"
    else:
        ownership = "modified-or-unknown-managed"
    return Inspection(
        ownership,
        f"f{managed:02d}" if managed is not None else None,
        digest_field,
        "conflict",
        "conflict",
        ("file", digest),
        content,
        "none",
    )


def _inspect_target(target: ResolvedTarget, desired: bytes) -> Inspection:
    stage = target.target.with_name(target.target.name + STAGE_SUFFIX)
    backup = target.target.with_name(target.target.name + BACKUP_SUFFIX)
    probe = target.target.parent
    while probe != target.base_dir:
        if (probe.exists() or probe.is_symlink()) and not probe.is_dir():
            return _path_conflict("path-conflict", str(probe))
        probe = probe.parent
    for residue_path in (stage, backup):
        if (residue_path.exists() or residue_path.is_symlink()) and not residue_path.is_file():
            return _path_conflict("residue-conflict", str(residue_path))
    if (target.target.exists() or target.target.is_symlink()) and not target.target.is_file():
        return _path_conflict("path-conflict", str(target.target))
    try:
        target_content = (
            target.target.read_bytes()
            if target.target.exists() or target.target.is_symlink()
            else None
        )
        stage_content = stage.read_bytes() if stage.exists() else None
        backup_content = backup.read_bytes() if backup.exists() else None
    except OSError as exc:
        return _path_conflict("path-conflict", f"{exc.filename or target.target}")

    # Every residue byte must itself be an emission known to this installer.  Never
    # delete a similarly named user file merely because it occupies our recovery path.
    if stage_content is not None and stage_content != desired:
        digest = f"sha256:{sha256_bytes(stage_content)}"
        return Inspection(
            "residue-conflict",
            None,
            digest,
            "conflict",
            "conflict",
            ("residue", digest),
            target_content,
            "none",
        )
    if backup_content is not None:
        backup_inspection = _classify_content(backup_content, desired)
        if backup_inspection.action == "conflict":
            return replace(backup_inspection, ownership="residue-conflict")
        if target_content is None:
            effective = replace(backup_inspection, residue="restore-backup")
        else:
            current = _classify_content(target_content, desired)
            if current.action == "conflict":
                return current
            if current.effective_content != backup_content and current.action != "unchanged":
                digest = f"sha256:{sha256_bytes(backup_content)}"
                return Inspection(
                    "residue-conflict",
                    None,
                    digest,
                    "conflict",
                    "conflict",
                    ("residue", digest),
                    target_content,
                    "none",
                )
            effective = replace(current, residue="discard-backup")
    else:
        effective = _classify_content(target_content, desired)
    if stage_content is not None and effective.action != "conflict":
        effective = replace(effective, residue="discard-stage")
    return effective


def _plan_file(target: ResolvedTarget, inspection: Inspection) -> dict[str, Any]:
    return {
        "agent": ",".join(target.agents),
        "base_dir": str(target.base_dir),
        "path": str(target.relative_path),
        "resolved_path": str(target.target),
        "ownership": inspection.ownership,
        "managed_format": inspection.managed_format,
        "prior_digest": inspection.prior_digest,
        "action": inspection.action,
        "status": inspection.status,
    }


def _build_report(
    *,
    package_version: str,
    scope: str,
    primary_base: Path,
    dry_run: bool,
    targets: Sequence[PlannedTarget],
) -> dict[str, Any]:
    return {
        "version": package_version,
        "target_table": TARGET_TABLE_VERSION,
        "scope": scope,
        "base_dir": str(primary_base),
        "dry_run": dry_run,
        "files": [_plan_file(item.resolved, item.inspection) for item in targets],
    }


def plan_skill_install(
    request: InstallRequest,
    *,
    rendered_skill: str,
    marker: str,
    package_version: str,
    cwd: Path,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[int, dict[str, Any], tuple[PlannedTarget, ...]]:
    """Return a complete, mutation-free plan and its predicted exit status."""
    scope, primary_base, resolved = resolve_targets(request, cwd=cwd, home=home, env=env)
    desired = install_skill_payload(rendered_skill, marker).encode("utf-8")
    planned = tuple(PlannedTarget(target, _inspect_target(target, desired)) for target in resolved)
    for base in sorted({item.resolved.base_dir for item in planned}, key=_utf8_sort_key):
        lock_path = base / LOCK_NAME
        if (lock_path.exists() or lock_path.is_symlink()) and _lock_is_active(lock_path):
            planned = _mark_conflict(planned, ownership="lock-conflict", base=base)
    exit_code = 1 if any(item.inspection.action == "conflict" for item in planned) else 0
    report = _build_report(
        package_version=package_version,
        scope=scope,
        primary_base=primary_base,
        dry_run=request.dry_run,
        targets=planned,
    )
    return exit_code, report, planned


def install_skill_payload(rendered: str, marker: str) -> str:
    """Insert the destination marker after the closing frontmatter delimiter."""
    lines = rendered.split("\n")
    delimiters = 0
    for index, line in enumerate(lines):
        if line.strip() == "---":
            delimiters += 1
            if delimiters == 2:
                lines.insert(index + 1, marker)
                return "\n".join(lines)
    raise SkillInstallExecutionError(
        errno.EINVAL, "bundled skill is missing its closing frontmatter delimiter"
    )


def _pid_is_active(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _lock_is_active(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("format") != "softschema-skill-lock-v1":
            return True
        pid = payload["pid"]
    except (OSError, ValueError, KeyError, TypeError):
        return True
    if type(pid) is not int or pid <= 0:
        return True
    return _pid_is_active(pid)


def _acquire_lock(base: Path) -> _HeldLock:
    base.mkdir(parents=True, exist_ok=True)
    path = base / LOCK_NAME
    for _attempt in range(3):
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            try:
                stale_inode = path.stat(follow_symlinks=False).st_ino
            except FileNotFoundError:
                continue
            if _lock_is_active(path):
                raise BlockingIOError(
                    errno.EWOULDBLOCK, f"installer base is locked: {base}"
                ) from None
            with suppress(FileNotFoundError):
                if path.stat(follow_symlinks=False).st_ino == stale_inode:
                    path.unlink()
            continue
        try:
            payload = json.dumps(
                {"format": "softschema-skill-lock-v1", "pid": os.getpid()},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            offset = 0
            while offset < len(payload):
                offset += os.write(descriptor, payload[offset:])
            os.fsync(descriptor)
            inode = os.fstat(descriptor).st_ino
        finally:
            os.close(descriptor)
        return _HeldLock(path, inode)
    raise BlockingIOError(errno.EWOULDBLOCK, f"could not acquire installer lock: {base}")


def _release_lock(lock: _HeldLock) -> None:
    try:
        if lock.path.stat(follow_symlinks=False).st_ino == lock.inode:
            lock.path.unlink()
    except FileNotFoundError:
        pass


def _mkdirs(path: Path, created: list[Path]) -> None:
    missing: list[Path] = []
    probe = path
    while not probe.exists():
        missing.append(probe)
        probe = probe.parent
    for directory in reversed(missing):
        directory.mkdir()
        created.append(directory)


def _cleanup_empty_directories(created: Sequence[Path]) -> None:
    for directory in reversed(created):
        with suppress(OSError):
            directory.rmdir()


def _repair_residue(item: PlannedTarget, desired: bytes) -> None:
    target = item.resolved.target
    stage = target.with_name(target.name + STAGE_SUFFIX)
    backup = target.with_name(target.name + BACKUP_SUFFIX)
    if backup.exists() and not target.exists():
        os.replace(backup, target)
    elif backup.exists():
        backup.unlink()
    if stage.exists():
        # Revalidation has already proved this is exactly the desired staged payload.
        if stage.read_bytes() != desired:
            raise SkillInstallExecutionError(
                errno.EBUSY, f"installer residue changed during repair: {stage}"
            )
        stage.unlink(missing_ok=True)


def _stage_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rollback(changed: Sequence[tuple[Path, bool]], staged: Sequence[Path]) -> None:
    failures: list[str] = []
    for target, had_existing in reversed(changed):
        backup = target.with_name(target.name + BACKUP_SUFFIX)
        stage = target.with_name(target.name + STAGE_SUFFIX)
        try:
            if backup.exists():
                target.unlink(missing_ok=True)
                os.replace(backup, target)
            elif not had_existing:
                target.unlink(missing_ok=True)
            stage.unlink(missing_ok=True)
        except OSError as exc:
            failures.append(f"{target}: {exc}")
    for target in staged:
        try:
            target.with_name(target.name + STAGE_SUFFIX).unlink(missing_ok=True)
        except OSError as exc:
            failures.append(f"{target}: {exc}")
    if failures:
        raise SkillInstallExecutionError(
            errno.EIO, "install rollback left recoverable residue: " + "; ".join(failures)
        )


def _mark_conflict(
    planned: Sequence[PlannedTarget], *, ownership: str, base: Path | None = None
) -> tuple[PlannedTarget, ...]:
    result: list[PlannedTarget] = []
    for item in planned:
        if base is None or item.resolved.base_dir == base:
            if item.inspection.action == "conflict":
                result.append(item)
                continue
            inspection = replace(
                item.inspection,
                ownership=ownership,
                action="conflict",
                status="conflict",
            )
            result.append(replace(item, inspection=inspection))
        else:
            result.append(item)
    return tuple(result)


def execute_skill_install(
    request: InstallRequest,
    *,
    rendered_skill: str,
    marker: str,
    package_version: str,
    cwd: Path,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
    fault_injector: FaultInjector | None = None,
) -> tuple[int, dict[str, Any]]:
    """Plan and, unless dry-run/conflicted, execute a recoverable transaction."""
    fault = fault_injector or (lambda _boundary: None)
    code, report, planned = plan_skill_install(
        request,
        rendered_skill=rendered_skill,
        marker=marker,
        package_version=package_version,
        cwd=cwd,
        home=home,
        env=env,
    )
    if code != 0 or request.dry_run:
        return code, report

    desired = install_skill_payload(rendered_skill, marker).encode("utf-8")
    bases = sorted({item.resolved.base_dir for item in planned}, key=_utf8_sort_key)
    held: list[_HeldLock] = []
    created_directories: list[Path] = []
    changed: list[tuple[Path, bool]] = []
    staged: list[Path] = []
    committed = False
    try:
        for base in bases:
            _mkdirs(base, created_directories)
            try:
                lock = _acquire_lock(base)
            except BlockingIOError:
                conflicted = _mark_conflict(planned, ownership="lock-conflict", base=base)
                return 1, _build_report(
                    package_version=package_version,
                    scope=report["scope"],
                    primary_base=Path(report["base_dir"]),
                    dry_run=False,
                    targets=conflicted,
                )
            held.append(lock)
            fault(f"after-lock:{base}")

        # Revalidate every target under all sorted locks before the first repair/write.
        revalidated = tuple(
            PlannedTarget(item.resolved, _inspect_target(item.resolved, desired))
            for item in planned
        )
        if any(
            new.inspection.fingerprint != old.inspection.fingerprint
            or new.inspection.action == "conflict"
            for old, new in zip(planned, revalidated, strict=True)
        ):
            conflicted = _mark_conflict(revalidated, ownership="changed-during-install")
            return 1, _build_report(
                package_version=package_version,
                scope=report["scope"],
                primary_base=Path(report["base_dir"]),
                dry_run=False,
                targets=conflicted,
            )
        planned = revalidated
        fault("after-revalidate")

        for item in planned:
            if item.inspection.residue != "none":
                _repair_residue(item, desired)
        # Repair can change the effective action (for example restore a prior backup),
        # so inspect once more before staging.
        planned = tuple(
            PlannedTarget(item.resolved, _inspect_target(item.resolved, desired))
            for item in planned
        )
        if any(item.inspection.action == "conflict" for item in planned):
            conflicted = _mark_conflict(planned, ownership="changed-during-repair")
            return 1, _build_report(
                package_version=package_version,
                scope=report["scope"],
                primary_base=Path(report["base_dir"]),
                dry_run=False,
                targets=conflicted,
            )

        actionable = [item for item in planned if item.inspection.action != "unchanged"]
        for item in actionable:
            parent = item.resolved.target.parent
            _mkdirs(parent, created_directories)
            canonical_parent = parent.resolve(strict=False)
            if not _is_relative_to(canonical_parent, item.resolved.base_dir):
                raise SkillInstallExecutionError(
                    errno.EPERM,
                    f"target parent escaped its selected base during install: {parent}",
                )
            stage = item.resolved.target.with_name(item.resolved.target.name + STAGE_SUFFIX)
            _stage_file(stage, desired)
            staged.append(item.resolved.target)
            fault(f"after-stage:{item.resolved.target}")

        fault("after-stage-all")
        pre_replace = tuple(
            PlannedTarget(item.resolved, _inspect_target(item.resolved, desired))
            for item in planned
        )
        if any(
            new.inspection.fingerprint != old.inspection.fingerprint
            or new.inspection.action == "conflict"
            for old, new in zip(planned, pre_replace, strict=True)
        ):
            _rollback((), staged)
            conflicted = _mark_conflict(pre_replace, ownership="changed-before-replace")
            return 1, _build_report(
                package_version=package_version,
                scope=report["scope"],
                primary_base=Path(report["base_dir"]),
                dry_run=False,
                targets=conflicted,
            )
        planned = pre_replace
        fault("after-pre-replace-revalidate")

        for item in actionable:
            target = item.resolved.target
            stage = target.with_name(target.name + STAGE_SUFFIX)
            backup = target.with_name(target.name + BACKUP_SUFFIX)
            had_existing = target.exists()
            changed.append((target, had_existing))
            if had_existing:
                os.replace(target, backup)
                fault(f"after-backup:{target}")
            os.replace(stage, target)
            fault(f"after-replace:{target}")

        fault("before-cleanup")
        committed = True
        for target, _had_existing in changed:
            target.with_name(target.name + BACKUP_SUFFIX).unlink(missing_ok=True)
            fault(f"after-backup-cleanup:{target}")
        # The observable plan is the preflight plan: it says what this invocation did.
        return 0, report
    except Exception as exc:
        if committed:
            raise SkillInstallExecutionError(
                errno.EIO,
                f"skill install committed but cleanup left recoverable residue: {exc}",
            ) from exc
        try:
            _rollback(changed, staged)
        except SkillInstallExecutionError as rollback_error:
            raise rollback_error from exc
        if isinstance(exc, OSError):
            raise SkillInstallExecutionError(
                exc.errno or errno.EIO, f"skill install failed and was rolled back: {exc}"
            ) from exc
        raise
    finally:
        for lock in reversed(held):
            _release_lock(lock)
        _cleanup_empty_directories(created_directories)


def format_install_plan_text(report: Mapping[str, Any]) -> str:
    """Render a stable human plan without hiding canonical destinations."""
    lines = [
        f"softschema skill install ({report['scope']}, {report['target_table']})",
        f"base: {report['base_dir']}",
        f"dry-run: {'yes' if report['dry_run'] else 'no'}",
    ]
    for file in report["files"]:
        lines.append(
            f"{file['action']:<9} {file['ownership']:<27} "
            f"{file['agent']:<12} {file['resolved_path']}"
        )
    return "\n".join(lines)
