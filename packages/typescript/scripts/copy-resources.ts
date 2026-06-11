/**
 * Copy the bundled doc/skill resources from the repo into packages/typescript/resources/
 * so the CLI serves them from the package (like Python's wheel force-include) rather than
 * reading repo files via the working directory. Run as part of `build`.
 *
 * The set of files is the single source of truth in `src/resources-manifest.ts`, which the
 * resource-manifest test also checks against the CLI's DOC_TOPICS.
 */
import { cpSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { RESOURCE_PATHS } from "../src/resources-manifest.js";

const REPO_ROOT = resolve(import.meta.dir, "../../..");
const OUT_ROOT = resolve(import.meta.dir, "../resources");

// Clear first so a removed resource does not linger from a previous build (the dir is
// gitignored, so local rebuilds otherwise keep stale files).
rmSync(OUT_ROOT, { recursive: true, force: true });
for (const rel of RESOURCE_PATHS) {
  const src = join(REPO_ROOT, rel);
  const dest = join(OUT_ROOT, rel);
  mkdirSync(dirname(dest), { recursive: true });
  cpSync(src, dest);
}
console.log(`Copied ${RESOURCE_PATHS.length} resources to ${OUT_ROOT}`);
