/** Shared-contract and failure-boundary tests for the safe skill installer. */

import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  symlinkSync,
  truncateSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse as parseYaml } from "yaml";
import { SKILL_DO_NOT_EDIT_MARKER } from "../src/cli.js";
import {
  acquireLock,
  AGENT_TARGETS,
  BACKUP_SUFFIX,
  executeSkillInstall,
  formatInstallPlanText,
  installSkillPayload,
  KNOWN_PRIOR_EMISSION_SHA256,
  LOCK_NAME,
  MAX_MANAGED_SKILL_BYTES,
  MAX_SKILL_LOCK_BYTES,
  planSkillInstall,
  releaseLock,
  resolveTargets,
  SkillInstallExecutionError,
  SkillInstallUsageError,
  STAGE_SUFFIX,
  type FaultInjector,
  type InstallReport,
  type InstallRequest,
} from "../src/skill-installer.js";

const REPO_ROOT = resolve(import.meta.dir, "../../..");
const CONFORMANCE = join(REPO_ROOT, "conformance/skill-installer");
const SOURCE_SKILL = join(REPO_ROOT, "skills/softschema/SKILL.md");
const PRIOR_EMISSION = join(CONFORMANCE, "prior-emission-v0.1.1.md");
const VERSION = "test-version";

let root: string;

