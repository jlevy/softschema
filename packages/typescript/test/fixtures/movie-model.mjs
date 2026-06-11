// Minimal Zod model for the golden `validate --model` parity scenario. A loose object
// accepts the movie payload so semantic validation passes; the point is to exercise the
// CLI's --model loading path under both Node and Bun, not to mirror the Pydantic model
// (semantic logic is language-specific by design). Lives beside the TypeScript package's
// node_modules so plain Node resolves `zod` without a TypeScript loader.
import { z } from "zod";

export const MoviePage = z.looseObject({ title: z.string() });
