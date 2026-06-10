/**
 * Every path in copy-resources.ts RESOURCES must exist in the repo.
 *
 * This guards against drift between the resource manifest and the actual
 * repo tree, without importing cli.ts (owned by a sibling agent).
 */
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, test } from "bun:test";

const REPO_ROOT = resolve(import.meta.dir, "../../..");

/**
 * Resource paths copied from copy-resources.ts RESOURCES array.
 * Keep in sync with that file.
 */
const RESOURCES = [
  "README.md",
  "AGENTS.md",
  "docs/softschema-guide.md",
  "docs/softschema-spec.md",
  "docs/softschema-python-design.md",
  "docs/softschema-typescript-design.md",
  "docs/development.md",
  "docs/installation.md",
  "docs/publishing.md",
  "examples/movie_page/README.md",
  "examples/movie_page/spirited-away.md",
  "examples/movie_page/model.py",
  "examples/movie_page/host_integration.py",
  "examples/movie_page/movie-page.schema.yaml",
  "skills/softschema/SKILL.md",
];

describe("copy-resources RESOURCES paths exist in repo", () => {
  for (const rel of RESOURCES) {
    test(`${rel} exists`, () => {
      const full = join(REPO_ROOT, rel);
      expect(existsSync(full)).toBe(true);
    });
  }
});
