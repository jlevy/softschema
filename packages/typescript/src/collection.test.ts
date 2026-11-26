import { expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  collectionFromSnapshotJson,
  collectionSnapshotJson,
  scanCollection,
} from "./collection.js";

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
    const values = initial.records[0]?.values;
    if (!values) throw new Error("expected a payload");
    values.name = 123;
    const document = initial.schemas[0]?.document;
    if (!document) throw new Error("expected a schema");
    document.type = "string";
    expect(scanCollection(root, { previous: initial }).records[0]?.values).toEqual({ name: "one" });
    const previous = collectionFromSnapshotJson(collectionSnapshotJson(initial));
    const unchanged = scanCollection(root, { previous });
    expect(unchanged.records[0]?.values).toEqual({ name: "one" });
    expect(unchanged.records[0]?.execution).toBe("completed");
    expect(unchanged.schemas[0]?.document.type).toBe("object");

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
    expect(partial.problems).toContainEqual({ path: "z.schema.json", code: "total_byte_limit" });
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
    expect(partial.problems).toEqual([{ path: ".", code: "entry_limit" }]);
    unlinkSync(join(root, "b.yaml"));
    const previous = collectionFromSnapshotJson(collectionSnapshotJson(partial));
    const final = scanCollection(root, { maxEntries: 2, previous });
    expect(final.complete).toBe(true);
    expect(final.removed).toEqual(["b.yaml"]);
    expect(final.added).toEqual(["c.yaml"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("equivalent schema documents share one fallback", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    const schema = {
      type: "object",
      "x-softschema": { contract },
      properties: { name: { type: "string" } },
    };
    writeFileSync(join(root, "a.schema.json"), JSON.stringify(schema));
    writeFileSync(join(root, "b.schema.json"), JSON.stringify(schema, null, 2));
    writeFileSync(join(root, "item.md"), record);
    writeFileSync(join(root, "ordinary.md"), "# Prose\n\nLearn about softschema here.");
    const scan = scanCollection(root);
    expect(scan.records).toHaveLength(1);
    expect(scan.records[0]).toMatchObject({
      profile: "pure-yaml",
      state: "valid",
      schema: "a.schema.json",
    });
    expect(scan.schemas[0]?.digest).toBe(scan.schemas[1]?.digest);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("a partial walk defers adding new members until listing completes", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    writeFileSync(join(root, "a.yaml"), record);
    writeFileSync(join(root, "b.yaml"), record);
    let previous = scanCollection(root, { maxEntries: 2 });
    unlinkSync(join(root, "a.yaml"));
    unlinkSync(join(root, "b.yaml"));
    const child = join(root, "z");
    const ignored = join(child, "ignored-extension.txt");
    mkdirSync(child);
    writeFileSync(ignored, "");
    for (const name of ["c.yaml", "d.yaml"]) {
      const path = join(root, name);
      writeFileSync(path, record);
      previous = scanCollection(root, { maxEntries: 2, previous });
      expect(previous.records.map((row) => row.path)).toEqual([name]);
      expect(previous.added).toEqual([]);
      expect(previous.removed).toEqual([]);
      if (name === "c.yaml") unlinkSync(path);
    }
    unlinkSync(ignored);
    const final = scanCollection(root, { maxEntries: 2, previous });
    expect(final.added).toEqual(["d.yaml"]);
    expect(final.removed).toEqual(["a.yaml", "b.yaml"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("collection reports whether structural validation ran", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    writeFileSync(join(root, "item.yaml"), record);
    for (const [shape, execution] of [
      [{ type: "bogus" }, "not_run"],
      [{ $ref: "#" }, "errored"],
    ] as const) {
      const schema = { "x-softschema": { contract }, ...shape };
      writeFileSync(join(root, "item.schema.json"), JSON.stringify(schema));
      expect(scanCollection(root).records[0]).toMatchObject({
        schema: "item.schema.json",
        state: "unbound",
        execution,
        errors: [expect.objectContaining({ kind: "schema_invalid" })],
      });
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("collection conforms the root payload without metadata", () => {
  const root = mkdtempSync(join(tmpdir(), "softschema-collection-"));
  try {
    const schema = {
      "x-softschema": { contract },
      type: "object",
      if: { maxProperties: 1 },
      // biome-ignore lint/suspicious/noThenProperty: JSON Schema's conditional keyword.
      then: { properties: { name: { type: "string" } } },
      else: { properties: { name: { type: "integer" } } },
    };
    writeFileSync(join(root, "item.schema.json"), JSON.stringify(schema));
    const input = join(root, "item.yaml");
    const source = `softschema: ${contract}\nname: 10\n`;
    writeFileSync(input, source);
    expect(scanCollection(root).records[0]).toMatchObject({
      state: "repaired",
      values: { name: "10" },
    });
    expect(readFileSync(input, "utf8")).toBe(source);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
