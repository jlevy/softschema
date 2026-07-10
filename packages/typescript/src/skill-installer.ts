/** Safe, cross-agent installation for the bundled softschema skill. */

import { createHash } from "node:crypto";
import {
  closeSync,
  existsSync,
  fstatSync,
  fsyncSync,
  lstatSync,
  mkdirSync,
  openSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmdirSync,
  statSync,
  unlinkSync,
  writeSync,
} from "node:fs";
import { homedir } from "node:os";
import {
  basename,
  dirname,
  isAbsolute,
  join,
  normalize,
  parse,
  relative,
  resolve,
  sep,
} from "node:path";

export const TARGET_TABLE_VERSION = "agent-targets-v1";
export const MANAGED_FORMAT = "f01";
export const LOCK_NAME = ".softschema-skill-install.lock";
export const STAGE_SUFFIX = ".softschema-stage";
export const BACKUP_SUFFIX = ".softschema-backup";

export const KNOWN_PRIOR_EMISSION_SHA256 = new Set([
  "554bf881da03dbf3c36a2c7444d7ef469d38783ba2c27c7b2e035e4b233339c0",
  "a0ab855baa1a65a32f09636536991f55a72115c6f9aa6ab51de6db2ee1c6eba6",
  "5123905a93350417abbb702d74fd9b5d92684199560c27694426326e8e8e1f43",
  "ff9ffe0e8aa3f79951a475cf6f4378e17783041fab47687615d037c93c4ee98c",
  "63fb27814dfad5ad8ea090c1879bb13d861915bd7084a5774b543ba16bd06fc5",
  "58dce894b18dabdbd6cf44b38c6db0413f848a44a3d44a6e7b794e95bd3c298a",
  "b65f2971a93ddbbf0169a3f35035983f7fd35f98dd5d15e1e7ea25e078a1a62e",
  "9bb289188f95d40214e37f087b993f41540b37bc123e79b052682181ed8d6080",
]);

const MANAGED_MARKER_RE =
  /<!-- DO NOT EDIT format=f(?<format>[0-9]+): written by `softschema skill --install`\.\n/;

export interface AgentTarget {
  selector: string;
  projectRoot: string;
  personalRoot: string;
  homeOverride: string | null;
  overrideRoot: string | null;
}

export const AGENT_TARGETS: readonly AgentTarget[] = [
  {
    selector: "codex",
    projectRoot: ".agents/skills",
    personalRoot: ".agents/skills",
    homeOverride: null,
    overrideRoot: null,
  },
  {
    selector: "claude",
    projectRoot: ".claude/skills",
    personalRoot: ".claude/skills",
    homeOverride: "CLAUDE_CONFIG_DIR",
    overrideRoot: "skills",
  },
  {
    selector: "gemini",
    projectRoot: ".gemini/skills",
    personalRoot: ".gemini/skills",
    homeOverride: "GEMINI_CLI_HOME",
    overrideRoot: ".gemini/skills",
  },
  {
    selector: "copilot",
    projectRoot: ".github/skills",
    personalRoot: ".copilot/skills",
    homeOverride: "COPILOT_HOME",
    overrideRoot: "skills",
  },
  {
    selector: "cursor",
    projectRoot: ".cursor/skills",
    personalRoot: ".cursor/skills",
    homeOverride: null,
    overrideRoot: null,
  },
  {
    selector: "windsurf",
    projectRoot: ".windsurf/skills",
    personalRoot: ".codeium/windsurf/skills",
    homeOverride: null,
    overrideRoot: null,
  },
  {
    selector: "opencode",
    projectRoot: ".opencode/skills",
    personalRoot: ".config/opencode/skills",
    homeOverride: null,
    overrideRoot: null,
  },
  {
    selector: "cline",
    projectRoot: ".cline/skills",
    personalRoot: ".cline/skills",
    homeOverride: null,
    overrideRoot: null,
  },
  {
    selector: "roo",
    projectRoot: ".roo/skills",
    personalRoot: ".roo/skills",
    homeOverride: null,
    overrideRoot: null,
  },
];

