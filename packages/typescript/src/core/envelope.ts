/** Runtime-neutral artifact-envelope selection. */

export class EnvelopeAmbiguityError extends Error {
  readonly candidates: string[];

  constructor(candidates: string[]) {
    super(
      "multiple top-level frontmatter keys; designate the softschema payload " +
        `(candidates: ${candidates.join(", ")})`,
    );
    this.candidates = [...candidates];
  }
}

/** Return the only non-metadata key, or require explicit disambiguation. */
export function inferEnvelopeKey(frontmatter: Record<string, unknown>): string | null {
  const candidates = Object.keys(frontmatter).filter((key) => key !== "softschema");
  if (candidates.length === 0) return null;
  if (candidates.length === 1) return candidates[0] ?? null;
  throw new EnvelopeAmbiguityError(candidates);
}
