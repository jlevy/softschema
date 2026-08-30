/**
 * Profile detection on the `--repair` path must reach the same read verdict as plain
 * `validate`.
 *
 * It once did not: a document that opened a frontmatter fence and never closed it was
 * detected as pure-yaml, its leading `---` was consumed as a YAML document-start marker,
 * and the repair path reported `valid` for a file plain `validate` could not open at
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
import { opensFrontmatterFence, splitFrontmatter } from "../src/portable.js";

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

    // `repair` must refuse it too, and name the same cause. It reports rather than
    // throws: an unreadable document is that command's normal input, so the diagnostic
    // goes in a record where the agent that wrote the file can act on it.
    stdout = "";
    expect(await main(argv("repair", path, "--check"))).toBe(1);
    const record = JSON.parse(stdout).structural.errors[0];
    expect(record.kind).toBe("yaml_parse_error");
    expect(record.message).toContain("Delimiter `---` for end of frontmatter not found");
    expect(record.message).not.toContain("has no YAML frontmatter");
  });

  test("a terminated fence still validates on both paths", async () => {
    const path = write("terminated.md", `---\n${FRONTMATTER_BODY}\n---\n# Body\n`);
    for (const args of [["validate", path], ["repair", path, "--check"]]) {
      stdout = "";
      expect(await main(argv(...args))).toBe(0);
      expect(JSON.parse(stdout).outcome).toBe("valid");
    }
  });

  test("a fenceless document is still read as pure-yaml", async () => {
    // The fix narrows what counts as "fenceless"; a document that never opened a fence
    // is still pure-yaml, which is the rule the narrowing must not break.
    const path = write("fenceless.md", `${FRONTMATTER_BODY}\n`);
    expect(await main(argv("repair", path, "--check"))).toBe(0);
    expect(JSON.parse(stdout).profile).toBe("pure-yaml");
  });

  test("a .yaml file opening with a document-start marker stays pure-yaml", async () => {
    // A `*.yaml` file may legitimately open with `---`. The suffix rule answers first,
    // so the fence check never sees it.
    const path = write("record.yaml", `---\n${FRONTMATTER_BODY}\n`);
    expect(await main(argv("repair", path, "--check"))).toBe(0);
    expect(JSON.parse(stdout).profile).toBe("pure-yaml");
  });

  // A final line with no trailing newline is a line to both readers (`split(/\r?\n/)` /
  // Python's `splitlines()`), so the offset scan in portable.ts has to agree. It once did
  // not: `lineEnd` returned null at EOF, which made `splitFrontmatter` report "no region
  // to rewrite" for a document ending exactly at its closing fence — `--repair` silently
  // skipped an artifact it could fix — and made `opensFrontmatterFence` call a lone `---`
  // fenceless.

  test("opensFrontmatterFence agrees with the reader at EOF", () => {
    expect(opensFrontmatterFence("---")).toBe(true);
    expect(opensFrontmatterFence("---\n")).toBe(true);
    expect(opensFrontmatterFence("")).toBe(false);
    expect(opensFrontmatterFence("name: Acme")).toBe(false);
  });

  test("splitFrontmatter finds a region ending at the closing fence", () => {
    const endedAtFence = splitFrontmatter("---\nname: Acme\n---");
    expect(endedAtFence).not.toBeNull();
    expect(endedAtFence?.metadataText).toBe("name: Acme\n");
    // An empty body, and the file's missing trailing newline preserved by the offsets.
    expect(endedAtFence?.bodyOffset).toBe("---\nname: Acme\n---".length);

    // Unchanged: a fence that never closes still has no region to rewrite.
    expect(splitFrontmatter("---\nname: Acme")).toBeNull();
  });

  test("repair fixes a document that ends at its closing fence", async () => {
    // Two documents differing only in a trailing newline must get the same verdict.
    // Before the fix the newline-less one was reported unreadable and left unrepaired.
    const body = [
      "---",
      "softschema:",
      "  contract: test.detect:Doc/v1",
      "  schema: mini.schema.yaml",
      "  envelope: rec",
      "rec:",
      "  name: Note: actually Q1",
      "---",
    ].join("\n");
    for (const [name, text] of [
      ["with-nl.md", `${body}\n`],
      ["no-nl.md", body],
    ] as const) {
      stdout = "";
      const path = write(name, text);
      expect(await main(argv("repair", path, "--check"))).toBe(1);
      const result = JSON.parse(stdout);
      expect(result.outcome).toBe("valid");
      expect(result.repairs.map((r: { code: string }) => r.code)).toEqual(["yaml_quoted_scalar"]);
    }
  });

  test("unparsable frontmatter names the parse failure, not a missing block", async () => {
    const path = write(
      "broken.md",
      "---\nsoftschema:\n  contract: test.detect:Doc/v1\nrec: [unclosed\n---\n# Body\n",
    );
    stdout = "";
    expect(await main(argv("repair", path, "--check"))).toBe(1);
    const record = JSON.parse(stdout).structural.errors[0];
    expect(record.message).not.toContain("has no YAML frontmatter");
    // The reader's own diagnosis, not a restatement that something went wrong.
    expect(record.message.length).toBeGreaterThan(20);
  });
});
