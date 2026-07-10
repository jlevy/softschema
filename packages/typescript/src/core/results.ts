/** JSON-compatible normalized validation result contracts. */

import type { SchemaInvalidErrorRecord, StructuralErrorRecord } from "../errors.js";

export type SchemaResource = boolean | Record<string, unknown>;
export type SchemaResources = Readonly<Record<string, SchemaResource>>;

export interface StructuralResult {
  ok: boolean;
  errors: (StructuralErrorRecord | SchemaInvalidErrorRecord | Record<string, unknown>)[];
  engine: string;
  skipped_reason: string | null;
}

export interface SemanticResult {
  ok: boolean;
  errors: Record<string, unknown>[];
  skipped_reason: string | null;
}

export interface ValidationResult {
  structural: StructuralResult;
  semantic: SemanticResult;
}

export interface ArtifactValidationResult {
  ok: boolean;
  output: Record<string, unknown>;
}

export type MetadataMode = "enforced" | "advisory";

export interface RawFrontmatter {
  hasFence: boolean;
  value: unknown;
}

export type ArtifactParseReason = "frontmatter" | "syntax" | "root" | "value_domain";
export type ArtifactInputReason = "not_found" | "unreadable" | "directory_requires_recursive";
