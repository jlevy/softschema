/**
 * Copy the bundled doc/skill resources from the repo into packages/typescript/resources/
 * so the CLI serves them from the package (like Python's wheel force-include) rather than
 * reading repo files via the working directory. Run as part of `build`.
 *
 * The resource set mirrors the CLI's DOC_TOPICS paths.
 */
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const REPO_ROOT = resolve(import.meta.dir, "../../..");
const OUT_ROOT = resolve(import.meta.dir, "../resources");

const RESOURCES = [
  "README.md",
  "AGENTS.md",
  "docs/softschema-guide.md",
  "docs/softschema-spec.md",
  "docs/softschema-python-design.md",
  "docs/development.md",
  "docs/installation.md",
  "docs/publishing.md",
  "examples/movie_page/README.md",
  "examples/movie_page/spirited-away.md",
  "examples/movie_page/model.py",
  "examples/movie_page/host_integration.py",
  "skills/softschema/SKILL.md",
];

for (const rel of RESOURCES) {
  const src = join(REPO_ROOT, rel);
  const dest = join(OUT_ROOT, rel);
  mkdirSync(dirname(dest), { recursive: true });
  cpSync(src, dest);
}
console.log(`Copied ${RESOURCES.length} resources to ${OUT_ROOT}`);
