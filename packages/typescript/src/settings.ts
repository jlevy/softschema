/**
 * Serialization helpers shared across the package, tuned for byte-for-byte parity
 * with the Python implementation's CLI output and schema hashing.
 */
import { createHash } from "node:crypto";
import { canonicalJson } from "./core/canonical-json.js";

export { canonicalJson, stableStringify } from "./core/canonical-json.js";

/** Deterministic SHA-256 over the canonical JSON form, hex-encoded. */
export function schemaSha256(value: unknown): string {
  return createHash("sha256").update(canonicalJson(value), "utf8").digest("hex");
}