const AGENT_TARGETS_BY_NAME = new Map(AGENT_TARGETS.map((target) => [target.selector, target]));
const IMPLICIT_PROJECT_AGENTS = ["codex", "claude"] as const;

export class SkillInstallUsageError extends Error {}
export class SkillInstallExecutionError extends Error {}

export interface InstallRequest {
  project?: boolean;
  globalScope?: boolean;
  directory?: string;
  agents?: readonly string[];
  allAgents?: boolean;
  noRepoCheck?: boolean;
  dryRun?: boolean;
}

export interface ResolvedTarget {
  agents: readonly string[];
  baseDir: string;
  relativePath: string;
  target: string;
}

type Action = "create" | "update" | "unchanged" | "conflict";
type Status = "created" | "updated" | "unchanged" | "conflict";
type Residue = "none" | "discard-stage" | "restore-backup" | "discard-backup";

interface Inspection {
  ownership: string;
  managedFormat: string | null;
  priorDigest: string | null;
  action: Action;
  status: Status;
  fingerprint: readonly [string, string | null];
  effectiveContent: Buffer | null;
  residue: Residue;
}

export interface PlannedTarget {
  resolved: ResolvedTarget;
  inspection: Inspection;
}

export interface InstallFilePlan {
  agent: string;
  base_dir: string;
  path: string;
  resolved_path: string;
  ownership: string;
  managed_format: string | null;
  prior_digest: string | null;
  action: Action;
  status: Status;
}

export interface InstallReport {
  version: string;
  target_table: string;
  scope: "project" | "global";
  base_dir: string;
  dry_run: boolean;
  files: InstallFilePlan[];
}

interface HeldLock {
  path: string;
  inode: number;
}

export type FaultInjector = (boundary: string) => void;

function sha256(content: Buffer): string {
  return createHash("sha256").update(content).digest("hex");
}

function compareUtf8(left: string, right: string): number {
  return Buffer.compare(Buffer.from(left, "utf8"), Buffer.from(right, "utf8"));
}

/** Resolve existing symlink parents while permitting a missing final suffix. */
function realpathAllowMissing(path: string): string {
  let probe = resolve(path);
  const tail: string[] = [];
  while (!existsSync(probe)) {
    const parent = dirname(probe);
    if (parent === probe) return probe;
    tail.unshift(basename(probe));
    probe = parent;
  }
  return resolve(realpathSync(probe), ...tail);
}

function isWithin(path: string, base: string): boolean {
  const rel = relative(base, path);
  return rel === "" || (!rel.startsWith(`..${sep}`) && rel !== ".." && !isAbsolute(rel));
}

function actualHome(home: string | undefined): string {
  return realpathAllowMissing(home ?? homedir());
}

function findGitRoot(start: string): string | null {
  const canonical = realpathAllowMissing(start);
  let probe =
    existsSync(canonical) && statSync(canonical).isDirectory() ? canonical : dirname(canonical);
  for (;;) {
    if (existsSync(join(probe, ".git"))) return realpathAllowMissing(probe);
    const parent = dirname(probe);
    if (parent === probe) return null;
    probe = parent;
  }
}

function requireSafeBase(base: string, home: string, scope: "project" | "global"): string {
  const canonical = realpathAllowMissing(base);
  if (parse(canonical).root === canonical) {
    throw new SkillInstallUsageError(`${scope} install base must not be the filesystem root`);
  }
  if (scope === "project" && canonical === home) {
    throw new SkillInstallUsageError("project install base must not be the user home directory");
  }
  return canonical;
}

