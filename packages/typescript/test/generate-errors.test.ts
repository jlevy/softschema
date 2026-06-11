/**
 * Error paths and happy paths for generate.ts: missing/unknown kind, missing contract,
 * unreadable contract, unterminated marker, plus renderFieldList and renderVocab.
 */
import { afterEach, describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseSections, regenerate } from "../src/generate.js";

let tempDir: string;
function makeTempDir(): string {
  tempDir = mkdtempSync(join(tmpdir(), "softschema-gen-test-"));
  return tempDir;
}

afterEach(() => {
  if (tempDir) {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

// Minimal valid schema for testing renderers.
const MINI_SCHEMA = `
$schema: "https://json-schema.org/draft/2020-12/schema"
type: object
properties:
  title:
    type: string
    description: "The title field"
  status:
    type: string
    enum: ["draft", "published", "archived"]
    description: "Current status"
  count:
    type: integer
required:
  - title
  - status
`;

describe("generate.ts error paths", () => {
  test("missing kind attribute throws", () => {
    const dir = makeTempDir();
    const schemaPath = join(dir, "test.schema.yaml");
    writeFileSync(schemaPath, MINI_SCHEMA);
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Test\n<!-- softschema:generated contract="test.schema.yaml" -->\nold\n<!-- /softschema:generated -->\n`,
    );
    expect(() => regenerate(doc)).toThrow("missing 'kind'");
  });

  test("unknown kind throws with known kinds listed", () => {
    const dir = makeTempDir();
    const schemaPath = join(dir, "test.schema.yaml");
    writeFileSync(schemaPath, MINI_SCHEMA);
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Test\n<!-- softschema:generated kind="bogus_kind" contract="test.schema.yaml" -->\nold\n<!-- /softschema:generated -->\n`,
    );
    expect(() => regenerate(doc)).toThrow(/unknown softschema:generated kind.*"bogus_kind"/);
  });

  test("missing contract attribute throws", () => {
    const dir = makeTempDir();
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Test\n<!-- softschema:generated kind="field_list" -->\nold\n<!-- /softschema:generated -->\n`,
    );
    expect(() => regenerate(doc)).toThrow("missing 'contract'");
  });

  test("unreadable contract path throws", () => {
    const dir = makeTempDir();
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Test\n<!-- softschema:generated kind="field_list" contract="nonexistent.schema.yaml" -->\nold\n<!-- /softschema:generated -->\n`,
    );
    expect(() => regenerate(doc)).toThrow();
  });

  test("unterminated softschema:generated marker throws", () => {
    const text = `# Test\n<!-- softschema:generated kind="field_list" contract="x.yaml" -->\nno closing marker here\n`;
    expect(() => parseSections(text)).toThrow(/unterminated softschema:generated marker/);
  });
});

describe("generate.ts happy paths", () => {
  test("renderFieldList produces field bullets", () => {
    const dir = makeTempDir();
    const schemaPath = join(dir, "test.schema.yaml");
    writeFileSync(schemaPath, MINI_SCHEMA);
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Fields\n<!-- softschema:generated kind="field_list" contract="test.schema.yaml" -->\nplaceholder\n<!-- /softschema:generated -->\n`,
    );
    const result = regenerate(doc);
    expect(result.sections).toBe(1);
    // The doc should have been rewritten if content drifted.
    const updated = readFileSync(doc, "utf8");
    expect(updated).toContain("`title` (string, required): The title field");
    expect(updated).toContain("`status` (string, required): Current status");
    expect(updated).toContain("`count` (integer, optional)");
  });

  test("renderVocab renders enum values as bullet list", () => {
    const dir = makeTempDir();
    const schemaPath = join(dir, "test.schema.yaml");
    writeFileSync(schemaPath, MINI_SCHEMA);
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Vocab\n<!-- softschema:generated kind="vocab" contract="test.schema.yaml" pointer="/properties/status" -->\nplaceholder\n<!-- /softschema:generated -->\n`,
    );
    const result = regenerate(doc);
    expect(result.sections).toBe(1);
    const updated = readFileSync(doc, "utf8");
    expect(updated).toContain("- `draft`");
    expect(updated).toContain("- `published`");
    expect(updated).toContain("- `archived`");
  });

  test("renderVocab without pointer attribute throws", () => {
    const dir = makeTempDir();
    const schemaPath = join(dir, "test.schema.yaml");
    writeFileSync(schemaPath, MINI_SCHEMA);
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Vocab\n<!-- softschema:generated kind="vocab" contract="test.schema.yaml" -->\nplaceholder\n<!-- /softschema:generated -->\n`,
    );
    expect(() => regenerate(doc)).toThrow(/requires a 'pointer' attribute/);
  });

  test("enum_table renders a Markdown table", () => {
    const dir = makeTempDir();
    const schemaPath = join(dir, "test.schema.yaml");
    writeFileSync(schemaPath, MINI_SCHEMA);
    const doc = join(dir, "doc.md");
    writeFileSync(
      doc,
      `# Enums\n<!-- softschema:generated kind="enum_table" contract="test.schema.yaml" -->\nplaceholder\n<!-- /softschema:generated -->\n`,
    );
    const result = regenerate(doc);
    expect(result.sections).toBe(1);
    const updated = readFileSync(doc, "utf8");
    expect(updated).toContain("| `status` | draft, published, archived |");
  });

  test("no sections returns sections=0 with no drift", () => {
    const dir = makeTempDir();
    const doc = join(dir, "plain.md");
    writeFileSync(doc, "# Just a plain doc\n\nNo markers here.\n");
    const result = regenerate(doc);
    expect(result.sections).toBe(0);
    expect(result.drift).toBe(false);
  });
});
