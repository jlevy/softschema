/**
 * Docs/skill resources must be BUNDLED in the package, not read from the working
 * directory. This runs the built CLI from a temp dir OUTSIDE the repo: if the CLI
 * depended on cwd (the original bug) these would fail with "resource not found".
 *
 * beforeAll builds the package so the test is self-contained regardless of run order.
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { beforeAll, describe, expect, test } from "bun:test";

const PACKAGE_ROOT = resolve(import.meta.dir, "..");
const CLI = join(PACKAGE_ROOT, "dist", "cli.js");

function runFromTmp(args: string[]): { status: number | null; stdout: string } {
  const cwd = mkdtempSync(join(tmpdir(), "softschema-standalone-"));
  const r = spawnSync("bun", [CLI, ...args], { cwd, encoding: "utf8" });
  return { status: r.status, stdout: r.stdout ?? "" };
}

describe("bundled resources (standalone, outside the repo)", () => {
  beforeAll(() => {
    const build = spawnSync("bun", ["run", "build"], { cwd: PACKAGE_ROOT, encoding: "utf8" });
    if (build.status !== 0) throw new Error(`build failed: ${build.stderr}`);
  });

  test("docs guide reads the bundled resource, not a cwd-relative file", () => {
    const r = runFromTmp(["docs", "guide"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("# Softschema Guide");
  });

  test("docs spec works from outside the repo", () => {
    const r = runFromTmp(["docs", "spec"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("# Softschema Spec");
  });

  test("docs --list --json works from outside the repo", () => {
    const r = runFromTmp(["docs", "--list", "--json"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain('"name": "guide"');
  });
});