function selectorNames(request: InstallRequest, scope: "project" | "global"): string[] {
  const requested = request.agents ?? [];
  if (requested.length > 0 && request.allAgents === true) {
    throw new SkillInstallUsageError("--agent and --all-agents are mutually exclusive");
  }
  if (scope === "global" && requested.length === 0 && request.allAgents !== true) {
    throw new SkillInstallUsageError("--global requires --agent NAME or --all-agents");
  }
  const raw =
    request.allAgents === true ? AGENT_TARGETS.map((target) => target.selector) : requested;
  const source = raw.length === 0 ? IMPLICIT_PROJECT_AGENTS : raw;
  const names: string[] = [];
  for (const name of source) {
    const normalized = name.trim().toLowerCase();
    if (normalized === "aider") {
      throw new SkillInstallUsageError(
        "unsupported agent target 'aider': aider has no documented native Agent Skills target; use its read: compatibility recipe",
      );
    }
    if (!AGENT_TARGETS_BY_NAME.has(normalized)) {
      const choices = AGENT_TARGETS.map((target) => target.selector).join(", ");
      throw new SkillInstallUsageError(
        `unknown agent target ${JSON.stringify(name)}; supported targets: ${choices}`,
      );
    }
    if (!names.includes(normalized)) names.push(normalized);
  }
  const selected = new Set(names);
  return AGENT_TARGETS.map((target) => target.selector).filter((name) => selected.has(name));
}

export function resolveTargets(
  request: InstallRequest,
  options: { cwd: string; home?: string; env?: Readonly<Record<string, string | undefined>> },
): { scope: "project" | "global"; primaryBase: string; targets: ResolvedTarget[] } {
  if (request.project === true && request.globalScope === true) {
    throw new SkillInstallUsageError("--project and --global are mutually exclusive");
  }
  if (request.directory !== undefined && request.project !== true) {
    throw new SkillInstallUsageError("--dir requires explicit --project");
  }
  if (request.globalScope === true && request.directory !== undefined) {
    throw new SkillInstallUsageError("--global and --dir are mutually exclusive");
  }
  if (request.noRepoCheck === true && request.project !== true) {
    throw new SkillInstallUsageError("--no-repo-check requires explicit --project");
  }

  const home = actualHome(options.home);
  const env = options.env ?? process.env;
  const scope = request.globalScope === true ? "global" : "project";
  const selectors = selectorNames(request, scope);
  const targets: ResolvedTarget[] = [];
  let primaryBase: string;

  if (scope === "project") {
    const requested = realpathAllowMissing(request.directory ?? options.cwd);
    const gitRoot = findGitRoot(requested);
    if (gitRoot === null && request.noRepoCheck !== true) {
      if (request.project !== true) {
        throw new SkillInstallUsageError(
          "skill install scope is ambiguous outside a Git repository; pass --project --no-repo-check --dir PATH or --global with agent selectors",
        );
      }
      throw new SkillInstallUsageError(
        "project install target is not inside a Git repository; pass --no-repo-check to confirm this destination",
      );
    }
    primaryBase = requireSafeBase(gitRoot ?? requested, home, scope);
    for (const selector of selectors) {
      const definition = AGENT_TARGETS_BY_NAME.get(selector);
      if (definition === undefined) throw new Error("validated selector is missing");
      const relativePath = join(definition.projectRoot, "softschema", "SKILL.md");
      targets.push({
        agents: [selector],
        baseDir: primaryBase,
        relativePath,
        target: join(primaryBase, relativePath),
      });
    }
  } else {
    primaryBase = requireSafeBase(home, home, scope);
    for (const selector of selectors) {
      const definition = AGENT_TARGETS_BY_NAME.get(selector);
      if (definition === undefined) throw new Error("validated selector is missing");
      const overrideValue =
        definition.homeOverride === null ? undefined : env[definition.homeOverride];
      let base = primaryBase;
      let root = definition.personalRoot;
      if (overrideValue !== undefined && overrideValue !== "") {
        if (!isAbsolute(overrideValue) || normalize(overrideValue) !== overrideValue) {
          throw new SkillInstallUsageError(
            `${definition.homeOverride} must be an absolute normalized path`,
          );
        }
        base = requireSafeBase(overrideValue, home, scope);
        if (definition.overrideRoot === null) throw new Error("agent override root is missing");
        root = definition.overrideRoot;
      }
      const relativePath = join(root, "softschema", "SKILL.md");
      targets.push({
        agents: [selector],
        baseDir: base,
        relativePath,
        target: join(base, relativePath),
      });
    }
  }

  const deduplicated = new Map<string, ResolvedTarget>();
  for (const target of targets) {
    const canonicalTarget = realpathAllowMissing(target.target);
    if (!isWithin(canonicalTarget, target.baseDir)) {
      throw new SkillInstallUsageError(
        `target path escapes its selected base through a symlink: ${target.target}`,
      );
    }
    const canonicalKey =
      process.platform === "win32" ? canonicalTarget.toLowerCase() : canonicalTarget;
    const existing = deduplicated.get(canonicalKey);
    if (existing === undefined) {
      deduplicated.set(canonicalKey, target);
    } else {
      deduplicated.set(canonicalKey, {
        ...existing,
        agents: [...new Set([...existing.agents, ...target.agents])].sort(),
      });
    }
  }
  const ordered = [...deduplicated.values()].sort(
    (a, b) => compareUtf8(a.baseDir, b.baseDir) || compareUtf8(a.relativePath, b.relativePath),
  );
  return { scope, primaryBase, targets: ordered };
}

