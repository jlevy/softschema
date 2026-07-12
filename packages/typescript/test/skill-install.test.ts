/**
 * skill --install behavior: run main(["skill","--install"]) in a temp dir and assert
 * both mirror files are created with the DO NOT EDIT marker; a second run reports
 * status "unchanged" for both.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { main, SKILL_INSTALL_TARGETS } from "../src/cli.js";

let tempDir: string;
let originalCwd: string;
let originalWrite: typeof process.stdout.write;
let stdout: string;

beforeEach(() => {
  tempDir = mkdtempSync(join(tmpdir(), "softschema-skill-install-"));
  originalCwd = process.cwd();
  process.chdir(tempDir);
  originalWrite = process.stdout.write.bind(process.stdout);
  stdout = "";
  process.stdout.write = ((chunk: string | Uint8Array) => {
    stdout += chunk.toString();
    return true;
  }) as typeof process.stdout.write;
});

afterEach(() => {
  process.stdout.write = originalWrite;
  process.chdir(originalCwd);
  rmSync(tempDir, { recursive: true, force: true });
});

const argv = (...args: string[]) => ["node", "cli.js", ...args];

describe("skill --install", () => {
  const installArgs = [
    "skill",
    "--install",
    "--scope",
    "project",
    "--agent",
    "portable",
    "--agent",
    "claude",
  ];

  test("creates both mirror files with DO NOT EDIT marker", async () => {
    const code = await main(argv(...installArgs));
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
      expect(content).toContain("DO NOT EDIT format=f02 source-sha256=");
    }

    // Verify the targets match SKILL_INSTALL_TARGETS
    const paths = result.files.map((f) => f.path);
    for (const target of Object.values(SKILL_INSTALL_TARGETS)) {
      expect(paths).toContain(target);
    }
  });

  test("second run reports unchanged for both files", async () => {
    // First run: create files.
    await main(argv(...installArgs));
    stdout = "";

    // Second run: should be unchanged.
    const code = await main(argv(...installArgs));
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

  test("dry-run previews and unmanaged files are refused", async () => {
    expect(await main(argv(...installArgs.slice(0, 6), "--dry-run"))).toBe(0);
    const preview = JSON.parse(stdout);
    expect(preview.files[0].status).toBe("would_create");
    expect(existsSync(join(tempDir, preview.files[0].path))).toBe(false);

    stdout = "";
    const target = join(tempDir, SKILL_INSTALL_TARGETS.portable);
    mkdirSync(join(tempDir, ".agents/skills/softschema"), { recursive: true });
    writeFileSync(target, "unmanaged\n");
    expect(await main(argv(...installArgs.slice(0, 6)))).toBe(2);
    expect(readFileSync(target, "utf8")).toBe("unmanaged\n");
  });
});
