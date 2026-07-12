/**
 * Per-field `x-softschema` annotations for Zod source schemas: the idiomatic mirror of
 * Python's `SoftField`. Wraps a Zod type with `.meta()` carrying `description` and an
 * `x-softschema` block; the compiler propagates it verbatim into the compiled JSON Schema
 * as a per-property `x-softschema:` block. The emitted block and omit-empty rules match
 * the Python implementation exactly.
 */
import type { z } from "zod";
import { checkPortableValue } from "./portable.js";

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
  if (!options || typeof options.description !== "string" || options.description.length === 0) {
    throw new TypeError("description must be a non-empty string");
  }
  if (typeof options.group !== "string" || options.group.length === 0) {
    throw new TypeError("group must be a non-empty string");
  }
  if (options.order !== undefined && !Number.isInteger(options.order)) {
    throw new TypeError("order must be an integer");
  }
  if (
    options.instruction !== undefined &&
    (typeof options.instruction !== "string" || options.instruction.length === 0)
  ) {
    throw new TypeError("instruction must be a non-empty string");
  }
  if (options.examples !== undefined && !Array.isArray(options.examples)) {
    throw new TypeError("examples must be an array");
  }
  if (
    options.aliases !== undefined &&
    (options.aliases === null ||
      typeof options.aliases !== "object" ||
      Array.isArray(options.aliases))
  ) {
    throw new TypeError("aliases must be a mapping");
  }
  if (
    options.owner !== undefined &&
    !["agent", "postprocess", "system", "human"].includes(options.owner)
  ) {
    throw new TypeError("owner is invalid");
  }
  if (
    options.tier !== undefined &&
    !["hard_fact", "constrained", "narrative"].includes(options.tier)
  ) {
    throw new TypeError("tier is invalid");
  }
  if (
    options.repair !== undefined &&
    !["none", "safe_coerce", "suggest_alias"].includes(options.repair)
  ) {
    throw new TypeError("repair is invalid");
  }
  checkPortableValue({ examples: options.examples ?? [], aliases: options.aliases ?? {} });
  for (const [name, values] of Object.entries(options.aliases ?? {})) {
    if (
      name.length === 0 ||
      !Array.isArray(values) ||
      values.length === 0 ||
      values.some((value) => typeof value !== "string" || value.length === 0)
    ) {
      throw new TypeError("aliases require non-empty names and values");
    }
  }
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
