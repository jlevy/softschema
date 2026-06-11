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

/** Build the `x-softschema` annotation block with the same omit-empty rules as Python. */
export function softFieldMeta(options: SoftFieldOptions): Record<string, unknown> {
  const meta: Record<string, unknown> = { group: options.group };
  if (options.order !== undefined) meta.order = options.order;
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
