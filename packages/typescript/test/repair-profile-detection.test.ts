/**
 * Profile detection on the `--repair` path must reach the same read verdict as plain
 * `validate`.
 *
 * It once did not: a document that opened a frontmatter fence and never closed it was
 * detected as pure-yaml, its leading `---` was consumed as a YAML document-start marker,
 * and `--check-repair` reported `valid` for a file plain `validate` could not open at
 * all. Both runtimes diverged in the same direction, so cross-implementation parity
 * stayed clean while both were wrong — which is why this is pinned per-implementation.
 *
 * See docs/project/reviews/review-2026-08-30-validate-repair-e2e.md, Finding 1.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { main } from "../src/cli.js";

const argv = (...args: string[]) => ["node", "cli.js", ...args];

const MINI_SCHEMA = `$schema: https://json-schema.org/draft/2020-12/schema
type: object
additionalProperties: false
required: [name]
properties:
  name: {type: string}
`;

const FRONTMATTER_BODY = `softschema:
  contract: test.detect:Doc/v1
  schema: mini.schema.yaml
  envelope: rec
  status: enforced
rec:
  name: Acme`;

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
  dir = mkdtempSync(join(tmpdir(), "softschema-detect-"));
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

describe("repair-path profile detection", () => {
  test("an unterminated fence is unreadable on both paths, for the same stated reason", async () => {
    const path = write("unterminated.md", `---\n${FRONTMATTER_BODY}\n`);

    expect(await main(argv("validate", path))).toBe(2);
    expect(stderr).toContain("Delimiter `---` for end of frontmatter not found");

    stderr = "";
    expect(await main(argv("validate", path, "--check-repair"))).toBe(2);
    expect(stderr).toContain("Delimiter `---` for end of frontmatter not found");
    expect(stderr).not.toContain("has no YAML frontmatter");
  });

  test("a terminated fence still validates on both paths", async () => {
    const path = write("terminated.md", `---\n${FRONTMATTER_BODY}\n---\n# Body\n`);
    for (const args of [["validate", path], ["validate", path, "--check-repair"]]) {
      stdout = "";
      expect(await main(argv(...args))).toBe(0);
      expect(JSON.parse(stdout).outcome).toBe("valid");
    }
  });

  test("a fenceless document is still read as pure-yaml", async () => {
    // The fix narrows what counts as "fenceless"; a document that never opened a fence
    // is still pure-yaml, which is the rule the narrowing must not break.
    const path = write("fenceless.md", `${FRONTMATTER_BODY}\n`);
    expect(await main(argv("validate", path, "--check-repair"))).toBe(0);
    expect(JSON.parse(stdout).profile).toBe("pure-yaml");
  });

  test("a .yaml file opening with a document-start marker stays pure-yaml", async () => {
    // A `*.yaml` file may legitimately open with `---`. The suffix rule answers first,
    // so the fence check never sees it.
    const path = write("record.yaml", `---\n${FRONTMATTER_BODY}\n`);
    expect(await main(argv("validate", path, "--check-repair"))).toBe(0);
    expect(JSON.parse(stdout).profile).toBe("pure-yaml");
  });

  test("unparsable frontmatter names the parse failure, not a missing block", async () => {
    const path = write(
      "broken.md",
      "---\nsoftschema:\n  contract: test.detect:Doc/v1\nrec: [unclosed\n---\n# Body\n",
    );
    expect(await main(argv("validate", path, "--check-repair"))).toBe(2);
    expect(stderr).toContain("could not be read");
    expect(stderr).not.toContain("has no YAML frontmatter");
  });
});
