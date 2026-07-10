import { expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { PortableValueError } from "../src/core/value-domain.js";
import {
  readBoundedBytes,
  readFrontmatterWithLocations,
  readPureYamlArtifactWithLocations,
} from "../src/validate.js";

test("file-backed YAML readers stop at one byte beyond the configured limit", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-bounded-read-"));
  const source = join(directory, "oversized.yaml");
  writeFileSync(source, "value", "utf8");

  expect(() => readBoundedBytes(source, 4)).toThrow(PortableValueError);
  expect(() => readFrontmatterWithLocations(source, { maxResourceBytes: 4 })).toThrow(
    "maximum resource size exceeded",
  );
  expect(() => readPureYamlArtifactWithLocations(source, { maxResourceBytes: 4 })).toThrow(
    "maximum resource size exceeded",
  );
});
