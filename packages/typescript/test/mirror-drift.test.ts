/**
 * The committed skill mirrors must stay in sync with the source skill.
 *
 * TS equivalent of packages/python/tests/test_skill_mirror_drift.py: regenerate the
 * install payload from skills/softschema/SKILL.md and fail if either committed mirror
 * differs. Matching the same source payload also proves the mirrors are byte-identical.
 */
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { expect, test } from "bun:test";
import { installSkillPayload, SKILL_INSTALL_TARGETS } from "../src/cli.js";

const REPO_ROOT = resolve(import.meta.dir, "../../..");
const SOURCE = join(REPO_ROOT, "skills/softschema/SKILL.md");

function packageVersion(): string {
  const pkg = JSON.parse(
    readFileSync(join(resolve(import.meta.dir, ".."), "package.json"), "utf8"),
  ) as { version?: string };
  return pkg.version ?? "unknown";
}

const sourceText = readFileSync(SOURCE, "utf8").replaceAll("<version>", packageVersion());
const expected = installSkillPayload(sourceText);

for (const relative of SKILL_INSTALL_TARGETS) {
  test(`${relative} matches skills/softschema/SKILL.md`, () => {
    const mirrorPath = join(REPO_ROOT, relative);
    const mirror = readFileSync(mirrorPath, "utf8");
    expect(mirror).toBe(expected);
  });
}
