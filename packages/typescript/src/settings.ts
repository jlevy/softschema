/**
 * Serialization helpers shared across the package, tuned for byte-for-byte parity
 * with the Python implementation's CLI output and schema hashing.
 */
import { createHash } from "node:crypto";

/** Recursively sort object keys so output is deterministic and matches Python's sort_keys. */
function sortKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortKeysDeep);
  }
  if (value !== null && typeof value === "object") {
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      sorted[key] = sortKeysDeep((value as Record<string, unknown>)[key]);
    }
    return sorted;
  }
  return value;
}

/**
 * Pretty JSON with 2-space indent and recursively sorted keys, matching Python's
 * `json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)`.
 */
export function stableStringify(value: unknown, indent = 2): string {
  return JSON.stringify(sortKeysDeep(value), null, indent);
}

/**
 * Compact, sorted-key JSON used as the canonical hash input, matching Python's
 * `json.dumps(value, sort_keys=True, separators=(",", ":"))`.
 */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortKeysDeep(value));
}

/** Deterministic SHA-256 over the canonical JSON form, hex-encoded. */
export function schemaSha256(value: unknown): string {
  return createHash("sha256").update(canonicalJson(value), "utf8").digest("hex");
}
