/**
 * skill --install behavior: run main(["skill","--install"]) in a temp dir and assert
 * both mirror files are created with the DO NOT EDIT marker; a second run reports
 * status "unchanged" for both.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { main, SKILL_DO_NOT_EDIT_MARKER, SKILL_INSTALL_TARGETS } from "../src/cli.js";

let tempDir: string;
let originalCwd: string;
let originalWrite: typeof process.stdout.write;
let originalErrorWrite: typeof process.stderr.write;
let stdout: string;
let stderr: string;

beforeEach(() => {
  tempDir = mkdtempSync(join(tmpdir(), "softschema-skill-install-"));
  mkdirSync(join(tempDir, ".git"));
  originalCwd = process.cwd();
  process.chdir(tempDir);
  originalWrite = process.stdout.write.bind(process.stdout);
  originalErrorWrite = process.stderr.write.bind(process.stderr);
  stdout = "";
  stderr = "";
  process.stdout.write = ((chunk: string | Uint8Array) => {
    stdout += chunk.toString();
    return true;
  }) as typeof process.stdout.write;
  process.stderr.write = ((chunk: string | Uint8Array) => {
    stderr += chunk.toString();
    return true;
  }) as typeof process.stderr.write;
});

afterEach(() => {
  process.stdout.write = originalWrite;
  process.stderr.write = originalErrorWrite;
  process.chdir(originalCwd);
  rmSync(tempDir, { recursive: true, force: true });
});

const argv = (...args: string[]) => ["node", "cli.js", ...args];

describe("skill --install", () => {
  test("creates both mirror files with DO NOT EDIT marker", async () => {
    const code = await main(argv("skill", "--install"));
    expect(code).toBe(0);

    const result = JSON.parse(stdout) as {
      version: string;
      base_dir: string;
      files: { path: string; status: string }[];
    };

    expect(result.files).toHaveLength(2);
    for (const file of result.files) {
      expect(file.status).toBe("created");
      const fullPath = join(tempDir, file.path);
      expect(existsSync(fullPath)).toBe(true);
      const content = readFileSync(fullPath, "utf8");
      expect(content).toContain(SKILL_DO_NOT_EDIT_MARKER.trimEnd());
    }

    // Verify the targets match SKILL_INSTALL_TARGETS
    const paths = result.files.map((f) => f.path);
    for (const target of SKILL_INSTALL_TARGETS) {
      expect(paths).toContain(target);
    }
  });

  test("second run reports unchanged for both files", async () => {
    // First run: create files.
    await main(argv("skill", "--install"));
    stdout = "";

    // Second run: should be unchanged.
    const code = await main(argv("skill", "--install"));
    expect(code).toBe(0);

    const result = JSON.parse(stdout) as {
      version: string;
      base_dir: string;
      files: { path: string; status: string }[];
    };

    expect(result.files).toHaveLength(2);
    for (const file of result.files) {
      expect(file.status).toBe("unchanged");
    }
  });

  test("text dry-run uses an explicit agent without mutation", async () => {
    const code = await main(
      argv(
        "skill",
        "--install",
        "--dry-run",
        "--agent",
        "cursor",
        "--agent",
        "roo",
        "--text",
      ),
    );
    expect(code).toBe(0);
    const portableStdout = stdout.replaceAll("\\", "/");
    expect(portableStdout).toContain("softschema skill install (project, agent-targets-v1)");
    expect(portableStdout).toContain(".cursor/skills/softschema/SKILL.md");
    expect(portableStdout).toContain(".roo/skills/softschema/SKILL.md");
    expect(portableStdout).not.toContain(".agents/skills");
    expect(existsSync(join(tempDir, ".cursor"))).toBe(false);
    expect(existsSync(join(tempDir, ".roo"))).toBe(false);
  });

  test("ambiguous location exits two without mutation", async () => {
    rmSync(join(tempDir, ".git"), { recursive: true });
    const code = await main(argv("skill", "--install"));
    expect(code).toBe(2);
    expect(stdout).toBe("");
    expect(stderr).toContain("scope is ambiguous outside a Git repository");
    expect(existsSync(join(tempDir, ".agents"))).toBe(false);
    expect(existsSync(join(tempDir, ".claude"))).toBe(false);
  });
});
