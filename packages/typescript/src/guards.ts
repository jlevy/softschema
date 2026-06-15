/** True for a non-null, non-array object — a JSON/YAML mapping. */
export function isMapping(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
