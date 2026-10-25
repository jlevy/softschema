/**
 * Docs/skill resources must be BUNDLED in the package, not read from the working
 * directory. This runs the built CLI from a temp dir OUTSIDE the repo: if the CLI
 * depended on cwd (the original bug) these would fail with "resource not found".
 *
 * The file builds a private copy of the package (see `built-package.ts`), so the test is
 * self-contained regardless of run order and never rewrites the shared `dist/`.
 */
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, setDefaultTimeout, test } from "bun:test";
import { SPAWN_TEST_TIMEOUT_MS, usePrivateBuild } from "./built-package.js";

setDefaultTimeout(SPAWN_TEST_TIMEOUT_MS);
const builtRoot = usePrivateBuild();

interface RunResult {
  status: number | null;
  stdout: string;
  stderr: string;
}

function runFromTmp(args: string[], files: Record<string, string> = {}): RunResult {
  const cwd = mkdtempSync(join(tmpdir(), "softschema-standalone-"));
  for (const [name, content] of Object.entries(files)) {
    mkdirSync(resolve(cwd, name, ".."), { recursive: true });
    writeFileSync(join(cwd, name), content);
  }
  const cli = join(builtRoot(), "dist", "cli.js");
  const r = spawnSync("bun", [cli, ...args], { cwd, encoding: "utf8" });
  return { status: r.status, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

describe("bundled resources (standalone, outside the repo)", () => {
  test("--help points agents to repo-local skill install", () => {
    const r = runFromTmp(["--help"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("IMPORTANT for agents");
    expect(r.stdout).toContain("repo root");
    expect(r.stdout).toContain("skill --install");
    expect(r.stdout).toContain("uvx softschema@latest");
    expect(r.stdout).toContain("npx -y softschema@latest");
  });

  test("--version prints the package version and implementation", () => {
    const r = runFromTmp(["--version"]);
    expect(r.status).toBe(0);
    expect(r.stdout.trim()).toMatch(/^softschema \d[\w.+-]* \(TypeScript\)$/);
  });

  test("docs guide reads the bundled resource, not a cwd-relative file", () => {
    const r = runFromTmp(["docs", "guide"], { "docs/softschema-guide.md": "COLLISION\n" });
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("# softschema Guide");
    expect(r.stdout).not.toContain("COLLISION");
  });

  test("docs spec works from outside the repo", () => {
    const r = runFromTmp(["docs", "spec"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("# softschema Spec");
  });

  test("docs --list --json works from outside the repo", () => {
    const r = runFromTmp(["docs", "--list", "--json"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain('"name": "guide"');
  });
});

describe("CLI error handling (stable exit codes, no stack traces)", () => {
  const BAD_FRONTMATTER = "---\nfoo: [unclosed\nbar: 1\n---\nbody\n";

  test("validate on malformed frontmatter YAML exits 2 without a stack trace", () => {
    const r = runFromTmp(
      ["validate", "doc.md", "--schema", "s.yaml", "--contract", "x:Y/v1", "--envelope", "foo"],
      { "doc.md": BAD_FRONTMATTER },
    );
    expect(r.status).toBe(2);
    expect(r.stderr).toContain("softschema validate:");
    expect(r.stderr).not.toMatch(/\n\s+at /);
  });

  test("validate with a non-Zod --model export exits 2", () => {
    const r = runFromTmp(["validate", "doc.md", "--model", "model.js:NotASchema"], {
      "doc.md": "---\nname: hi\n---\n",
      "model.js": "export const NotASchema = { not: 'zod' };\n",
    });
    expect(r.status).toBe(2);
    expect(r.stderr).toContain("is not a Zod schema");
  });

  test("inspect on malformed frontmatter YAML exits 2 without a stack trace", () => {
    const r = runFromTmp(["inspect", "doc.md"], { "doc.md": BAD_FRONTMATTER });
    expect(r.status).toBe(2);
    expect(r.stderr).toContain("softschema inspect:");
    expect(r.stderr).not.toMatch(/\n\s+at /);
  });
});
