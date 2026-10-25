// Semantic invariant absent from the CLI fixture's structural schema.
import { z } from "zod";

export const Sample = z.strictObject({ name: z.string() }).refine(
  (value) => value.name !== "rejected",
  { message: "name is unavailable" },
);