function lexists(path: string): boolean {
  try {
    lstatSync(path);
    return true;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return false;
    throw error;
  }
}

function pathConflict(ownership: string, detail: string): Inspection {
  return {
    ownership,
    managedFormat: null,
    priorDigest: null,
    action: "conflict",
    status: "conflict",
    fingerprint: ["path", detail],
    effectiveContent: null,
    residue: "none",
  };
}

function managedFormat(content: Buffer): number | null {
  const match = MANAGED_MARKER_RE.exec(content.toString("utf8"));
  const value = match?.groups?.format;
  return value === undefined ? null : Number.parseInt(value, 10);
}

function classifyContent(content: Buffer | null, desired: Buffer): Inspection {
  if (content === null) {
    return {
      ownership: "absent",
      managedFormat: null,
      priorDigest: null,
      action: "create",
      status: "created",
      fingerprint: ["absent", null],
      effectiveContent: null,
      residue: "none",
    };
  }
  const digest = sha256(content);
  const digestField = `sha256:${digest}`;
  const managed = managedFormat(content);
  if (content.equals(desired)) {
    return {
      ownership: "managed",
      managedFormat: MANAGED_FORMAT,
      priorDigest: digestField,
      action: "unchanged",
      status: "unchanged",
      fingerprint: ["file", digest],
      effectiveContent: content,
      residue: "none",
    };
  }
  if (KNOWN_PRIOR_EMISSION_SHA256.has(digest)) {
    return {
      ownership: "managed-prior",
      managedFormat: managed === null ? null : `f${managed.toString().padStart(2, "0")}`,
      priorDigest: digestField,
      action: "update",
      status: "updated",
      fingerprint: ["file", digest],
      effectiveContent: content,
      residue: "none",
    };
  }
  let ownership: string;
  if (managed === null) ownership = "unmanaged";
  else if (managed > Number.parseInt(MANAGED_FORMAT.slice(1), 10)) ownership = "newer-managed";
  else if (managed !== Number.parseInt(MANAGED_FORMAT.slice(1), 10)) ownership = "unknown-managed";
  else ownership = "modified-or-unknown-managed";
  return {
    ownership,
    managedFormat: managed === null ? null : `f${managed.toString().padStart(2, "0")}`,
    priorDigest: digestField,
    action: "conflict",
    status: "conflict",
    fingerprint: ["file", digest],
    effectiveContent: content,
    residue: "none",
  };
}

