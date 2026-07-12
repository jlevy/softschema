/**
 * Deterministic presentation JSON and canonical schema-hash encoding.
 */
import { createHash } from "node:crypto";

/** Recursively sort object keys for stable presentation within this runtime. */
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
 * Pretty JSON with recursively sorted keys for stable diffs within this runtime.
 */
export function stableStringify(value: unknown, indent = 2): string {
  return JSON.stringify(sortKeysDeep(value), null, indent);
}

/**
 * Compact, sorted-key JSON used as the canonical hash input, matching Python's
 * `json.dumps(value, sort_keys=True, separators=(",", ":"))`.
 */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError("canonical JSON requires finite numbers");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(",")}]`;
  }
  if (typeof value === "object") {
    return `{${Object.keys(value as Record<string, unknown>)
      .sort()
      .map(
        (key) => `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key])}`,
      )
      .join(",")}}`;
  }
  throw new TypeError(`canonical JSON does not support ${typeof value}`);
}

/** Deterministic SHA-256 over the canonical JSON form, hex-encoded. */
export function schemaSha256(value: unknown): string {
  return createHash("sha256").update(canonicalJson(value), "utf8").digest("hex");
}
