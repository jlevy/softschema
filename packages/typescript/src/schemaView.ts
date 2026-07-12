/**
 * Read-only navigation over a compiled JSON Schema: the idiomatic mirror of the
 * Python `SchemaView`. One reader for every downstream consumer (generated sections, QA,
 * agent prompts) so $ref resolution and x-softschema lookup never diverge.
 */
import { isMapping } from "./guards.js";
import { checkContractId } from "./models.js";
import { parsePortableYaml, readUtf8 } from "./portable.js";

const X_SOFTSCHEMA = "x-softschema";

type SchemaNode = Record<string, unknown>;

/** One leaf-ish property in a compiled JSON Schema bundle. */
export interface FieldInfo {
  /** JSON Pointer (RFC 6901) relative to the root schema document. */
  pointer: string;
  name: string;
  jsonType: string | null;
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

function refFromAnyOf(prop: SchemaNode): string | null {
  const branch = nullableValueBranch(prop);
  return branch !== null && typeof branch.$ref === "string" ? branch.$ref : null;
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

function extractType(prop: SchemaNode): string | null {
  const t = prop.type;
  if (typeof t === "string") return t;
  if (Array.isArray(t) && t.length === 2 && t.filter((entry) => entry === "null").length === 1) {
    const nonNull = t.filter((e) => e !== "null");
    if (nonNull.length === 1 && typeof nonNull[0] === "string") return nonNull[0];
  }
  const branch = nullableValueBranch(prop);
  if (branch !== null && typeof branch.type === "string" && branch.type !== "null")
    return branch.type;
  return null;
}

function extractEnum(prop: SchemaNode): string[] | null {
  const enumValue = prop.enum;
  if (Array.isArray(enumValue) && enumValue.every((v) => typeof v === "string")) {
    return [...(enumValue as string[])];
  }
  const branch = nullableValueBranch(prop);
  if (
    branch !== null &&
    Array.isArray(branch.enum) &&
    branch.enum.every((v) => typeof v === "string")
  ) {
    return [...(branch.enum as string[])];
  }
  return null;
}

function nullableValueBranch(prop: SchemaNode): SchemaNode | null {
  const anyOf = prop.anyOf;
  if (!Array.isArray(anyOf) || anyOf.length !== 2) return null;
  const nulls = anyOf.filter(
    (entry) => isMapping(entry) && Object.keys(entry).length === 1 && entry.type === "null",
  );
  const others = anyOf.filter(
    (entry) => isMapping(entry) && !(Object.keys(entry).length === 1 && entry.type === "null"),
  );
  return nulls.length === 1 && others.length === 1 ? (others[0] as SchemaNode) : null;
}

function extractSoftmeta(prop: SchemaNode): Record<string, unknown> {
  const meta = prop[X_SOFTSCHEMA];
  return isMapping(meta) ? { ...meta } : {};
}

export class SchemaView {
  private readonly schema: SchemaNode;

  constructor(schema: SchemaNode) {
    this.schema = structuredClone(schema);
  }

  /** Load a YAML or JSON compiled schema from disk. */
  static load(schemaPath: string): SchemaView {
    const data = parsePortableYaml(readUtf8(schemaPath));
    if (!isMapping(data)) {
      throw new Error(`schema at ${schemaPath} is not a mapping at the root`);
    }
    return new SchemaView(data);
  }

  get raw(): SchemaNode {
    return structuredClone(this.schema);
  }

  get rootSoftmeta(): Record<string, unknown> {
    const meta = this.schema[X_SOFTSCHEMA];
    return isMapping(meta) ? { ...meta } : {};
  }

  get contractId(): string | null {
    const metaContract = this.rootSoftmeta.contract;
    return typeof metaContract === "string" ? checkContractId(metaContract) : null;
  }

  get schemaId(): string | null {
    return typeof this.schema.$id === "string" ? this.schema.$id : null;
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

  field(pointer: string): FieldInfo {
    const found = this.iterFields().find((info) => info.pointer === pointer);
    if (found === undefined) throw new Error(`no field at pointer ${JSON.stringify(pointer)}`);
    return found;
  }

  enumValues(pointer: string): string[] | null {
    return this.field(pointer).enum;
  }

  softmeta(pointer: string): Record<string, unknown> {
    return { ...this.field(pointer).softmeta };
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
    if (ref === null) ref = refFromAnyOf(prop);
    if (ref === null || seenRefs.has(ref)) return { node: prop, ref: null };
    const target = resolveRef(this.schema, ref);
    return target !== null
      ? {
          node: {
            ...target,
            ...Object.fromEntries(Object.entries(prop).filter(([key]) => key !== "$ref")),
          },
          ref,
        }
      : { node: prop, ref: null };
  }
}
