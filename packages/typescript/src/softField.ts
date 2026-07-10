/**
 * Per-field `x-softschema` annotations for Zod source schemas: the idiomatic mirror of
 * Python's `SoftField`. Wraps a Zod type with `.meta()` carrying `description` and an
 * `x-softschema` block; the compiler propagates it verbatim into the compiled JSON Schema
 * as a per-property `x-softschema:` block. The emitted block and omit-empty rules match
 * the Python implementation exactly.
 */
import type { z } from "zod";

export type SoftOwner = "agent" | "postprocess" | "system" | "human";
export type SoftTier = "hard_fact" | "constrained" | "narrative";
export type RepairKind = "none" | "safe_coerce" | "suggest_alias";

const SOFT_OWNERS: readonly SoftOwner[] = ["agent", "postprocess", "system", "human"];
const SOFT_TIERS: readonly SoftTier[] = ["hard_fact", "constrained", "narrative"];
const REPAIR_KINDS: readonly RepairKind[] = ["none", "safe_coerce", "suggest_alias"];
const SOFT_FIELD_ERRORS = {
  group: "soft field annotation group must be a non-empty string",
  instruction: "soft field annotation instruction must be a non-empty string",
  order: "soft field annotation order must be an integer",
  owner: "soft field annotation owner must be one of: agent, postprocess, system, human",
  tier: "soft field annotation tier must be one of: hard_fact, constrained, narrative",
  repair: "soft field annotation repair must be one of: none, safe_coerce, suggest_alias",
  examples: "soft field annotation examples must be an array",
  aliases: "soft field annotation aliases must be an object of string arrays",
} as const;

export interface SoftFieldOptions {
  description: string;
  group: string;
  owner?: SoftOwner;
  tier?: SoftTier;
  order?: number;
  instruction?: string;
  examples?: unknown[];
  aliases?: Record<string, string[]>;
  repair?: RepairKind;
}

function isAliasRecord(value: unknown): value is Record<string, string[]> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) return false;
  return Object.values(value).every(
    (aliases) => Array.isArray(aliases) && aliases.every((alias) => typeof alias === "string"),
  );
}

function validateSoftFieldOptions(options: SoftFieldOptions): void {
  if (typeof options.group !== "string" || options.group.length === 0) {
    throw new TypeError(SOFT_FIELD_ERRORS.group);
  }
  if (
    options.instruction !== undefined &&
    (typeof options.instruction !== "string" || options.instruction.length === 0)
  ) {
    throw new TypeError(SOFT_FIELD_ERRORS.instruction);
  }
  if (
    options.order !== undefined &&
    (typeof options.order !== "number" || !Number.isInteger(options.order))
  ) {
    throw new TypeError(SOFT_FIELD_ERRORS.order);
  }
  if (options.owner !== undefined && !SOFT_OWNERS.includes(options.owner)) {
    throw new TypeError(SOFT_FIELD_ERRORS.owner);
  }
  if (options.tier !== undefined && !SOFT_TIERS.includes(options.tier)) {
    throw new TypeError(SOFT_FIELD_ERRORS.tier);
  }
  if (options.repair !== undefined && !REPAIR_KINDS.includes(options.repair)) {
    throw new TypeError(SOFT_FIELD_ERRORS.repair);
  }
  if (options.examples !== undefined && !Array.isArray(options.examples)) {
    throw new TypeError(SOFT_FIELD_ERRORS.examples);
  }
  if (options.aliases !== undefined && !isAliasRecord(options.aliases)) {
    throw new TypeError(SOFT_FIELD_ERRORS.aliases);
  }
}

/** Build the `x-softschema` annotation block with the same omit-empty rules as Python. */
export function softFieldMeta(options: SoftFieldOptions): Record<string, unknown> {
  validateSoftFieldOptions(options);
  const meta: Record<string, unknown> = { group: options.group };
  if (options.order !== undefined) meta.order = options.order === 0 ? 0 : options.order;
  if (options.tier !== undefined) meta.tier = options.tier;
  meta.owner = options.owner ?? "agent";
  if (options.instruction !== undefined) meta.instruction = options.instruction;
  if (options.examples && options.examples.length > 0) meta.examples = options.examples;
  if (options.aliases && Object.keys(options.aliases).length > 0) meta.aliases = options.aliases;
  const repair = options.repair ?? "none";
  if (repair !== "none") meta.repair = repair;
  return meta;
}

/** Attach softschema authoring metadata to a Zod type (idiomatic mirror of `SoftField`). */
export function softField<T extends z.ZodType>(schema: T, options: SoftFieldOptions): T {
  return schema.meta({
    description: options.description,
    "x-softschema": softFieldMeta(options),
  }) as T;
}
