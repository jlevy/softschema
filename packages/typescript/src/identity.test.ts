import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "yaml";
import { z } from "zod";
import { isProgrammerBug } from "./cli.js";
import { buildCanonicalSchema } from "./compile.js";
import { identityProblem } from "./identity.js";
import { validateStructural } from "./validate.js";

interface IdentityVector {
  id: string;
  problem?: string;
  nested?: boolean;
}
const vectors = parse(
  readFileSync(join(import.meta.dir, "../../../tests/vectors/identities.yaml"), "utf8"),
) as {
  refuse: IdentityVector[];
  accept: IdentityVector[];
  order: {
    schema: Record<string, unknown>;
    resources?: Record<string, Record<string, unknown>>;
    message: string;
  }[];
};
const ROOT = "https://example.com/root.json";
const Named = z.object({ name: z.string() });

function schemaWith(identity: string, nested: boolean): Record<string, unknown> {
  return nested
    ? { $id: ROOT, type: "object", $defs: { X: { $id: identity, type: "string" } } }
    : { $id: identity, type: "object" };
}

describe("resource identity grammar", () => {
  test("refusals name the same rule as Python, in compile and validation alike", () => {
    // Compile refuses a root identity as the schema id, and validation refuses it as the
    // `$id`, with one message.
    for (const { id, problem, nested = false } of vectors.refuse) {
      expect(identityProblem(id, !nested)).toBe(problem ?? null);
      const label = nested ? "a $id" : "the root $id";
      const message = `${label} must ${problem}, got ${JSON.stringify(id)}`;
      const structural = validateStructural({ name: "n" }, schemaWith(id, nested));
      expect(structural.execution).toBe("not_run");
      expect(structural.errors[0]).toMatchObject({ reason: "resource_identity", message });
      if (!nested) {
        let thrown: unknown;
        try {
          buildCanonicalSchema(Named, "example:Named/v1", id);
        } catch (error) {
          thrown = error;
        }
        // A plain Error, not a programmer-bug class, so the CLI reports it with exit 2.
        expect(thrown).toBeInstanceOf(Error);
        expect(isProgrammerBug(thrown)).toBe(false);
        expect((thrown as Error).message).toBe(message);
      }
    }
  });

  test("acceptances pass the grammar, compile as the schema id, and validate", () => {
    for (const { id, nested = false } of vectors.accept) {
      expect(identityProblem(id, !nested)).toBeNull();
      expect(validateStructural({ name: "n" }, schemaWith(id, nested)).execution).toBe("completed");
      if (!nested) {
        const { schema } = buildCanonicalSchema(Named, "example:Named/v1", id);
        expect(schema.$id).toBe(id);
        expect(validateStructural({ name: "n" }, schema).ok).toBe(true);
      }
    }
  });

  test("with several invalid identities, both runtimes quote the same one", () => {
    for (const { schema, resources, message } of vectors.order) {
      const result = validateStructural("x", structuredClone(schema), { resources });
      expect(result.errors[0]).toMatchObject({ reason: "resource_identity", message });
    }
  });
});
