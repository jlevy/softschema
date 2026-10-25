/**
 * A private build of this package, for the tests that run the built output.
 *
 * `bun run build` owns `dist/` and `resources/`, and other readers use them while
 * `bun test` runs: the golden runner, `cross-impl-diff.sh`, a developer's own build, or a
 * second test run. The build deletes both before writing them (bunup's `clean`,
 * copy-resources' `rmSync`), so a test that rebuilt them in place left every concurrent
 * reader a window with no CLI or a half-written one. Tests therefore never write those
 * paths: each test file that needs the built output builds its own copy, laid out like
 * an installed package (`package.json`, `dist/`, `resources/`), and removes it afterward.
 *
 * The copy is under `node_modules/.cache/` because bunup writes only below its root
 * directory. There, the bundle resolves the package's dependencies as an installed copy
 * does, and git, tsc, biome, and flowmark already ignore it.
 */
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { afterAll, beforeAll } from "bun:test";
import { copyResources } from "../scripts/copy-resources.js";

const PACKAGE_ROOT = resolve(import.meta.dir, "..");

/** The two steps `buildPrivateCopy` runs; a change to the build script must change both. */
const MIRRORED_BUILD_SCRIPT = "bun scripts/copy-resources.ts && bunup";

// Budgets for the tests that spawn processes, measured on a 4-core Linux host with Bun
// 1.4.4: idle, and with three `bun test` runs in parallel plus `yes` on every core. One
// spawned CLI or Node consumer took 0.15-0.2 s idle and at most 0.93 s under that load;
// the private build took 0.25-0.3 s and at most 0.96 s. The budgets sit far above both
// because they exist to stop a hang, not to measure speed. When a test times out, Bun
// (1.3.11 and 1.4.4 alike) kills the synchronous spawn's child, so a hung CLI fails its
// test instead of stalling the suite.

/**
 * Per-test budget in a file whose tests each spawn one CLI or Node process. Pass it to
 * `setDefaultTimeout`, which Bun scopes to the calling file.
 */
export const SPAWN_TEST_TIMEOUT_MS = 30_000;

/** Budget for the hook that produces the private build; a cold cache is slower. */
const BUILD_TIMEOUT_MS = 120_000;

function buildPrivateCopy(): string {
  const pkg = JSON.parse(readFileSync(join(PACKAGE_ROOT, "package.json"), "utf8")) as {
    scripts?: Record<string, string>;
  };
  if (pkg.scripts?.build !== MIRRORED_BUILD_SCRIPT) {
    throw new Error(
      `package.json "build" is ${JSON.stringify(pkg.scripts?.build)}; update ` +
        "test/built-package.ts so the private build still matches it",
    );
  }

  const cache = join(PACKAGE_ROOT, "node_modules", ".cache", "softschema-test-build");
  mkdirSync(cache, { recursive: true });
  const root = mkdtempSync(join(cache, "build-"));
  try {
    copyFileSync(join(PACKAGE_ROOT, "package.json"), join(root, "package.json"));
    copyResources(join(root, "resources"));
    // bunup reads bunup.config.ts from its root; only the output directory differs.
    const outDir = relative(PACKAGE_ROOT, join(root, "dist"));
    const r = spawnSync("bun", ["run", "bunup", "--out-dir", outDir], {
      cwd: PACKAGE_ROOT,
      encoding: "utf8",
    });
    if (r.status !== 0) throw new Error(`private build failed (exit ${r.status}): ${r.stderr}`);
    return root;
  } catch (error) {
    rmSync(root, { recursive: true, force: true });
    throw error;
  }
}

/**
 * Build a private copy of the package before this file's tests and remove it after them.
 * Call at the top level of a test file; the returned function gives the copy's root.
 */
export function usePrivateBuild(): () => string {
  let root: string | undefined;
  beforeAll(() => {
    root = buildPrivateCopy();
  }, BUILD_TIMEOUT_MS);
  afterAll(() => {
    if (root !== undefined) rmSync(root, { recursive: true, force: true });
  });
  return () => {
    if (root === undefined) throw new Error("the private build has not run");
    return root;
  };
}
