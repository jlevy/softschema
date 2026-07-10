/** Runtime-neutral deterministic JSON serialization helpers. */

function sortKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeysDeep);
  if (value !== null && typeof value === "object") {
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      sorted[key] = sortKeysDeep((value as Record<string, unknown>)[key]);
    }
    return sorted;
  }
  return value;
}

/** Pretty JSON with recursively sorted keys. */
export function stableStringify(value: unknown, indent = 2): string {
  return JSON.stringify(sortKeysDeep(value), null, indent);
}

/** Compact JSON with recursively sorted keys. */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortKeysDeep(value));
}
