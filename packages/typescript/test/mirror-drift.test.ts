/**
 * The committed skill mirrors must stay in sync with the source skill.
 *
 * TS equivalent of packages/python/tests/test_skill_mirror_drift.py: regenerate the
 * install payload from skills/softschema/SKILL.md and fail if either committed mirror
 * differs. Also asserts the two mirrors are byte-identical.
 */
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, test } from "bun:test";
import { installSkillPayload, SKILL_INSTALL_TARGETS } from "../src/cli.js";

const REPO_ROOT = resolve(import.meta.dir, "../../..");
const SOURCE = join(REPO_ROOT, "skills/softschema/SKILL.md");

function packageVersion(): string {
  const pkg = JSON.parse(
    readFileSync(join(resolve(import.meta.dir, ".."), "package.json"), "utf8"),
  ) as { version?: string };
  return pkg.version ?? "unknown";
}

describe("committed skill mirrors match source", () => {
  const sourceText = readFileSync(SOURCE, "utf8").replaceAll("<version>", packageVersion());
  const expected = installSkillPayload(sourceText);

  for (const relative of Object.values(SKILL_INSTALL_TARGETS)) {
    test(`${relative} matches skills/softschema/SKILL.md`, () => {
      const mirrorPath = join(REPO_ROOT, relative);
      const mirror = readFileSync(mirrorPath, "utf8");
      expect(mirror).toBe(expected);
    });
  }

  test("the .agents and .claude skill mirrors are byte-identical", () => {
    const contents = new Set(
      Object.values(SKILL_INSTALL_TARGETS).map((rel) => readFileSync(join(REPO_ROOT, rel), "utf8")),
    );
    expect(contents.size).toBe(1);
  });
});
