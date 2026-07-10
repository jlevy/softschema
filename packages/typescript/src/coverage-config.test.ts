/** Regression checks for the package-source coverage boundary. */

import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test("coverage excludes only generated bundles and transient integration copies", () => {
  const bunfig = readFileSync(resolve(import.meta.dir, "../bunfig.toml"), "utf8");

  expect(bunfig).toContain('"dist/**"');
  expect(bunfig).toContain('"**/softschema-example-*/**"');
  expect(bunfig).toContain('"**/softschema model path */**"');
  expect(bunfig).not.toContain('"src/**"');
});
