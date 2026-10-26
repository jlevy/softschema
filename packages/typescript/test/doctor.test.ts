/**
 * `doctor`: which runners the caller has, and the prefix it recommends.
 *
 * Each scenario lays fake executables out under a temporary directory and injects the
 * search path and the path softschema runs from, so no test depends on what is
 * installed. The Python suite (`packages/python/tests/test_doctor.py`) runs the same
 * scenarios and expects the same reports.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { chmodSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { doctorReport, doctorText, ephemeralRunner, main } from "../src/cli.js";

// The layouts `uvx` and `npx` really create: each prepends the throwaway environment's
// bin directory to the PATH of the softschema it starts.
const UV_CACHE = ".cache/uv";
const UVX_ENV = `${UV_CACHE}/archive-v0/V9O-H0OPJjiVa81e`;
const UVX_BIN = `${UVX_ENV}/bin`;
const UVX_MODULE = `${UVX_ENV}/lib/python3.14/site-packages/softschema/cli.py`;
const NPX_ENV = ".npm/_npx/be80e5187394a449/node_modules";
const NPX_BIN = `${NPX_ENV}/.bin`;
const NPX_MODULE = `${NPX_ENV}/softschema/dist/cli.js`;
const INSTALLED_BIN = "usr/local/bin";
const TOOLS_BIN = "opt/tools/bin";
const SOURCE_MODULE = "src/softschema/cli.py";

let root = "";

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "softschema-doctor-"));
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

/** Create a file `name` in `dir` that PATH lookup accepts as an executable. */
function executable(dir: string, name: string): string {
  mkdirSync(join(root, dir), { recursive: true });
  const path = join(root, dir, name);
  writeFileSync(path, "#!/bin/sh\n");
  chmodSync(path, 0o755);
  return path;
}

/** Mark `dir` as a cache root, as uv marks its own. */
function tagCache(dir: string): void {
  mkdirSync(join(root, dir), { recursive: true });
  writeFileSync(join(root, dir, "CACHEDIR.TAG"), "Signature: 8a477f597d28d172789f06886806bc55\n");
}

const searchPath = (...dirs: string[]) => dirs.map((dir) => join(root, dir)).join(delimiter);

const report = (running: string, ...dirs: string[]) =>
  doctorReport({ pathValue: searchPath(...dirs), runningPath: join(root, running) });

const runners = (paths: { softschema: string | null; uvx: string | null; npx: string | null }) =>
  (["softschema", "uvx", "npx"] as const).map((name) => ({
    name,
    available: paths[name] !== null,
    path: paths[name],
  }));

