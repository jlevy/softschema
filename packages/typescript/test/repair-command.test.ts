/**
 * The `repair` command, and the postures `repair` and `validate` take toward an
 * unreadable artifact.
 *
 * `repair` is its own command because it answers a different question from `validate` and
 * has the opposite posture toward a document that cannot be read. `validate` is the
 * consuming-side gate and refuses one; `repair` is the producing-side loop and reports one.
 * See docs/project/specs/active/plan-2026-08-30-repair-command.md.
 *
 * Kept in step with the Python cases in packages/python/tests/test_cli.py.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { main } from "../src/cli.js";
import { ArtifactInvalidError, loadArtifact } from "../src/validate.js";

const argv = (...args: string[]) => ["node", "cli.js", ...args];

const MINI_SCHEMA = `$schema: https://json-schema.org/draft/2020-12/schema
type: object
additionalProperties: false
required: [name]
properties:
  name: {type: string}
`;

const NEEDS_REPAIR = `---
softschema:
  contract: test.detect:Doc/v1
  schema: mini.schema.yaml
  envelope: rec
rec:
  name: Note: actually Q1
---
# Body
`;

const UNREADABLE = `---
softschema:
  contract: test.detect:Doc/v1
  envelope: rec
rec:
  name: A
`;

let stdout = "";
let stderr = "";
let originalStdout: typeof process.stdout.write;
let originalStderr: typeof process.stderr.write;
let dir = "";

beforeEach(() => {
  stdout = "";
  stderr = "";
  originalStdout = process.stdout.write.bind(process.stdout);
  originalStderr = process.stderr.write.bind(process.stderr);
  process.stdout.write = ((chunk: string | Uint8Array) => {
    stdout += chunk.toString();
    return true;
  }) as typeof process.stdout.write;
  process.stderr.write = ((chunk: string | Uint8Array) => {
    stderr += chunk.toString();
    return true;
  }) as typeof process.stderr.write;
  dir = mkdtempSync(join(tmpdir(), "softschema-repair-"));
  writeFileSync(join(dir, "mini.schema.yaml"), MINI_SCHEMA);
});

afterEach(() => {
  process.stdout.write = originalStdout;
  process.stderr.write = originalStderr;
  rmSync(dir, { recursive: true, force: true });
});

function write(name: string, text: string): string {
  const path = join(dir, name);
  writeFileSync(path, text);
  return path;
}

describe("the repair command", () => {
  test("repair writes but --dry-run and --check do not", async () => {
    for (const [name, extra, expectedExit] of [
      ["written.md", [], 0],
      ["dry.md", ["--dry-run"], 0],
      ["checked.md", ["--check"], 1],
    ] as const) {
      const path = write(name, NEEDS_REPAIR);
      const before = readFileSync(path, "utf8");
      stdout = "";
      expect(await main(argv("repair", path, ...extra))).toBe(expectedExit);
      const result = JSON.parse(stdout);
      // Every mode reaches the same verdict and reports the same change; they differ
      // only in whether the file moves and what the exit code asserts.
      expect(result.outcome).toBe("valid");
      expect(result.repairs.map((r: { code: string }) => r.code)).toEqual(["yaml_quoted_scalar"]);
      expect(readFileSync(path, "utf8") !== before).toBe(extra.length === 0);
    }
  });

  test("--check and --dry-run differ only on an already-clean document", async () => {
    // The whole reason both flags exist: --check asserts "nothing needed doing" and fails
    // a document that repairs cleanly, while --dry-run keeps the ordinary pass condition.
    const clean = NEEDS_REPAIR.replace("name: Note: actually Q1", 'name: "Note: actually Q1"');
    for (const [name, text, dryExit, checkExit] of [
      ["dirty.md", NEEDS_REPAIR, 0, 1],
      ["clean.md", clean, 0, 0],
    ] as const) {
      const path = write(name, text);
      expect(await main(argv("repair", path, "--dry-run"))).toBe(dryExit);
      expect(await main(argv("repair", path, "--check"))).toBe(checkExit);
    }
  });

  test("--dry-run and --check are mutually exclusive", async () => {
    const path = write("doc.md", NEEDS_REPAIR);
    expect(await main(argv("repair", path, "--dry-run", "--check"))).toBe(2);
  });

  test("validate no longer accepts the retired repair flags", async () => {
    const path = write("doc.md", NEEDS_REPAIR);
    // retired-surface-ok — this test exists to assert these no longer parse
    for (const flag of ["--repair", "--check-repair"]) {
      expect(await main(argv("validate", path, flag))).toBe(2);
    }
  });

  test("validate never writes", async () => {
    const path = write("doc.md", NEEDS_REPAIR);
    const before = readFileSync(path, "utf8");
    await main(argv("validate", path));
    expect(readFileSync(path, "utf8")).toBe(before);
  });
});

describe("strictness is a property of the command", () => {
  test("validate refuses an unreadable artifact with or without a contract", async () => {
    // `validate` has always read unconditionally, so this pins existing behavior rather
    // than fixing it — and it was not pinned before. The verdict must not come to depend
    // on a flag that has nothing to do with whether the file can be opened.
    const path = write("unreadable.md", UNREADABLE);
    for (const extra of [[], ["--contract", "test.detect:Doc/v1"]] as const) {
      stdout = "";
      stderr = "";
      expect(await main(argv("validate", path, ...extra))).toBe(2);
      expect(stdout).toBe(""); // exit 2 is a message, never a result document
      expect(stderr).toContain("Delimiter `---` for end of frontmatter not found");
    }
  });

  test("repair reports an unreadable artifact with or without a contract", async () => {
    // The defect this closes: `repair` is the checking posture by definition, but threw a
    // usage error about --contract when it could not infer a binding — advising a flag
    // that would not have helped, to the one caller who most needs the diagnostic.
    const path = write("unreadable.md", UNREADABLE);
    for (const extra of [[], ["--contract", "test.detect:Doc/v1"]] as const) {
      stdout = "";
      stderr = "";
      expect(await main(argv("repair", path, "--check", ...extra))).toBe(1);
      expect(stderr).toBe("");
      const record = JSON.parse(stdout).structural.errors[0];
      expect(record.kind).toBe("yaml_parse_error");
      expect(record.message).toContain("Delimiter `---` for end of frontmatter not found");
      expect(record.message).not.toContain("--contract");
    }
  });

  test("repair leaves an unreadable artifact untouched", async () => {
    const path = write("unreadable.md", UNREADABLE);
    const before = readFileSync(path, "utf8");
    expect(await main(argv("repair", path))).toBe(1);
    expect(readFileSync(path, "utf8")).toBe(before);
  });
});

describe("loadArtifact, the strict consuming API", () => {
  const contract = () => ({
    id: "test.detect:Doc/v1",
    model: null,
    envelopeKey: "rec",
    status: "soft" as const,
    profile: "frontmatter-md" as const,
    schemaPath: join(dir, "mini.schema.yaml"),
  });

  test("returns values on valid and throws on anything less", () => {
    const valid = write(
      "valid.md",
      "---\nsoftschema:\n  contract: test.detect:Doc/v1\n  envelope: rec\nrec:\n  name: Acme\n---\n# Body\n",
    );
    expect(loadArtifact(valid, contract())).toEqual({ name: "Acme" });

    // The trap this closes: validateArtifact returns values: null here, so a consumer
    // that forgets to check `outcome` gets null where it expected a mapping.
    const unreadable = write("unreadable.md", UNREADABLE);
    expect(() => loadArtifact(unreadable, contract())).toThrow(ArtifactInvalidError);
    try {
      loadArtifact(unreadable, contract());
    } catch (err) {
      expect(err).toBeInstanceOf(ArtifactInvalidError);
      expect((err as ArtifactInvalidError).result.outcome).not.toBe("valid");
      expect((err as ArtifactInvalidError).message).toContain("unreadable.md");
    }
  });
});