function inspectTarget(target: ResolvedTarget, desired: Buffer): Inspection {
  const stage = `${target.target}${STAGE_SUFFIX}`;
  const backup = `${target.target}${BACKUP_SUFFIX}`;
  let probe = dirname(target.target);
  while (probe !== target.baseDir) {
    try {
      if (lexists(probe) && !statSync(probe).isDirectory()) {
        return pathConflict("path-conflict", probe);
      }
    } catch {
      return pathConflict("path-conflict", probe);
    }
    probe = dirname(probe);
  }
  for (const residuePath of [stage, backup]) {
    try {
      if (lexists(residuePath) && !statSync(residuePath).isFile()) {
        return pathConflict("residue-conflict", residuePath);
      }
    } catch {
      return pathConflict("residue-conflict", residuePath);
    }
  }
  try {
    if (lexists(target.target) && !statSync(target.target).isFile()) {
      return pathConflict("path-conflict", target.target);
    }
  } catch {
    return pathConflict("path-conflict", target.target);
  }
  let targetContent: Buffer | null;
  let stageContent: Buffer | null;
  let backupContent: Buffer | null;
  try {
    targetContent = lexists(target.target) ? readFileSync(target.target) : null;
    stageContent = lexists(stage) ? readFileSync(stage) : null;
    backupContent = lexists(backup) ? readFileSync(backup) : null;
  } catch (error) {
    return pathConflict("path-conflict", (error as NodeJS.ErrnoException).path ?? target.target);
  }

  if (stageContent !== null && !stageContent.equals(desired)) {
    const digest = `sha256:${sha256(stageContent)}`;
    return {
      ownership: "residue-conflict",
      managedFormat: null,
      priorDigest: digest,
      action: "conflict",
      status: "conflict",
      fingerprint: ["residue", digest],
      effectiveContent: targetContent,
      residue: "none",
    };
  }

  let effective: Inspection;
  if (backupContent !== null) {
    const backupInspection = classifyContent(backupContent, desired);
    if (backupInspection.action === "conflict") {
      effective = { ...backupInspection, ownership: "residue-conflict" };
    } else if (targetContent === null) {
      effective = { ...backupInspection, residue: "restore-backup" };
    } else {
      const current = classifyContent(targetContent, desired);
      if (current.action === "conflict") return current;
      if (!current.effectiveContent?.equals(backupContent) && current.action !== "unchanged") {
        const digest = `sha256:${sha256(backupContent)}`;
        return {
          ownership: "residue-conflict",
          managedFormat: null,
          priorDigest: digest,
          action: "conflict",
          status: "conflict",
          fingerprint: ["residue", digest],
          effectiveContent: targetContent,
          residue: "none",
        };
      }
      effective = { ...current, residue: "discard-backup" };
    }
  } else {
    effective = classifyContent(targetContent, desired);
  }
  if (stageContent !== null && effective.action !== "conflict") {
    effective = { ...effective, residue: "discard-stage" };
  }
  return effective;
}

function planFile(target: ResolvedTarget, inspection: Inspection): InstallFilePlan {
  return {
    agent: target.agents.join(","),
    base_dir: target.baseDir,
    path: target.relativePath,
    resolved_path: target.target,
    ownership: inspection.ownership,
    managed_format: inspection.managedFormat,
    prior_digest: inspection.priorDigest,
    action: inspection.action,
    status: inspection.status,
  };
}

function buildReport(
  packageVersion: string,
  scope: "project" | "global",
  primaryBase: string,
  dryRun: boolean,
  targets: readonly PlannedTarget[],
): InstallReport {
  return {
    version: packageVersion,
    target_table: TARGET_TABLE_VERSION,
    scope,
    base_dir: primaryBase,
    dry_run: dryRun,
    files: targets.map((item) => planFile(item.resolved, item.inspection)),
  };
}

export function installSkillPayload(rendered: string, marker: string): string {
  const lines = rendered.split("\n");
  let delimiters = 0;
  for (let index = 0; index < lines.length; index += 1) {
    if (lines[index]?.trim() === "---") {
      delimiters += 1;
      if (delimiters === 2) {
        lines.splice(index + 1, 0, marker);
        return lines.join("\n");
      }
    }
  }
  throw new SkillInstallExecutionError(
    "bundled skill is missing its closing frontmatter delimiter",
  );
}

