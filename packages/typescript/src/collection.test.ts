import { expect, test } from "bun:test";
import { mkdtempSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { type CollectionScan, scanCollection } from "./collection.js";

const contract = "example:Item/v1";
const record = `softschema: ${contract}\nname: one\n`;

test("snapshot refresh invalidates verdicts when only the schema changes", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    const contract = "example:Item/v1";
    const schema = (type: string) =>
      JSON.stringify({
        "x-softschema": { contract },
        type: "object",
        properties: { name: { type } },
        required: ["name"],
      });
    const valid = `softschema: ${contract}\nname: one\n`;
    writeFileSync(join(root, "item.schema.json"), schema("string"));
    writeFileSync(join(root, "item.yaml"), valid);
    const initial = scanCollection(root);
    expect(initial.records[0]?.state).toBe("valid");
    const previous = JSON.parse(JSON.stringify(initial)) as CollectionScan;
    const unchanged = scanCollection(root, { previous });
    expect(unchanged.records[0]).toBe(previous.records[0]);

    writeFileSync(join(root, "item.schema.json"), schema("integer"));
    writeFileSync(join(root, "new.yaml"), valid);
    const updated = scanCollection(root, { previous: unchanged });
    expect(updated.added).toEqual(["new.yaml"]);
    expect(updated.changed).toEqual(["item.schema.json"]);
    expect(updated.records.map((record) => record.state)).toEqual(["invalid", "invalid"]);
    expect(updated.records).toEqual(scanCollection(root).records);
    unlinkSync(join(root, "item.yaml"));
    expect(scanCollection(root, { previous: updated }).removed).toEqual(["item.yaml"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("an incomplete scan leaves fallback pending and preserves explicit binding", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    const schema = (type: string) =>
      JSON.stringify({
        type: "object",
        "x-softschema": { contract },
        properties: { name: { type } },
      });
    const text = schema("string");
    const direct = `softschema:\n  contract: ${contract}\n  schema: a.schema.json\nname: one\n`;
    writeFileSync(join(root, "a.schema.json"), text);
    writeFileSync(join(root, "b.yaml"), record);
    writeFileSync(join(root, "direct.yaml"), direct);
    writeFileSync(join(root, "z.schema.json"), schema("integer"));
    const partial = scanCollection(root, {
      maxTotalBytes: text.length + record.length + direct.length,
    });
    expect(partial.complete).toBe(false);
    expect(partial.records[0]?.errors).toEqual([{ kind: "schema_discovery_incomplete" }]);
    expect(partial.records[1]?.state).toBe("valid");
    expect(scanCollection(root).records[0]?.errors).toEqual([{ kind: "schema_ambiguous" }]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("a byte-limited scan reports a known deletion and keeps Markdown body bytes", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    writeFileSync(join(root, "a.yaml"), record);
    writeFileSync(join(root, "b.yaml"), record);
    writeFileSync(join(root, "z.yaml"), `name: ${"x".repeat(100)}`);
    const maxTotalBytes = 2 * record.length;
    const initial = scanCollection(root, { maxTotalBytes });
    expect(initial.complete).toBe(false);
    unlinkSync(join(root, "b.yaml"));
    const partial = scanCollection(root, { maxTotalBytes, previous: initial });
    expect(partial.complete).toBe(false);
    expect(partial.removed).toEqual(["b.yaml"]);
    unlinkSync(join(root, "z.yaml"));
    expect(scanCollection(root, { maxTotalBytes, previous: partial }).removed).toEqual([]);
    const body = "First line\r\nSecond line\r\n";
    writeFileSync(
      join(root, "item.md"),
      `---\r\nsoftschema:\r\n  contract: ${contract}\r\n  envelope: item\r\ntitle: Document title\r\nitem:\r\n  name: one\r\n---\r\n${body}`,
    );
    const artifact = scanCollection(root).records[1];
    expect(artifact?.body).toBe(body);
    expect(artifact?.host).toEqual({ title: "Document title" });
    expect(artifact?.envelope).toBe("item");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("an incomplete walk keeps known names for a later complete scan", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    writeFileSync(join(root, "a.yaml"), record);
    writeFileSync(join(root, "b.yaml"), record);
    const initial = scanCollection(root, { maxEntries: 2 });
    writeFileSync(join(root, "c.yaml"), record);
    const partial = scanCollection(root, { maxEntries: 2, previous: initial });
    expect(partial.complete).toBe(false);
    expect(partial.removed).toEqual([]);
    unlinkSync(join(root, "b.yaml"));
    const previous = JSON.parse(JSON.stringify(partial)) as CollectionScan;
    const final = scanCollection(root, { maxEntries: 2, previous });
    expect(final.complete).toBe(true);
    expect(final.removed).toEqual(["b.yaml"]);
    expect(final.added).toEqual(["c.yaml"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