beforeEach(() => {
  root = realpathSync(mkdtempSync(join(tmpdir(), "softschema-safe-install-")));
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

function renderedSkill(): string {
  return readFileSync(SOURCE_SKILL, "utf8");
}

function makeRepo(name = "repo"): string {
  const repo = join(root, name);
  mkdirSync(join(repo, ".git"), { recursive: true });
  return repo;
}

function runInstall(
  request: InstallRequest,
  options: {
    cwd: string;
    home?: string;
    env?: Readonly<Record<string, string | undefined>>;
    faultInjector?: FaultInjector;
  },
): { code: number; report: InstallReport } {
  return executeSkillInstall(request, {
    renderedSkill: renderedSkill(),
    marker: SKILL_DO_NOT_EDIT_MARKER,
    packageVersion: VERSION,
    home: options.home ?? join(root, "home"),
    ...options,
  });
}

describe("agent-targets-v1 parity", () => {
  test("matches the shared target table", () => {
    const fixture = parseYaml(
      readFileSync(join(CONFORMANCE, "agent-targets-v1.yaml"), "utf8"),
    ) as {
      version: string;
      implicit_project_agents: string[];
      agents: Array<{
        selector: string;
        project_root: string;
        personal_root: string;
        home_override: string | null;
        override_root: string | null;
      }>;
    };
    const actual = AGENT_TARGETS.map((target) => ({
      selector: target.selector,
      project_root: target.projectRoot,
      personal_root: target.personalRoot,
      home_override: target.homeOverride,
      override_root: target.overrideRoot,
    }));
    expect(fixture.version).toBe("agent-targets-v1");
    expect(fixture.implicit_project_agents).toEqual(["codex", "claude"]);
    expect(actual).toEqual(fixture.agents);
  });

  test("matches the shared known-prior digest allowlist", () => {
    const fixture = parseYaml(
      readFileSync(join(CONFORMANCE, "known-prior-emissions-v1.yaml"), "utf8"),
    ) as { version: string; emissions: Array<{ release: string; sha256: string }> };
    expect(fixture.version).toBe("known-prior-emissions-v1");
    expect(new Set(fixture.emissions.map((item) => item.sha256))).toEqual(
      KNOWN_PRIOR_EMISSION_SHA256,
    );
  });

  test("implicit project dry-run matches the shared golden without mutation", () => {
    const repo = makeRepo();
    const nested = join(repo, "src/deep");
    mkdirSync(nested, { recursive: true });
    const { code, report } = planSkillInstall(
      { dryRun: true },
      {
        renderedSkill: renderedSkill(),
        marker: SKILL_DO_NOT_EDIT_MARKER,
        packageVersion: VERSION,
        cwd: nested,
        home: join(root, "home"),
        env: {},
      },
    );
    const expected = parseYaml(
      readFileSync(join(CONFORMANCE, "project-dry-run.golden.yaml"), "utf8")
        .replace("<version>", VERSION)
        .replaceAll("<repo>", repo.replaceAll("\\", "/")),
    ) as InstallReport;
    const normalizedReport = structuredClone(report);
    normalizedReport.base_dir = normalizedReport.base_dir.replaceAll("\\", "/");
    for (const file of normalizedReport.files) {
      file.base_dir = file.base_dir.replaceAll("\\", "/");
      file.path = file.path.replaceAll("\\", "/");
      file.resolved_path = file.resolved_path.replaceAll("\\", "/");
    }
    expect(code).toBe(0);
    expect(normalizedReport).toEqual(expected);
    expect(existsSync(join(repo, ".agents"))).toBe(false);
    expect(existsSync(join(repo, ".claude"))).toBe(false);
    expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
  });

  test("expands global agents and only the three documented overrides", () => {
    const home = join(root, "home");
    const claude = join(root, "claude-config");
    const gemini = join(root, "gemini-home");
    const copilot = join(root, "copilot-home");
    const result = resolveTargets(
      { globalScope: true, allAgents: true, dryRun: true },
      {
        cwd: root,
        home,
        env: {
          CLAUDE_CONFIG_DIR: claude,
          GEMINI_CLI_HOME: gemini,
          COPILOT_HOME: copilot,
          CODEX_HOME: join(root, "ignored-codex"),
          OPENCODE_CONFIG: join(root, "ignored-opencode.json"),
          CLINE_DATA_DIR: join(root, "ignored-cline"),
        },
      },
    );
    const destinations = Object.fromEntries(
      result.targets.map((target) => [target.agents[0], target.target]),
    );
    expect(destinations).toEqual({
      codex: join(home, ".agents/skills/softschema/SKILL.md"),
      claude: join(claude, "skills/softschema/SKILL.md"),
      gemini: join(gemini, ".gemini/skills/softschema/SKILL.md"),
      copilot: join(copilot, "skills/softschema/SKILL.md"),
      cursor: join(home, ".cursor/skills/softschema/SKILL.md"),
      windsurf: join(home, ".codeium/windsurf/skills/softschema/SKILL.md"),
      opencode: join(home, ".config/opencode/skills/softschema/SKILL.md"),
      cline: join(home, ".cline/skills/softschema/SKILL.md"),
      roo: join(home, ".roo/skills/softschema/SKILL.md"),
    });
  });

  test("deduplicates converged global destinations independently of selector order", () => {
    const home = join(root, "home");
    const env = { CLAUDE_CONFIG_DIR: join(home, ".agents") };
    const first = resolveTargets(
      { globalScope: true, agents: ["claude", "codex"] },
      { cwd: root, home, env },
    ).targets;
    const second = resolveTargets(
      { globalScope: true, agents: ["codex", "claude"] },
      { cwd: root, home, env },
    ).targets;
    expect(first).toEqual(second);
    expect(first).toHaveLength(1);
    expect(first[0]?.agents).toEqual(["claude", "codex"]);
    expect(first[0]?.target).toBe(join(home, ".agents/skills/softschema/SKILL.md"));
  });
});

describe("scope and path policy", () => {
  test("refuses ambiguous, home, root, unsupported, and unsafe invocations", () => {
    const home = join(root, "home");
    mkdirSync(home);
    expect(() => resolveTargets({}, { cwd: root, home, env: {} })).toThrow(
      "ambiguous outside a Git repository",
    );
    expect(() =>
      resolveTargets(
        { project: true, noRepoCheck: true, directory: home },
        { cwd: root, home, env: {} },
      ),
    ).toThrow("user home");
    expect(() =>
      resolveTargets(
        { project: true, noRepoCheck: true, directory: resolve(root, "/") },
        { cwd: root, home, env: {} },
      ),
    ).toThrow("filesystem root");
    expect(() =>
      resolveTargets(
        { project: true, agents: ["aider"] },
        { cwd: root, home, env: {} },
      ),
    ).toThrow("unsupported agent target");
    expect(() =>
      resolveTargets({ globalScope: true }, { cwd: root, home, env: {} }),
    ).toThrow("requires --agent");
    expect(() =>
      resolveTargets(
        { globalScope: true, agents: ["claude"] },
        { cwd: root, home, env: { CLAUDE_CONFIG_DIR: "relative" } },
      ),
    ).toThrow("absolute normalized");
  });

  test("accepts worktree and submodule .git files as independent roots", () => {
    const worktree = join(root, "worktree");
    const submodule = join(worktree, "vendor/module");
    mkdirSync(submodule, { recursive: true });
    writeFileSync(join(worktree, ".git"), "gitdir: ../repo/.git/worktrees/w\n");
    writeFileSync(join(submodule, ".git"), "gitdir: ../../.git/modules/module\n");
    expect(
      resolveTargets({}, { cwd: join(worktree, "vendor"), home: join(root, "home") })
        .primaryBase,
    ).toBe(worktree);
    expect(resolveTargets({}, { cwd: submodule, home: join(root, "home") }).primaryBase).toBe(
      submodule,
    );
  });

  test("rejects a symlink parent that escapes the selected base", () => {
    const repo = makeRepo();
    const outside = join(root, "outside");
    mkdirSync(outside);
    symlinkSync(outside, join(repo, ".cursor"), "dir");
    expect(() =>
      resolveTargets({ agents: ["cursor"] }, { cwd: repo, home: join(root, "home") }),
    ).toThrow("escapes its selected base");
  });

  test("explicit non-repo dry-run creates nothing", () => {
    const destination = join(root, "not-created");
    const { code, report } = runInstall(
      {
        project: true,
        noRepoCheck: true,
        directory: destination,
        agents: ["cursor"],
        dryRun: true,
      },
      { cwd: root },
    );
    expect(code).toBe(0);
    expect(report.files[0]?.resolved_path).toBe(
      join(destination, ".cursor/skills/softschema/SKILL.md"),
    );
    expect(existsSync(destination)).toBe(false);
  });
});

describe("ownership and transaction safety", () => {
  test("creates and then leaves the portable pair unchanged", () => {
    const repo = makeRepo();
    const first = runInstall({}, { cwd: repo });
    expect(first.code).toBe(0);
    expect(first.report.files.map((file) => file.status)).toEqual(["created", "created"]);
    const second = runInstall({}, { cwd: repo });
    expect(second.code).toBe(0);
    expect(second.report.files.map((file) => file.status)).toEqual([
      "unchanged",
      "unchanged",
    ]);
  });

  test("preflights all targets before refusing unmanaged, modified, and newer files", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    mkdirSync(resolve(target, ".."), { recursive: true });
    const desired = installSkillPayload(renderedSkill(), SKILL_DO_NOT_EDIT_MARKER);
    const cases = new Map([
      ["unmanaged", "user-owned\n"],
      ["modified-or-unknown-managed", `${desired}local edit\n`],
      ["newer-managed", desired.replace("format=f01", "format=f99")],
    ]);
    for (const [ownership, content] of cases) {
      writeFileSync(target, content);
      const result = runInstall({ dryRun: true }, { cwd: repo });
      expect(result.code).toBe(1);
      expect(result.report.files[0]?.ownership).toBe(ownership);
      expect(result.report.files[0]?.action).toBe("conflict");
      expect(existsSync(join(repo, ".claude"))).toBe(false);
    }
  });

  test("updates a byte-exact released prior emission", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    mkdirSync(resolve(target, ".."), { recursive: true });
    const prior = readFileSync(PRIOR_EMISSION);
    expect(KNOWN_PRIOR_EMISSION_SHA256.has(createHash("sha256").update(prior).digest("hex"))).toBe(
      true,
    );
    writeFileSync(target, prior);
    const result = runInstall({ agents: ["codex"] }, { cwd: repo });
    expect(result.code).toBe(0);
    expect(result.report.files[0]?.ownership).toBe("managed-prior");
    expect(result.report.files[0]?.status).toBe("updated");
    expect(readFileSync(target, "utf8")).toBe(
      installSkillPayload(renderedSkill(), SKILL_DO_NOT_EDIT_MARKER),
    );
  });

  test("an active installer lock is a non-clobbering conflict", () => {
    const repo = makeRepo();
    const lock = acquireLock(repo);
    let result: { code: number; report: InstallReport };
    try {
      result = runInstall({ agents: ["codex"], dryRun: true }, { cwd: repo });
      expect(existsSync(join(repo, LOCK_NAME))).toBe(true);
    } finally {
      releaseLock(lock);
    }
    expect(result.code).toBe(1);
    expect(result.report.files[0]?.ownership).toBe("lock-conflict");
    expect(existsSync(join(repo, ".agents"))).toBe(false);
  });

  test("never deletes an unrecognized lock file", () => {
    const repo = makeRepo();
    const lockPath = join(repo, LOCK_NAME);
    writeFileSync(lockPath, "user-owned\n");
    const result = runInstall({ agents: ["codex"], dryRun: true }, { cwd: repo });
    expect(result.code).toBe(1);
    expect(result.report.files[0]?.ownership).toBe("lock-conflict");
    expect(readFileSync(lockPath, "utf8")).toBe("user-owned\n");
  });

  test.each([true, false])(
    "reports an oversized sparse lock as a non-mutating conflict",
    (dryRun) => {
      const repo = makeRepo();
      const lockPath = join(repo, LOCK_NAME);
      writeFileSync(lockPath, "");
      truncateSync(lockPath, MAX_SKILL_LOCK_BYTES + 1);

      const result = runInstall({ agents: ["codex"], dryRun }, { cwd: repo });

      expect(result.code).toBe(1);
      expect(result.report.files[0]?.ownership).toBe("lock-conflict");
      expect(lstatSync(lockPath).size).toBe(MAX_SKILL_LOCK_BYTES + 1);
      expect(existsSync(join(repo, ".agents"))).toBe(false);
    },
  );

  test.each(["target-directory", "parent-file"])(
    "reports %s as a path conflict",
    (blocker) => {
      const repo = makeRepo();
      const target = join(repo, ".agents/skills/softschema/SKILL.md");
      if (blocker === "target-directory") mkdirSync(target, { recursive: true });
      else writeFileSync(join(repo, ".agents"), "not a directory\n");
      const result = runInstall({ agents: ["codex"], dryRun: true }, { cwd: repo });
      expect(result.code).toBe(1);
      expect(result.report.files[0]?.ownership).toBe("path-conflict");
    },
  );

  test.each([
    ["", "path-conflict", true],
    [STAGE_SUFFIX, "residue-conflict", true],
    [BACKUP_SUFFIX, "residue-conflict", true],
    ["", "path-conflict", false],
    [STAGE_SUFFIX, "residue-conflict", false],
    [BACKUP_SUFFIX, "residue-conflict", false],
  ] as const)(
    "reports an oversized %s managed-skill node as a %s conflict",
    (suffix, ownership, dryRun) => {
      const repo = makeRepo();
      const target = join(repo, ".agents/skills/softschema/SKILL.md");
      mkdirSync(resolve(target, ".."), { recursive: true });
      const hostile = `${target}${suffix}`;
      writeFileSync(hostile, "");
      truncateSync(hostile, MAX_MANAGED_SKILL_BYTES + 1);

      const result = runInstall({ agents: ["codex"], dryRun }, { cwd: repo });

      expect(result.code).toBe(1);
      expect(result.report.files[0]?.ownership).toBe(ownership);
      expect(result.report.files[0]?.action).toBe("conflict");
      expect(lstatSync(hostile).size).toBe(MAX_MANAGED_SKILL_BYTES + 1);
      expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
      if (suffix !== "") expect(existsSync(target)).toBe(false);
    },
  );

  test.each([
    ["", "path-conflict"],
    [STAGE_SUFFIX, "residue-conflict"],
    [BACKUP_SUFFIX, "residue-conflict"],
  ] as const)(
    "reports a managed-skill symlink at suffix %s as a non-mutating dry-run conflict",
    (suffix, ownership) => {
      const repo = makeRepo();
      const target = join(repo, ".agents/skills/softschema/SKILL.md");
      mkdirSync(resolve(target, ".."), { recursive: true });
      const outside = join(repo, "user-owned.md");
      writeFileSync(outside, "user-owned\n");
      const hostile = `${target}${suffix}`;
      symlinkSync(outside, hostile, "file");

      const result = runInstall({ agents: ["codex"], dryRun: true }, { cwd: repo });

      expect(result.code).toBe(1);
      expect(result.report.files[0]?.ownership).toBe(ownership);
      expect(lstatSync(hostile).isSymbolicLink()).toBe(true);
      expect(readFileSync(outside, "utf8")).toBe("user-owned\n");
      expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
    },
  );

  test("acquires independent global bases in sorted order", () => {
    const home = join(root, "z-home");
    const claude = join(root, "a-claude");
    const seen: string[] = [];
    const result = runInstall(
      { globalScope: true, agents: ["codex", "claude"] },
      {
        cwd: root,
        home,
        env: { CLAUDE_CONFIG_DIR: claude },
        faultInjector: (boundary) => {
          if (boundary.startsWith("after-lock:")) seen.push(boundary.slice("after-lock:".length));
        },
      },
    );
    expect(result.code).toBe(0);
    expect(seen).toEqual([claude, home].sort());
  });

  test.each([
    ["after-stage:", 1],
    ["after-stage:", 2],
    ["after-replace:", 1],
    ["after-replace:", 2],
  ])("rolls back all staged targets after %s failure %i", (prefix, failOn) => {
      const repo = makeRepo();
      let calls = 0;
      expect(() =>
        runInstall(
          {},
          {
            cwd: repo,
            faultInjector: (boundary) => {
              if (boundary.startsWith(prefix)) {
                calls += 1;
                if (calls === failOn) throw new Error("injected failure");
              }
            },
          },
        ),
      ).toThrow(SkillInstallExecutionError);
      for (const relativePath of [
        ".agents/skills/softschema/SKILL.md",
        ".claude/skills/softschema/SKILL.md",
      ]) {
        const target = join(repo, relativePath);
        expect(existsSync(target)).toBe(false);
        expect(existsSync(`${target}${STAGE_SUFFIX}`)).toBe(false);
        expect(existsSync(`${target}${BACKUP_SUFFIX}`)).toBe(false);
      }
      expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
  });

  test.each([
    "after-lock:",
    "after-revalidate",
    "after-stage-all",
    "after-pre-replace-revalidate",
    "before-cleanup",
  ])(
    "rolls back a %s control-boundary failure",
    (boundary) => {
      const repo = makeRepo();
      expect(() =>
        runInstall(
          {},
          {
            cwd: repo,
            faultInjector: (observed) => {
              if (observed.startsWith(boundary)) throw new Error("injected failure");
            },
          },
        ),
      ).toThrow(SkillInstallExecutionError);
      expect(existsSync(join(repo, ".agents"))).toBe(false);
      expect(existsSync(join(repo, ".claude"))).toBe(false);
      expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
    },
  );

  test("restores the prior emission after an after-backup failure", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    mkdirSync(resolve(target, ".."), { recursive: true });
    const prior = readFileSync(PRIOR_EMISSION);
    writeFileSync(target, prior);
    expect(() =>
      runInstall(
        { agents: ["codex"] },
        {
          cwd: repo,
          faultInjector: (boundary) => {
            if (boundary.startsWith("after-backup:")) throw new Error("injected failure");
          },
        },
      ),
    ).toThrow(SkillInstallExecutionError);
    expect(readFileSync(target)).toEqual(prior);
    expect(existsSync(`${target}${STAGE_SUFFIX}`)).toBe(false);
    expect(existsSync(`${target}${BACKUP_SUFFIX}`)).toBe(false);
    expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
  });

  test("pre-replace revalidation preserves a raced user file", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    const result = runInstall(
      { agents: ["codex"] },
      {
        cwd: repo,
        faultInjector: (boundary) => {
          if (boundary === "after-stage-all") writeFileSync(target, "raced after staging\n");
        },
      },
    );
    expect(result.code).toBe(1);
    expect(result.report.files[0]?.ownership).toBe("unmanaged");
    expect(readFileSync(target, "utf8")).toBe("raced after staging\n");
    expect(existsSync(`${target}${STAGE_SUFFIX}`)).toBe(false);
    expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
  });

  test("committed cleanup failure leaves repairable, not rolled-back, state", () => {
    const repo = makeRepo();
    const targets = [
      join(repo, ".agents/skills/softschema/SKILL.md"),
      join(repo, ".claude/skills/softschema/SKILL.md"),
    ];
    const prior = readFileSync(PRIOR_EMISSION);
    for (const target of targets) {
      mkdirSync(resolve(target, ".."), { recursive: true });
      writeFileSync(target, prior);
    }
    let calls = 0;
    expect(() =>
      runInstall(
        {},
        {
          cwd: repo,
          faultInjector: (boundary) => {
            if (boundary.startsWith("after-backup-cleanup:")) {
              calls += 1;
              if (calls === 1) throw new Error("injected cleanup failure");
            }
          },
        },
      ),
    ).toThrow("committed but cleanup left recoverable residue");
    const desired = installSkillPayload(renderedSkill(), SKILL_DO_NOT_EDIT_MARKER);
    expect(targets.every((target) => readFileSync(target, "utf8") === desired)).toBe(true);
    expect(targets.filter((target) => existsSync(`${target}${BACKUP_SUFFIX}`))).toHaveLength(1);

    expect(runInstall({}, { cwd: repo }).code).toBe(0);
    expect(targets.every((target) => !existsSync(`${target}${BACKUP_SUFFIX}`))).toBe(true);
  });

  test("repairs killed-process residue and a stale lock idempotently", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    mkdirSync(resolve(target, ".."), { recursive: true });
    writeFileSync(target, readFileSync(PRIOR_EMISSION));
    writeFileSync(`${target}${STAGE_SUFFIX}`, installSkillPayload(renderedSkill(), SKILL_DO_NOT_EDIT_MARKER));
    renameSync(target, `${target}${BACKUP_SUFFIX}`);
    writeFileSync(
      join(repo, LOCK_NAME),
      JSON.stringify({ format: "softschema-skill-lock-v1", pid: 2147483647 }),
    );

    const result = runInstall({ agents: ["codex"] }, { cwd: repo });
    expect(result.code).toBe(0);
    expect(readFileSync(target, "utf8")).toBe(
      installSkillPayload(renderedSkill(), SKILL_DO_NOT_EDIT_MARKER),
    );
    expect(existsSync(`${target}${STAGE_SUFFIX}`)).toBe(false);
    expect(existsSync(`${target}${BACKUP_SUFFIX}`)).toBe(false);
    expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
    expect(runInstall({ agents: ["codex"] }, { cwd: repo }).report.files[0]?.status).toBe(
      "unchanged",
    );
  });

  test("dry-run does not repair existing recoverable residue", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    mkdirSync(resolve(target, ".."), { recursive: true });
    writeFileSync(`${target}${BACKUP_SUFFIX}`, readFileSync(PRIOR_EMISSION));
    writeFileSync(
      `${target}${STAGE_SUFFIX}`,
      installSkillPayload(renderedSkill(), SKILL_DO_NOT_EDIT_MARKER),
    );
    const result = runInstall({ agents: ["codex"], dryRun: true }, { cwd: repo });
    expect(result.code).toBe(0);
    expect(existsSync(target)).toBe(false);
    expect(readFileSync(`${target}${BACKUP_SUFFIX}`)).toEqual(readFileSync(PRIOR_EMISSION));
    expect(existsSync(`${target}${STAGE_SUFFIX}`)).toBe(true);
    expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
  });

  test("reports an oversized stage raced into repair without mutating residue", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    mkdirSync(resolve(target, ".."), { recursive: true });
    const prior = readFileSync(PRIOR_EMISSION);
    writeFileSync(`${target}${BACKUP_SUFFIX}`, prior);
    writeFileSync(
      `${target}${STAGE_SUFFIX}`,
      installSkillPayload(renderedSkill(), SKILL_DO_NOT_EDIT_MARKER),
    );

    const result = runInstall(
      { agents: ["codex"] },
      {
        cwd: repo,
        faultInjector: (boundary) => {
          if (boundary === "after-revalidate") {
            truncateSync(`${target}${STAGE_SUFFIX}`, MAX_MANAGED_SKILL_BYTES + 1);
          }
        },
      },
    );

    expect(result.code).toBe(1);
    expect(result.report.files[0]?.ownership).toBe("residue-conflict");
    expect(existsSync(target)).toBe(false);
    expect(readFileSync(`${target}${BACKUP_SUFFIX}`)).toEqual(prior);
    expect(lstatSync(`${target}${STAGE_SUFFIX}`).size).toBe(MAX_MANAGED_SKILL_BYTES + 1);
    expect(existsSync(join(repo, LOCK_NAME))).toBe(false);
  });

  test("revalidates after locks and preserves a raced user file", () => {
    const repo = makeRepo();
    const target = join(repo, ".agents/skills/softschema/SKILL.md");
    const result = runInstall(
      { agents: ["codex"] },
      {
        cwd: repo,
        faultInjector: (boundary) => {
          if (boundary.startsWith("after-lock:")) {
            mkdirSync(resolve(target, ".."), { recursive: true });
            writeFileSync(target, "raced\n");
          }
        },
      },
    );
    expect(result.code).toBe(1);
    expect(result.report.files[0]?.ownership).toBe("unmanaged");
    expect(result.report.files[0]?.action).toBe("conflict");
    expect(readFileSync(target, "utf8")).toBe("raced\n");
  });
});

test("stable text plan includes scope, table, action, ownership, and canonical path", () => {
  const repo = makeRepo();
  const result = runInstall({ dryRun: true, agents: ["cursor"] }, { cwd: repo });
  expect(formatInstallPlanText(result.report)).toBe(
    `softschema skill install (project, agent-targets-v1)\n` +
      `base: ${repo}\n` +
      `dry-run: yes\n` +
      `create    absent                      cursor       ${join(repo, ".cursor/skills/softschema/SKILL.md")}`,
  );
});

test("usage errors use the installer error type", () => {
  expect(() => resolveTargets({}, { cwd: root, home: join(root, "home") })).toThrow(
    SkillInstallUsageError,
  );
});
