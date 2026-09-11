/**
 * A verdict must say which mechanism decided it, not only whether it passed.
 *
 * `status` states intended maturity and binds nothing. So a document declaring `enforced`
 * and validated with nothing bound comes back `valid` with an empty error list, because
 * there was nothing to disagree with. That verdict is honest about the check it ran and
 * silent about the check it did not, and the two are indistinguishable to anything
 * reading `outcome`.
 *
 * Mirrors packages/python/tests/test_enforcement_clarity.py case for case.
 */

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { z } from "zod";
import { compileSchema } from "./compile.js";
import type { Contract } from "./models.js";
import { validateArtifact } from "./validate.js";

const Sample = z.strictObject({ name: z.string() });

function tmpDir(): string {
  return mkdtempSync(join(tmpdir(), "softschema-enf-"));
}

function writeDoc(dir: string, status = "enforced"): string {
  const path = join(dir, "doc.md");
  writeFileSync(
    path,
    "---\nsoftschema:\n  contract: example:Sample/v1\n  envelope: sample\n" +
      `  status: ${status}\nsample:\n  name: hello\n---\n# body\n`,
  );
  return path;
}

function mkContract(overrides: Partial<Contract> = {}): Contract {
  return {
    id: "example:Sample/v1",
    model: null,
    envelopeKey: "sample",
    status: "enforced",
    profile: "frontmatter-md",
    schemaPath: null,
    ...overrides,
  };
}

function codes(warnings: { code: string }[]): string[] {
  return warnings.map((w) => w.code);
}

describe("enforcement_applied", () => {
  test("enforced with nothing bound is reported, not silently passed", () => {
    const result = validateArtifact(writeDoc(tmpDir()), mkContract());

    expect(result.enforcement_applied).toBe("none");
    expect(codes(result.warnings)).toContain("document-enforcement-not-applied");
  });

  test("enforced via a model only says so", () => {
    // A model closes the object in its own language and says nothing to any other. That
    // is a real check and a weaker promise than the word `enforced` names, so it is
    // reported as its own level rather than folded into either neighbour.
    const result = validateArtifact(writeDoc(tmpDir()), mkContract({ model: "inline:Sample" }), {
      semanticModel: Sample,
    });

    expect(result.enforcement_applied).toBe("model");
    expect(codes(result.warnings)).toContain("document-enforcement-via-model-only");
  });

  test("enforced with a bound schema is silent", () => {
    const dir = tmpDir();
    const schemaPath = join(dir, "sample.schema.yaml");
    compileSchema(z.strictObject({ name: z.string() }), schemaPath, {
      contractId: "example:Sample/v1",
    });

    const result = validateArtifact(writeDoc(dir), mkContract({ schemaPath }));

    expect(result.ok).toBe(true);
    expect(result.enforcement_applied).toBe("schema");
    expect(result.warnings).toEqual([]);
  });

  test("a bound schema that cannot be read applied nothing", () => {
    // Deriving the mechanism from `structural.skipped_reason` reports `schema` here,
    // because a failure to load the schema skips nothing and validates nothing. That is
    // the same false assurance in a new field, so the mechanism is recorded where the
    // check would have run.
    const dir = tmpDir();
    const result = validateArtifact(
      writeDoc(dir),
      mkContract({ schemaPath: join(dir, "absent.schema.yaml") }),
    );

    expect(result.outcome).toBe("invalid");
    expect(result.enforcement_applied).toBe("none");
    expect(codes(result.warnings)).toContain("document-enforcement-not-applied");
  });

  test("a soft document is not warned about", () => {
    // Only a shortfall against a claim is a finding. `soft` claims nothing.
    const result = validateArtifact(writeDoc(tmpDir(), "soft"), mkContract({ status: "soft" }));

    expect(result.enforcement_applied).toBe("none");
    expect(result.warnings).toEqual([]);
  });

  test("it is reported for every verdict, not only on a shortfall", () => {
    const result = validateArtifact(
      writeDoc(tmpDir(), "permissive"),
      mkContract({ status: "permissive", model: "inline:Sample" }),
      { semanticModel: Sample },
    );

    expect(result.enforcement_applied).toBe("model");
    expect(result.warnings).toEqual([]);
  });

  test("an unreadable artifact reports none", () => {
    const result = validateArtifact(join(tmpDir(), "absent.md"), mkContract());

    expect(result.enforcement_applied).toBe("none");
  });
});