describe("doctor recommendation", () => {
  test("an installed softschema on PATH is recommended", () => {
    const softschema = executable(INSTALLED_BIN, "softschema");
    const uvx = executable(TOOLS_BIN, "uvx");
    const npx = executable(TOOLS_BIN, "npx");

    const result = report(SOURCE_MODULE, INSTALLED_BIN, TOOLS_BIN);

    expect(result.runners).toEqual(runners({ softschema, uvx, npx }));
    expect(result.recommended_invocation).toBe("softschema");
  });

  test("a uvx environment recommends uvx, not its own softschema", () => {
    tagCache(UV_CACHE);
    executable(UVX_BIN, "softschema");
    const uvx = executable(TOOLS_BIN, "uvx");
    const npx = executable(TOOLS_BIN, "npx");

    const result = report(UVX_MODULE, UVX_BIN, TOOLS_BIN);

    expect(result.runners).toEqual(runners({ softschema: null, uvx, npx }));
    expect(result.recommended_invocation).toBe("uvx softschema@latest");
  });

  test("the npx cache recommends npx, not its own softschema", () => {
    executable(NPX_BIN, "softschema");
    const uvx = executable(TOOLS_BIN, "uvx");
    const npx = executable(TOOLS_BIN, "npx");

    const result = report(NPX_MODULE, NPX_BIN, TOOLS_BIN);

    // The runner that started softschema wins over the skill's uvx-first fallback.
    expect(result.runners).toEqual(runners({ softschema: null, uvx, npx }));
    expect(result.recommended_invocation).toBe("npx -y softschema@latest");
  });

  test("an installed softschema wins over the runner that started it", () => {
    tagCache(UV_CACHE);
    executable(UVX_BIN, "softschema");
    const softschema = executable(INSTALLED_BIN, "softschema");
    const uvx = executable(TOOLS_BIN, "uvx");

    const result = report(UVX_MODULE, UVX_BIN, INSTALLED_BIN, TOOLS_BIN);

    expect(result.runners).toEqual(runners({ softschema, uvx, npx: null }));
    expect(result.recommended_invocation).toBe("softschema");
  });

  test("neither installed nor ephemeral falls back to the first runner", () => {
    const npx = executable(TOOLS_BIN, "npx");

    const result = report(SOURCE_MODULE, TOOLS_BIN);

    expect(result.runners).toEqual(runners({ softschema: null, uvx: null, npx }));
    expect(result.recommended_invocation).toBe("npx -y softschema@latest");
  });

  test("a runner missing from PATH is not recommended", () => {
    tagCache(UV_CACHE);
    executable(UVX_BIN, "softschema");
    const npx = executable(TOOLS_BIN, "npx");

    // Started by a uvx the caller's PATH does not have, e.g. one run by absolute path.
    const result = report(UVX_MODULE, UVX_BIN, TOOLS_BIN);
    expect(result.runners).toEqual(runners({ softschema: null, uvx: null, npx }));
    expect(result.recommended_invocation).toBe("npx -y softschema@latest");

    expect(report(UVX_MODULE, UVX_BIN).recommended_invocation).toBeNull();
  });

  test("an install under a directory named like a cache is found", () => {
    const softschema = executable("opt/archive-v0/bin", "softschema");

    const result = report(SOURCE_MODULE, "opt/archive-v0/bin");

    expect(result.runners).toEqual(runners({ softschema, uvx: null, npx: null }));
    expect(result.recommended_invocation).toBe("softschema");
  });

  test.each<[string, string | null, "uvx" | "npx" | null]>([
    [".cache/uv/archive-v0/V9O-H0OPJjiVa81e/bin/softschema", ".cache/uv", "uvx"],
    ["_temp/setup-uv-cache/builds-v0/.tmpAbc/bin", "_temp/setup-uv-cache", "uvx"],
    [".cache/uv/environments-v2/0413/f9c7/bin/softschema", ".cache/uv", "uvx"],
    ["opt/archive-v0/bin/softschema", null, null],
    ["opt/cache/archive-v0/x/bin", "opt", null],
    [".npm/_npx/be80e5187394a449/node_modules/softschema/dist/cli.js", null, "npx"],
    ["opt/_npx/bin/softschema", null, null],
    [".local/share/uv/tools/softschema/bin/softschema", null, null],
    ["home/archive-v0-notes/softschema/cli.py", null, null],
    ["project/node_modules/softschema/dist/cli.js", null, null],
  ])("%s (cache root %p) is from runner %p", (location, cacheRoot, expected) => {
    if (cacheRoot !== null) tagCache(cacheRoot);

    expect(ephemeralRunner(join(root, location))).toBe(expected);
  });

  test("ephemeralRunner splits Windows paths", () => {
    const path =
      "C:\\Users\\me\\AppData\\Local\\npm-cache\\_npx\\be80e5187394a449\\node_modules\\.bin\\x.cmd";

    expect(ephemeralRunner(path)).toBe("npx");
  });

  test("a lookup error that is not an operating-system error propagates", () => {
    // A NUL byte is an invalid argument, not a missing path: a bug, never "not found".
    expect(() => doctorReport({ pathValue: "bad\0dir", runningPath: SOURCE_MODULE })).toThrow(
      TypeError,
    );
  });

  test("a non-executable file or a directory named softschema is not a runner", () => {
    mkdirSync(join(root, "plain"));
    writeFileSync(join(root, "plain", "softschema"), "");
    mkdirSync(join(root, "dir", "softschema"), { recursive: true });

    const result = report(SOURCE_MODULE, "plain", "dir");

    expect(result.runners).toEqual(runners({ softschema: null, uvx: null, npx: null }));
    expect(result.recommended_invocation).toBeNull();
  });

  test("doctor --json reads PATH from the environment", async () => {
    const softschema = executable(INSTALLED_BIN, "softschema");
    const uvx = executable(TOOLS_BIN, "uvx");
    const originalPath = process.env.PATH;
    const originalWrite = process.stdout.write.bind(process.stdout);
    let stdout = "";
    process.env.PATH = searchPath(INSTALLED_BIN, TOOLS_BIN);
    process.stdout.write = ((chunk: string | Uint8Array) => {
      stdout += chunk.toString();
      return true;
    }) as typeof process.stdout.write;
    try {
      expect(await main(["node", "cli.js", "doctor", "--json"])).toBe(0);
    } finally {
      process.stdout.write = originalWrite;
      process.env.PATH = originalPath;
    }

    const output = JSON.parse(stdout);
    expect(output).toEqual({
      version: output.version,
      runners: runners({ softschema, uvx, npx: null }),
      recommended_invocation: "softschema",
    });
    expect(output.version).toMatch(/^\d+\.\d+\.\d+/);
  });

  test("the text report tells the user how to recover when no runner exists", () => {
    const result = doctorReport({ pathValue: root, runningPath: SOURCE_MODULE });

    expect(doctorText(result)).toBe(
      [
        `softschema version: ${result.version}`,
        "available runners:",
        "  softschema: no",
        "  uvx: no",
        "  npx: no",
        "recommended invocation: unavailable",
        "Install uv or Node, then retry.",
      ].join("\n"),
    );
  });
});
