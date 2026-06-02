import { describe, expect, test } from "bun:test";
import type { Contract } from "./models.js";
import { Contracts } from "./registry.js";

function contract(id: string, envelopeKey: string | null = null): Contract {
  return { id, model: null, envelopeKey, status: "soft", profile: "frontmatter-md", schemaPath: null };
}

describe("Contracts", () => {
  test("registers and resolves by id", () => {
    const registry = new Contracts();
    const c = contract("example:Sample/v1");
    registry.register(c);
    expect(registry.resolve("example:Sample/v1")).toEqual(c);
    expect(registry.resolve("missing")).toBeNull();
  });

  test("re-registering an identical contract is a no-op", () => {
    const registry = new Contracts();
    registry.register(contract("a:B/v1"));
    expect(() => registry.register(contract("a:B/v1"))).not.toThrow();
  });

  test("registering a different contract under the same id throws", () => {
    const registry = new Contracts();
    registry.register(contract("a:B/v1"));
    expect(() => registry.register(contract("a:B/v1", "envelope"))).toThrow("already registered");
  });
});
