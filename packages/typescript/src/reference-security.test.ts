import { expect, test } from "bun:test";
import { Socket } from "node:net";
import type { SchemaInvalidErrorRecord } from "./errors.js";
import { validateStructural } from "./validate.js";

const JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema";

function referenceError(reference: string): SchemaInvalidErrorRecord {
  return {
    kind: "schema_invalid",
    reason: "reference",
    message: "compiled schema reference is unavailable offline",
    schema_path: "/$ref",
    reference,
  };
}

test("trusted resources resolve relative to an absolute root id", () => {
  const schema = {
    $schema: JSON_SCHEMA_2020_12,
    $id: "https://schemas.example/root",
    $ref: "child",
  };
  const resources = {
    "https://schemas.example/child": {
      $schema: JSON_SCHEMA_2020_12,
      type: "object",
      required: ["name"],
      properties: { name: { type: "string" } },
    },
  };

  const result = validateStructural({ name: "Ada" }, schema, { resources });

  expect(result.ok).toBe(true);
});

test("trusted resources resolve relative to their mapping URI", () => {
  const schema = {
    $schema: JSON_SCHEMA_2020_12,
    $ref: "https://schemas.example/bundle/root",
  };
  const resources = {
    "https://schemas.example/bundle/root": {
      $schema: JSON_SCHEMA_2020_12,
      $ref: "child",
    },
    "https://schemas.example/bundle/child": {
      $schema: JSON_SCHEMA_2020_12,
      type: "string",
    },
  };

  expect(validateStructural("Ada", schema, { resources }).ok).toBe(true);
});

test("idless roots have no implicit relative file base", () => {
  const schema = {
    $schema: JSON_SCHEMA_2020_12,
    $ref: "sibling.schema.json",
  };
  const resources = {
    "https://schemas.example/sibling.schema.json": {
      $schema: JSON_SCHEMA_2020_12,
      type: "object",
    },
  };

  expect(validateStructural({}, schema, { resources }).errors).toEqual([
    referenceError("sibling.schema.json"),
  ]);
});

test("unresolved HTTP and file references never call retrieval APIs", () => {
  const originalFetch = globalThis.fetch;
  const originalConnect = Socket.prototype.connect;
  const originalBunFile = Bun.file;
  let fetchCalls = 0;
  let socketCalls = 0;
  let fileCalls = 0;
  globalThis.fetch = (async () => {
    fetchCalls += 1;
    throw new Error("schema retrieval must remain offline");
  }) as unknown as typeof fetch;
  Socket.prototype.connect = function trapSocketConnect() {
    socketCalls += 1;
    throw new Error("schema retrieval must remain offline");
  } as typeof Socket.prototype.connect;
  Bun.file = (() => {
    fileCalls += 1;
    throw new Error("schema retrieval must remain offline");
  }) as typeof Bun.file;

  const references = [
    "http://127.0.0.1:1/schema.json",
    "file:///tmp/softschema-must-not-read.schema.json",
  ];
  try {
    for (const reference of references) {
      const result = validateStructural({}, { $schema: JSON_SCHEMA_2020_12, $ref: reference });
      expect(result.errors).toEqual([referenceError(reference)]);
    }
  } finally {
    globalThis.fetch = originalFetch;
    Socket.prototype.connect = originalConnect;
    Bun.file = originalBunFile;
  }

  expect(fetchCalls).toBe(0);
  expect(socketCalls).toBe(0);
  expect(fileCalls).toBe(0);
});

test("a supplied resource cannot enable transitive retrieval", () => {
  const missing = "https://schemas.example/not-loaded";
  const resources = {
    "https://schemas.example/root": {
      $schema: JSON_SCHEMA_2020_12,
      $ref: missing,
    },
  };

  const result = validateStructural(
    {},
    {
      $schema: JSON_SCHEMA_2020_12,
      $ref: "https://schemas.example/root",
    },
    { resources },
  );

  expect(result.errors).toEqual([referenceError(missing)]);
});
