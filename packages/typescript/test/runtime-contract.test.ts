import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { z } from "zod";
import {
  type Contract,
  type ContractDescriptor,
  defineContract,
  defineContractDescriptor,
} from "../src/models.js";
import { bindContract } from "../src/runtime-contract.js";
import { validateArtifact } from "../src/validate.js";

function descriptor(model: string | null): ContractDescriptor {
  return {
    id: "test.runtime:Payload/v1",
    model,
    envelopeKey: "data",
    status: "soft",
    profile: "frontmatter-md",
    schemaPath: null,
  };
}

describe("portable contract descriptors", () => {
  test("defineContractDescriptor validates, freezes, and stays JSON-serializable", () => {
    const value = defineContractDescriptor(descriptor("./model.mjs:Payload"));
    expect(Object.isFrozen(value)).toBe(true);
    expect(JSON.parse(JSON.stringify(value))).toEqual(value);
  });

  test("the v0.2 Contract and defineContract aliases remain compatible", () => {
    const legacy: Contract = descriptor(null);
    expect(defineContract(legacy)).toEqual(defineContractDescriptor(legacy));
  });

  test("the JavaScript boundary strips extras and rejects invalid field shapes", () => {
    const withExtra = {
      ...descriptor(null),
      runtimeOnly: new Map([["not", "serializable"]]),
    };
    expect(defineContractDescriptor(withExtra)).toEqual(descriptor(null));
    expect(Object.hasOwn(defineContractDescriptor(withExtra), "runtimeOnly")).toBe(false);
    expect(() =>
      defineContractDescriptor({ ...descriptor(null), model: 42 } as unknown as ContractDescriptor),
    ).toThrow("contract descriptor model must be a string or null");
  });
});

describe("runtime Zod contract bindings", () => {
  const model = z.strictObject({ name: z.string() });

  test("binding fails deterministically for a missing semantic model", () => {
    expect(() => bindContract(descriptor("./model.mjs:Payload"))).toThrow(
      "contract descriptor names a model but no semantic model was provided",
    );
  });

  test("binding fails deterministically for an unexpected semantic model", () => {
    expect(() => bindContract(descriptor(null), model)).toThrow(
      "contract descriptor has no model name but a semantic model was provided",
    );
  });

  test("binding rejects values that are not Zod schemas", () => {
    expect(() => bindContract(descriptor("./model.mjs:Payload"), {} as z.ZodType)).toThrow(
      "semantic model must be a Zod schema",
    );
  });

  test("preferred binding and deprecated v0.2 overload serialize identically", () => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-runtime-contract-"));
    const path = join(directory, "artifact.md");
    writeFileSync(path, "---\ndata:\n  name: Ada\n---\n");
    const portable = descriptor("./model.mjs:Payload");
    const preferred = validateArtifact(path, bindContract(portable, model));
    const legacy = validateArtifact(path, portable, { semanticModel: model });
    expect(preferred).toEqual(legacy);
  });

  test("a runtime binding rejects a second semantic model option at the JS boundary", () => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-runtime-contract-"));
    const path = join(directory, "artifact.md");
    writeFileSync(path, "---\ndata:\n  name: Ada\n---\n");
    const binding = bindContract(descriptor("./model.mjs:Payload"), model);
    expect(() =>
      validateArtifact(path, binding, { semanticModel: model } as never),
    ).toThrow("semanticModel cannot be supplied with a RuntimeContract");
  });
});