export function planSkillInstall(
  request: InstallRequest,
  options: {
    renderedSkill: string;
    marker: string;
    packageVersion: string;
    cwd: string;
    home?: string;
    env?: Readonly<Record<string, string | undefined>>;
  },
): { code: number; report: InstallReport; planned: PlannedTarget[] } {
  const { scope, primaryBase, targets } = resolveTargets(request, options);
  const desired = Buffer.from(installSkillPayload(options.renderedSkill, options.marker), "utf8");
  let planned = targets.map((target) => ({
    resolved: target,
    inspection: inspectTarget(target, desired),
  }));
  for (const base of [...new Set(planned.map((item) => item.resolved.baseDir))].sort(compareUtf8)) {
    const lockPath = join(base, LOCK_NAME);
    if (lexists(lockPath) && lockIsActive(lockPath)) {
      planned = markConflict(planned, "lock-conflict", base);
    }
  }
  const code = planned.some((item) => item.inspection.action === "conflict") ? 1 : 0;
  return {
    code,
    report: buildReport(
      options.packageVersion,
      scope,
      primaryBase,
      request.dryRun === true,
      planned,
    ),
    planned,
  };
}

function pidIsActive(pid: number): boolean {
  if (!Number.isSafeInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return (error as NodeJS.ErrnoException).code !== "ESRCH";
  }
}

function lockIsActive(path: string): boolean {
  try {
    if (lstatSync(path).isSymbolicLink()) return true;
    const payload = JSON.parse(readFileSync(path, "utf8")) as {
      format?: unknown;
      pid?: unknown;
    };
    return (
      payload.format !== "softschema-skill-lock-v1" ||
      typeof payload.pid !== "number" ||
      !Number.isSafeInteger(payload.pid) ||
      payload.pid <= 0 ||
      pidIsActive(payload.pid)
    );
  } catch {
    return true;
  }
}

export function acquireLock(base: string): HeldLock {
  mkdirSync(base, { recursive: true });
  const path = join(base, LOCK_NAME);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    let descriptor: number;
    try {
      descriptor = openSync(path, "wx", 0o600);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
      let staleInode: number;
      try {
        staleInode = lstatSync(path).ino;
      } catch (statError) {
        if ((statError as NodeJS.ErrnoException).code === "ENOENT") continue;
        throw statError;
      }
      if (lockIsActive(path)) {
        const lockError = new Error(`installer base is locked: ${base}`) as NodeJS.ErrnoException;
        lockError.code = "EWOULDBLOCK";
        throw lockError;
      }
      try {
        if (lstatSync(path).ino === staleInode) unlinkSync(path);
      } catch (unlinkError) {
        if ((unlinkError as NodeJS.ErrnoException).code !== "ENOENT") throw unlinkError;
      }
      continue;
    }
    try {
      const payload = Buffer.from(
        JSON.stringify({ format: "softschema-skill-lock-v1", pid: process.pid }),
      );
      let offset = 0;
      while (offset < payload.length) offset += writeSync(descriptor, payload, offset);
      fsyncSync(descriptor);
      return { path, inode: fstatSync(descriptor).ino };
    } finally {
      closeSync(descriptor);
    }
  }
  const error = new Error(`could not acquire installer lock: ${base}`) as NodeJS.ErrnoException;
  error.code = "EWOULDBLOCK";
  throw error;
}

