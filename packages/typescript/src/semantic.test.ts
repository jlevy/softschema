import { describe, expect, test } from "bun:test";
import { z } from "zod";
import { validateSemantic } from "./validate.js";

// Cross-field invariant expressible only in the semantic layer (Zod refine / Pydantic
// validator) — impl-specific by design, tested per-language.
const Reaction = z
  .object({ direction: z.enum(["up", "down"]), delta: z.number() })
  .refine((v) => (v.direction === "up" ? v.delta >= 0 : v.delta <= 0), {
    message: "delta sign must match direction",
  });

describe("semantic (Zod) validation", () => {
  test("passes when the cross-field invariant holds", () => {
    const result = validateSemantic({ direction: "up", delta: 1.5 }, Reaction);
    expect(result.ok).toBe(true);
    expect(result.errors).toEqual([]);
    expect(result.skipped_reason).toBeNull();
  });

  test("fails the refinement and reports the message", () => {
    const result = validateSemantic({ direction: "up", delta: -1 }, Reaction);
    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => String(e.message).includes("delta sign"))).toBe(true);
  });
});
