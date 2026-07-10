/**
 * Read-only navigation over a compiled JSON Schema: the idiomatic mirror of the
 * Python `SchemaView`. One reader for every downstream consumer (generated sections, QA,
 * agent prompts) so $ref resolution and x-softschema lookup never diverge.
 */
import { readBoundedBytes } from "./bounded-file.js";
import { isMapping } from "./guards.js";
import { validateContractId, validateSchemaId } from "./models.js";
import {
  parsePortableYaml,
  resolveValidationLimits,
  type ValidationLimitOverrides,
} from "./yaml-value-domain.js";

const X_SOFTSCHEMA = "x-softschema";
const ANNOTATION_KEYWORDS = new Set([
  "$comment",
  "contentEncoding",
  "contentMediaType",
  "default",
  "deprecated",
  "description",
  "examples",
  "format",
  "readOnly",
  "title",
  "writeOnly",
  X_SOFTSCHEMA,
]);
const NULL_SCHEMA_KEYWORDS = new Set([...ANNOTATION_KEYWORDS, "type"]);
const REFERENCE_SCHEMA_KEYWORDS = new Set([...ANNOTATION_KEYWORDS, "$ref"]);

type SchemaNode = Record<string, unknown>;

/** One leaf-ish property in a compiled JSON Schema bundle. */
export interface FieldInfo {
  /** JSON Pointer (RFC 6901) relative to the root schema document. */
  pointer: string;
  name: string;
  /** One exact type, or null for a genuine union or unspecified type. */
  jsonType: string | null;
  /** One exact string enum, or null for a genuine union or absent enum. */
  enum: string[] | null;
  required: boolean;
  description: string | null;
  /** The field's per-property `x-softschema` block (empty when unannotated). */
  softmeta: Record<string, unknown>;
}

