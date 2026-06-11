/**
 * Resource-manifest guards (the TypeScript analogue of the Python wheel
 * force-include coverage test):
 *
 * 1. Every path in the single-source-of-truth manifest (`src/resources-manifest.ts`,
 *    which `copy-resources.ts` bundles) exists in the repo.
 * 2. Every CLI `DOC_TOPICS` path is covered by the manifest, so no `docs <topic>` can
 *    reference a file that the package does not ship.
 */
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, test } from "bun:test";
import { DOC_TOPICS } from "../src/cli.js";
import { RESOURCE_PATHS } from "../src/resources-manifest.js";

const REPO_ROOT = resolve(import.meta.dir, "../../..");

describe("resource manifest", () => {
  for (const rel of RESOURCE_PATHS) {
    test(`manifest path ${rel} exists in the repo`, () => {
      expect(existsSync(join(REPO_ROOT, rel))).toBe(true);
    });
  }
});

describe("DOC_TOPICS are bundled", () => {
  for (const topic of DOC_TOPICS) {
    test(`topic '${topic.name}' (${topic.path}) is in the resource manifest`, () => {
      expect(RESOURCE_PATHS).toContain(topic.path);
    });
  }
});
