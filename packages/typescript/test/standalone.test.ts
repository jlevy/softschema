/**
 * Docs/skill resources must be BUNDLED in the package, not read from the working
 * directory. This runs the built CLI from a temp dir OUTSIDE the repo: if the CLI
 * depended on cwd (the original bug) these would fail with "resource not found".
 *
 * beforeAll builds the package so the test is self-contained regardless of run order.
 */
import { spawnSync } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { beforeAll, describe, expect, test } from "bun:test";

const PACKAGE_ROOT = resolve(import.meta.dir, "..");
const CLI = join(PACKAGE_ROOT, "dist", "cli.js");
const MOVIE_MODEL = join(PACKAGE_ROOT, "test", "fixtures", "movie-model.mjs");

interface RunResult {
  status: number | null;
  stdout: string;
  stderr: string;
}

function runFromTmp(args: string[], files: Record<string, string> = {}): RunResult {
  const cwd = mkdtempSync(join(tmpdir(), "softschema-standalone-"));
  for (const [name, content] of Object.entries(files)) {
    writeFileSync(join(cwd, name), content);
  }
  const r = spawnSync("bun", [CLI, ...args], { cwd, encoding: "utf8" });
  return { status: r.status, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

/** Run a copied package from inside a consumer repo with colliding resource paths. */
function runFromAdversarialInstall(args: string[], files: Record<string, string>): RunResult {
  const cwd = mkdtempSync(join(tmpdir(), "softschema-consumer-"));
  const installed = join(cwd, "node_modules", "softschema");
  mkdirSync(installed, { recursive: true });
  cpSync(join(PACKAGE_ROOT, "dist"), join(installed, "dist"), { recursive: true });
  cpSync(join(PACKAGE_ROOT, "resources"), join(installed, "resources"), { recursive: true });
  writeFileSync(join(installed, "package.json"), '{"name":"softschema","type":"module"}\n');
  symlinkSync(
    join(PACKAGE_ROOT, "node_modules"),
    join(installed, "node_modules"),
    process.platform === "win32" ? "junction" : "dir",
  );
  for (const [name, content] of Object.entries(files)) {
    const target = join(cwd, name);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, content);
  }
  const r = spawnSync("node", [join(installed, "dist", "cli.js"), ...args], {
    cwd,
    encoding: "utf8",
  });
  return { status: r.status, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

/** Run a built CLI from the repository's exact source-checkout package layout. */
function runFromExactCheckout(args: string[], files: Record<string, string>): RunResult {
  const cwd = mkdtempSync(join(tmpdir(), "softschema-checkout-"));
  const packageRoot = join(cwd, "packages", "typescript");
  mkdirSync(packageRoot, { recursive: true });
  cpSync(join(PACKAGE_ROOT, "dist"), join(packageRoot, "dist"), { recursive: true });
  cpSync(join(PACKAGE_ROOT, "resources"), join(packageRoot, "resources"), { recursive: true });
  symlinkSync(
    join(PACKAGE_ROOT, "node_modules"),
    join(packageRoot, "node_modules"),
    process.platform === "win32" ? "junction" : "dir",
  );
  writeFileSync(join(cwd, "pyproject.toml"), "[project]\nname = 'softschema'\n");
  const pythonMarker = join(cwd, "packages", "python", "src", "softschema", "cli.py");
  mkdirSync(dirname(pythonMarker), { recursive: true });
  writeFileSync(pythonMarker, "# checkout marker\n");
  for (const [name, content] of Object.entries(files)) {
    const target = join(cwd, name);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, content);
  }
  const r = spawnSync("node", [join(packageRoot, "dist", "cli.js"), ...args], {
    cwd,
    encoding: "utf8",
  });
  return { status: r.status, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

describe("bundled resources (standalone, outside the repo)", () => {
  // Building can exceed Bun's default hook timeout on a cold cache or loaded machine,
  // so the hook gets an explicit generous timeout.
  beforeAll(() => {
    const build = spawnSync("bun", ["run", "build"], { cwd: PACKAGE_ROOT, encoding: "utf8" });
    if (build.status !== 0) throw new Error(`build failed: ${build.stderr}`);
  }, 120_000);

  test("--help points agents to repo-local skill install", () => {
    const r = runFromTmp(["--help"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("IMPORTANT for agents");
    expect(r.stdout).toContain("repo root");
    expect(r.stdout).toContain("skill --install");
    expect(r.stdout).toContain("uvx --from 'softschema==0.2.2' softschema");
    expect(r.stdout).toContain("npx --yes softschema@0.2.2");
    expect(r.stdout).toContain("bunx --bun softschema@0.2.2");
  });

  test("--version prints 'softschema <version>'", () => {
    const r = runFromTmp(["--version"]);
    expect(r.status).toBe(0);
    expect(r.stdout.trim()).toMatch(/^softschema \d[\w.+-]*$/);
  });

  test("doctor --json reports Node when the package runs under Node", () => {
    const r = runFromAdversarialInstall(["doctor", "--json"], {});
    expect(r.status).toBe(0);
    const report = JSON.parse(r.stdout) as {
      protocol_version: string;
      runtime: { name: string; version: string };
      capabilities: { model_loaders: string[] };
    };
    expect(report.protocol_version).toBe("1");
    expect(report.runtime.name).toBe("node");
    expect(report.runtime.version).toMatch(/^\d+\.\d+/);
    expect(report.capabilities.model_loaders).toEqual(["json-schema", "zod"]);
  });

  test("docs guide reads the bundled resource, not a cwd-relative file", () => {
    const r = runFromTmp(["docs", "guide"]);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("# softschema Guide");
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

  test("installed docs and skills ignore colliding consumer-repository files", () => {
    const guide = runFromAdversarialInstall(["docs", "guide"], {
      "docs/softschema-guide.md": "# MALICIOUS CONSUMER GUIDE\n",
    });
    expect(guide.status).toBe(0);
    expect(guide.stdout).toContain("# softschema Guide");
    expect(guide.stdout).not.toContain("MALICIOUS CONSUMER GUIDE");

    const skill = runFromAdversarialInstall(["skill"], {
      "skills/softschema/SKILL.md": "# MALICIOUS CONSUMER SKILL\n",
    });
    expect(skill.status).toBe(0);
    expect(skill.stdout).toContain("# softschema Skill");
    expect(skill.stdout).not.toContain("MALICIOUS CONSUMER SKILL");
  });

  test("exact source-checkout layout prefers live resources over the bundle", () => {
    const skill = runFromExactCheckout(["skill"], {
      "skills/softschema/SKILL.md": "# LIVE SOURCE SKILL\n",
    });
    expect(skill.status).toBe(0);
    expect(skill.stdout).toBe("# LIVE SOURCE SKILL\n");
  });
});

describe("CLI error handling (stable exit codes, no stack traces)", () => {
  const BAD_FRONTMATTER = "---\nfoo: [unclosed\nbar: 1\n---\nbody\n";

  test("validate on malformed frontmatter YAML exits 1 with a parse record", () => {
    const r = runFromTmp(
      ["validate", "doc.md", "--schema", "s.yaml", "--contract", "x:Y/v1", "--envelope", "foo"],
      { "doc.md": BAD_FRONTMATTER },
    );
    expect(r.status).toBe(1);
    expect(r.stderr).toBe("");
    expect(JSON.parse(r.stdout)).toMatchObject({ kind: "parse_error", reason: "syntax" });
    expect(r.stderr).not.toMatch(/\n\s+at /);
  });

  test("validate with a non-Zod --model export exits 2", () => {
    const r = runFromTmp(
      ["validate", "doc.md", "--model", "model.js:NotASchema", "--contract", "x:Y/v1"],
      {
      "doc.md": "---\nname: hi\n---\n",
      "model.js": "export const NotASchema = { not: 'zod' };\n",
      },
    );
    expect(r.status).toBe(2);
    expect(r.stderr).toContain("is not a Zod schema");
  });

  test("the built Node CLI imports .mjs models whose paths need URL encoding", () => {
    const moduleName = "model path #100%.mjs";
    const r = runFromAdversarialInstall(
      [
        "validate",
        "doc.md",
        "--model",
        `${moduleName}:MoviePage`,
        "--contract",
        "x:Y/v1",
        "--envelope",
        "data",
      ],
      {
        "doc.md": "---\ndata:\n  title: ok\n---\n",
        [moduleName]:
          `export { MoviePage } from ${JSON.stringify(pathToFileURL(MOVIE_MODEL).href)};\n`,
      },
    );
    expect(r.status).toBe(0);
    expect(r.stderr).toBe("");
  });

  test("the built Node CLI rejects direct .ts models with an actionable error", () => {
    const r = runFromAdversarialInstall(
      ["validate", "doc.md", "--model", "model.ts:MoviePage", "--contract", "x:Y/v1"],
      {
        "doc.md": "---\ndata:\n  title: ok\n---\n",
        "model.ts": "export const MoviePage = {};\n",
      },
    );
    expect(r.status).toBe(2);
    expect(r.stderr).toContain("compile it to .js or .mjs, or run softschema with Bun");
    expect(r.stderr).not.toMatch(/\n\s+at /);
  });

  test("inspect on malformed frontmatter YAML exits 2 without a stack trace", () => {
    const r = runFromTmp(["inspect", "doc.md"], { "doc.md": BAD_FRONTMATTER });
    expect(r.status).toBe(2);
    expect(r.stderr).toContain("softschema inspect:");
    expect(r.stderr).not.toMatch(/\n\s+at /);
  });
});