function escapePointerSegment(segment: string): string {
  return segment.replace(/~/g, "~0").replace(/\//g, "~1");
}

function unescapePointerSegment(segment: string): string {
  return segment.replace(/~1/g, "/").replace(/~0/g, "~");
}

function deepSnapshot<T>(value: T): T {
  return structuredClone(value);
}

function resolveRef(schema: SchemaNode, ref: string): SchemaNode | null {
  if (!ref.startsWith("#/")) return null;
  let cur: unknown = schema;
  for (const rawSegment of ref.slice(2).split("/")) {
    const segment = unescapePointerSegment(rawSegment);
    if (isMapping(cur) && segment in cur) {
      cur = cur[segment];
    } else {
      return null;
    }
  }
  return isMapping(cur) ? cur : null;
}

function isExactNullSchema(value: unknown): boolean {
  return (
    isMapping(value) &&
    value.type === "null" &&
    Object.keys(value).every((key) => NULL_SCHEMA_KEYWORDS.has(key))
  );
}

function exactNullableValueBranch(prop: SchemaNode): SchemaNode | null {
  const present = ["anyOf", "oneOf"].filter((keyword) => Object.hasOwn(prop, keyword));
  if (present.length !== 1) return null;
  if (!Object.keys(prop).every((key) => ANNOTATION_KEYWORDS.has(key) || key === present[0])) {
    return null;
  }
  const union = prop[present[0] as "anyOf" | "oneOf"];
  if (!Array.isArray(union) || union.length !== 2) return null;
  const nullIndexes = union.flatMap((entry, index) => (isExactNullSchema(entry) ? [index] : []));
  if (nullIndexes.length !== 1) return null;
  const branch = union[1 - (nullIndexes[0] as number)];
  return isMapping(branch) ? branch : null;
}

function schemaExcludesNull(schema: SchemaNode, root: SchemaNode, seenRefs: Set<string>): boolean {
  const schemaType = schema.type;
  if (typeof schemaType === "string") return schemaType !== "null";
  if (Array.isArray(schemaType) && schemaType.length > 0) return !schemaType.includes("null");
  if (Array.isArray(schema.enum)) return !schema.enum.includes(null);
  if (Object.hasOwn(schema, "const")) return schema.const !== null;
  const ref = schema.$ref;
  if (typeof ref === "string" && !seenRefs.has(ref)) {
    const target = resolveRef(root, ref);
    if (target !== null) return schemaExcludesNull(target, root, new Set(seenRefs).add(ref));
  }
  for (const keyword of ["anyOf", "oneOf"] as const) {
    const union = schema[keyword];
    if (Array.isArray(union) && union.length > 0) {
      return union.every(
        (branch) => isMapping(branch) && schemaExcludesNull(branch, root, seenRefs),
      );
    }
  }
  const allOf = schema.allOf;
  if (Array.isArray(allOf)) {
    return allOf.some((branch) => isMapping(branch) && schemaExcludesNull(branch, root, seenRefs));
  }
  return false;
}

function exactNullableRef(
  prop: SchemaNode,
  root: SchemaNode,
): { ref: string; branch: SchemaNode } | null {
  const branch = exactNullableValueBranch(prop);
  if (
    branch === null ||
    !Object.keys(branch).every((key) => REFERENCE_SCHEMA_KEYWORDS.has(key)) ||
    typeof branch.$ref !== "string"
  ) {
    return null;
  }
  const target = resolveRef(root, branch.$ref);
  if (target === null || !schemaExcludesNull(target, root, new Set())) return null;
  return { ref: branch.$ref, branch };
}

function extractType(prop: SchemaNode): string | null {
  if (Object.hasOwn(prop, "$ref")) return null;
  const t = prop.type;
  if (typeof t === "string") return t;
  if (Array.isArray(t)) {
    const nonNull = t.filter((entry) => typeof entry === "string" && entry !== "null");
    if (
      t.every((entry) => typeof entry === "string") &&
      t.length >= 1 &&
      t.length <= 2 &&
      new Set(t).size === t.length &&
      nonNull.length === 1
    ) {
      return nonNull[0] as string;
    }
  }
  const branch = exactNullableValueBranch(prop);
  if (branch !== null && typeof branch.type === "string" && branch.type !== "null") {
    return branch.type;
  }
  return null;
}

function extractEnum(prop: SchemaNode): string[] | null {
  if (Object.hasOwn(prop, "$ref")) return null;
  const enumValue = prop.enum;
  if (Array.isArray(enumValue) && enumValue.every((v) => typeof v === "string")) {
    return [...(enumValue as string[])];
  }
  const branch = exactNullableValueBranch(prop);
  if (
    branch !== null &&
    Array.isArray(branch.enum) &&
    branch.enum.every((value) => typeof value === "string")
  ) {
    return [...(branch.enum as string[])];
  }
  return null;
}

function extractSoftmeta(prop: SchemaNode): Record<string, unknown> {
  const meta = prop[X_SOFTSCHEMA];
  return isMapping(meta) ? deepSnapshot(meta) : {};
}

export class SchemaView {
  private readonly schema: SchemaNode;

  /** Snapshot an already normalized JSON-compatible schema mapping. */
  constructor(schema: SchemaNode) {
    this.schema = deepSnapshot(schema);
  }

  /**
   * Load a compiled YAML or JSON schema through the portable-value boundary.
   * Filesystem, UTF-8, portable-YAML, and non-mapping-root failures are thrown.
   */
  static load(schemaPath: string, validationLimits: ValidationLimitOverrides = {}): SchemaView {
    const limits = resolveValidationLimits(validationLimits);
    const encoded = readBoundedBytes(schemaPath, limits.maxResourceBytes);
    const text = new TextDecoder("utf-8", { fatal: true }).decode(encoded);
    const data = parsePortableYaml(text, limits, { encodedSize: encoded.byteLength });
    if (!isMapping(data)) {
      throw new Error(`schema at ${schemaPath} is not a mapping at the root`);
    }
    return new SchemaView(data);
  }

  get raw(): SchemaNode {
    return deepSnapshot(this.schema);
  }

  get rootSoftmeta(): Record<string, unknown> {
    const meta = this.schema[X_SOFTSCHEMA];
    return isMapping(meta) ? deepSnapshot(meta) : {};
  }

  get contractId(): string | null {
    const metaContract = this.rootSoftmeta.contract;
    if (typeof metaContract === "string") {
      try {
        return validateContractId(metaContract);
      } catch {
        return null;
      }
    }
    if (typeof this.schema.$id === "string") {
      try {
        return validateContractId(this.schema.$id);
      } catch {
        // Only a logical legacy-0.2 `$id` is a contract fallback.
      }
    }
    return null;
  }

  get schemaId(): string | null {
    if (typeof this.schema.$id === "string") {
      try {
        return validateSchemaId(this.schema.$id);
      } catch {
        // Invalid or legacy logical IDs are not JSON Schema resource identities.
      }
    }
    return null;
  }

  get schemaSha256(): string | null {
    const value = this.rootSoftmeta.schema_sha256;
    return typeof value === "string" ? value : null;
  }

  iterFields(includeRefs = true): FieldInfo[] {
    const out: FieldInfo[] = [];
    this.walk(this.schema, "", new Set(), includeRefs, out);
    return out;
  }

  /** Return one field; throws `Error` when the pointer does not resolve. */
  field(pointer: string): FieldInfo {
    const found = this.iterFields().find((info) => info.pointer === pointer);
    if (found === undefined) throw new Error(`no field at pointer ${JSON.stringify(pointer)}`);
    return found;
  }

  enumValues(pointer: string): string[] | null {
    return this.field(pointer).enum;
  }

  softmeta(pointer: string): Record<string, unknown> {
    return deepSnapshot(this.field(pointer).softmeta);
  }

  fieldsByGroup(group: string): FieldInfo[] {
    return this.iterFields().filter((f) => f.softmeta.group === group);
  }

  fieldsByOwner(owner: string): FieldInfo[] {
    return this.iterFields().filter((f) => f.softmeta.owner === owner);
  }

  fieldsByTier(tier: string): FieldInfo[] {
    return this.iterFields().filter((f) => f.softmeta.tier === tier);
  }

  private walk(
    node: SchemaNode,
    basePointer: string,
    seenRefs: Set<string>,
    includeRefs: boolean,
    out: FieldInfo[],
  ): void {
    const properties = node.properties;
    if (!isMapping(properties)) return;
    const requiredSet = new Set(Array.isArray(node.required) ? (node.required as string[]) : []);
    for (const [name, rawProp] of Object.entries(properties)) {
      if (!isMapping(rawProp)) continue;
      const { node: prop, ref } = this.maybeResolveRef(rawProp, seenRefs, includeRefs);
      const pointer = `${basePointer}/properties/${escapePointerSegment(name)}`;
      out.push({
        pointer,
        name,
        jsonType: extractType(prop),
        enum: extractEnum(prop),
        required: requiredSet.has(name),
        description: typeof prop.description === "string" ? prop.description : null,
        softmeta: extractSoftmeta(prop),
      });
      if (includeRefs && isMapping(prop.properties)) {
        // Carry the just-followed $ref down the recursion path so a cyclic schema
        // (A -> B -> A) terminates. The augmented set is scoped to this path only, so
        // a $def reused by sibling fields (e.g. Address) still expands under each.
        const nextSeen = ref !== null ? new Set(seenRefs).add(ref) : seenRefs;
        this.walk(prop, pointer, nextSeen, includeRefs, out);
      }
    }
  }

  private maybeResolveRef(
    prop: SchemaNode,
    seenRefs: Set<string>,
    includeRefs: boolean,
  ): { node: SchemaNode; ref: string | null } {
    if (!includeRefs) return { node: prop, ref: null };
    let ref = typeof prop.$ref === "string" ? prop.$ref : null;
    let refBranch: SchemaNode | null = null;
    if (ref !== null) {
      if (!Object.keys(prop).every((key) => REFERENCE_SCHEMA_KEYWORDS.has(key))) {
        return { node: prop, ref: null };
      }
    } else {
      const nullable = exactNullableRef(prop, this.schema);
      if (nullable === null) return { node: prop, ref: null };
      ref = nullable.ref;
      refBranch = nullable.branch;
    }
    if (ref === null || seenRefs.has(ref)) return { node: prop, ref: null };
    const target = resolveRef(this.schema, ref);
    if (target === null) return { node: prop, ref: null };
    const merged = { ...target };
    for (const source of [refBranch, prop]) {
      if (source !== null) {
        for (const [key, value] of Object.entries(source)) {
          if (ANNOTATION_KEYWORDS.has(key)) merged[key] = value;
        }
      }
    }
    return { node: merged, ref };
  }
}