export function releaseLock(lock: HeldLock): void {
  try {
    if (lstatSync(lock.path).ino === lock.inode) unlinkSync(lock.path);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
}

function mkdirs(path: string, created: string[]): void {
  const missing: string[] = [];
  let probe = path;
  while (!existsSync(probe)) {
    missing.push(probe);
    probe = dirname(probe);
  }
  for (const directory of missing.reverse()) {
    mkdirSync(directory);
    created.push(directory);
  }
}

function cleanupEmptyDirectories(created: readonly string[]): void {
  for (const directory of [...created].reverse()) {
    try {
      rmdirSync(directory);
    } catch {
      // Expected when a successful target keeps the directory non-empty.
    }
  }
}

function repairResidue(item: PlannedTarget, desired: Buffer): void {
  const target = item.resolved.target;
  const stage = `${target}${STAGE_SUFFIX}`;
  const backup = `${target}${BACKUP_SUFFIX}`;
  if (existsSync(backup) && !existsSync(target)) renameSync(backup, target);
  else if (existsSync(backup)) unlinkSync(backup);
  if (existsSync(stage)) {
    if (!readFileSync(stage).equals(desired)) {
      throw new SkillInstallExecutionError(`installer residue changed during repair: ${stage}`);
    }
    unlinkSync(stage);
  }
}

function stageFile(path: string, payload: Buffer): void {
  const descriptor = openSync(path, "wx", 0o644);
  try {
    let offset = 0;
    while (offset < payload.length) offset += writeSync(descriptor, payload, offset);
    fsyncSync(descriptor);
  } finally {
    closeSync(descriptor);
  }
}

function rollback(changed: readonly [string, boolean][], staged: readonly string[]): void {
  const failures: string[] = [];
  for (const [target, hadExisting] of [...changed].reverse()) {
    const backup = `${target}${BACKUP_SUFFIX}`;
    try {
      if (existsSync(backup)) {
        if (existsSync(target)) unlinkSync(target);
        renameSync(backup, target);
      } else if (!hadExisting && existsSync(target)) {
        unlinkSync(target);
      }
      if (existsSync(`${target}${STAGE_SUFFIX}`)) unlinkSync(`${target}${STAGE_SUFFIX}`);
    } catch (error) {
      failures.push(`${target}: ${(error as Error).message}`);
    }
  }
  for (const target of staged) {
    try {
      if (existsSync(`${target}${STAGE_SUFFIX}`)) unlinkSync(`${target}${STAGE_SUFFIX}`);
    } catch (error) {
      failures.push(`${target}: ${(error as Error).message}`);
    }
  }
  if (failures.length > 0) {
    throw new SkillInstallExecutionError(
      `install rollback left recoverable residue: ${failures.join("; ")}`,
    );
  }
}

function markConflict(
  planned: readonly PlannedTarget[],
  ownership: string,
  base?: string,
): PlannedTarget[] {
  return planned.map((item) => {
    if (base !== undefined && item.resolved.baseDir !== base) return item;
    if (item.inspection.action === "conflict") return item;
    return {
      ...item,
      inspection: { ...item.inspection, ownership, action: "conflict", status: "conflict" },
    };
  });
}

export function executeSkillInstall(
  request: InstallRequest,
  options: {
    renderedSkill: string;
    marker: string;
    packageVersion: string;
    cwd: string;
    home?: string;
    env?: Readonly<Record<string, string | undefined>>;
    faultInjector?: FaultInjector;
  },
): { code: number; report: InstallReport } {
  const fault = options.faultInjector ?? (() => undefined);
  const initial = planSkillInstall(request, options);
  if (initial.code !== 0 || request.dryRun === true) {
    return { code: initial.code, report: initial.report };
  }

  const desired = Buffer.from(installSkillPayload(options.renderedSkill, options.marker), "utf8");
  let planned = initial.planned;
  const bases = [...new Set(planned.map((item) => item.resolved.baseDir))].sort(compareUtf8);
  const held: HeldLock[] = [];
  const createdDirectories: string[] = [];
  const changed: [string, boolean][] = [];
  const staged: string[] = [];
  let committed = false;
  try {
    for (const base of bases) {
      mkdirs(base, createdDirectories);
      let lock: HeldLock;
      try {
        lock = acquireLock(base);
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "EWOULDBLOCK") throw error;
        const conflicted = markConflict(planned, "lock-conflict", base);
        return {
          code: 1,
          report: buildReport(
            options.packageVersion,
            initial.report.scope,
            initial.report.base_dir,
            false,
            conflicted,
          ),
        };
      }
      held.push(lock);
      fault(`after-lock:${base}`);
    }

    const revalidated = planned.map((item) => ({
      resolved: item.resolved,
      inspection: inspectTarget(item.resolved, desired),
    }));
    if (
      revalidated.some(
        (item, index) =>
          item.inspection.fingerprint[0] !== planned[index]?.inspection.fingerprint[0] ||
          item.inspection.fingerprint[1] !== planned[index]?.inspection.fingerprint[1] ||
          item.inspection.action === "conflict",
      )
    ) {
      const conflicted = markConflict(revalidated, "changed-during-install");
      return {
        code: 1,
        report: buildReport(
          options.packageVersion,
          initial.report.scope,
          initial.report.base_dir,
          false,
          conflicted,
        ),
      };
    }
    planned = revalidated;
    fault("after-revalidate");

    for (const item of planned) {
      if (item.inspection.residue !== "none") repairResidue(item, desired);
    }
    planned = planned.map((item) => ({
      resolved: item.resolved,
      inspection: inspectTarget(item.resolved, desired),
    }));
    if (planned.some((item) => item.inspection.action === "conflict")) {
      const conflicted = markConflict(planned, "changed-during-repair");
      return {
        code: 1,
        report: buildReport(
          options.packageVersion,
          initial.report.scope,
          initial.report.base_dir,
          false,
          conflicted,
        ),
      };
    }

    const actionable = planned.filter((item) => item.inspection.action !== "unchanged");
    for (const item of actionable) {
      const parent = dirname(item.resolved.target);
      mkdirs(parent, createdDirectories);
      if (!isWithin(realpathAllowMissing(parent), item.resolved.baseDir)) {
        throw new SkillInstallExecutionError(
          `target parent escaped its selected base during install: ${parent}`,
        );
      }
      stageFile(`${item.resolved.target}${STAGE_SUFFIX}`, desired);
      staged.push(item.resolved.target);
      fault(`after-stage:${item.resolved.target}`);
    }

    fault("after-stage-all");
    const preReplace = planned.map((item) => ({
      resolved: item.resolved,
      inspection: inspectTarget(item.resolved, desired),
    }));
    if (
      preReplace.some(
        (item, index) =>
          item.inspection.fingerprint[0] !== planned[index]?.inspection.fingerprint[0] ||
          item.inspection.fingerprint[1] !== planned[index]?.inspection.fingerprint[1] ||
          item.inspection.action === "conflict",
      )
    ) {
      rollback([], staged);
      const conflicted = markConflict(preReplace, "changed-before-replace");
      return {
        code: 1,
        report: buildReport(
          options.packageVersion,
          initial.report.scope,
          initial.report.base_dir,
          false,
          conflicted,
        ),
      };
    }
    planned = preReplace;
    fault("after-pre-replace-revalidate");

    for (const item of actionable) {
      const target = item.resolved.target;
      const hadExisting = existsSync(target);
      changed.push([target, hadExisting]);
      if (hadExisting) {
        renameSync(target, `${target}${BACKUP_SUFFIX}`);
        fault(`after-backup:${target}`);
      }
      renameSync(`${target}${STAGE_SUFFIX}`, target);
      fault(`after-replace:${target}`);
    }
    fault("before-cleanup");
    committed = true;
    for (const [target] of changed) {
      if (existsSync(`${target}${BACKUP_SUFFIX}`)) unlinkSync(`${target}${BACKUP_SUFFIX}`);
      fault(`after-backup-cleanup:${target}`);
    }
    return { code: 0, report: initial.report };
  } catch (error) {
    if (committed) {
      throw new SkillInstallExecutionError(
        `skill install committed but cleanup left recoverable residue: ${(error as Error).message}`,
        { cause: error },
      );
    }
    try {
      rollback(changed, staged);
    } catch (rollbackError) {
      throw new SkillInstallExecutionError((rollbackError as Error).message, { cause: error });
    }
    throw new SkillInstallExecutionError(
      `skill install failed and was rolled back: ${(error as Error).message}`,
      { cause: error },
    );
  } finally {
    for (const lock of [...held].reverse()) releaseLock(lock);
    cleanupEmptyDirectories(createdDirectories);
  }
}

export function formatInstallPlanText(report: InstallReport): string {
  const lines = [
    `softschema skill install (${report.scope}, ${report.target_table})`,
    `base: ${report.base_dir}`,
    `dry-run: ${report.dry_run ? "yes" : "no"}`,
  ];
  for (const file of report.files) {
    lines.push(
      `${file.action.padEnd(9)} ${file.ownership.padEnd(27)} ${file.agent.padEnd(12)} ${file.resolved_path}`,
    );
  }
  return lines.join("\n");
}
