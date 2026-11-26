import { expect, test } from "bun:test";
import { mkdtempSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { type CollectionScan, scanCollection } from "./collection.js";

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
