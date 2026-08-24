/**
 * Apply `status: enforced` undeclared-property rules to Draft 2020-12 schemas.
 *
 * "Closure" below means rejecting a present object property when no successful
 * applicable schema evaluates its value at that object location.
 */

import { isMapping } from "./guards.js";

type Json = unknown;
type Schema = Record<string, Json>;
type FragmentContext = "same_instance" | "nested_instance" | null;

const ROOT_RETRIEVAL_URI = "https://softschema.invalid/__root__";

const NAME_MAP_KEYWORDS = new Set([
  "properties",
  "$defs",
  "definitions",
  "patternProperties",
  "dependentSchemas",
]);
const SCHEMA_LIST_KEYWORDS = new Set(["anyOf", "oneOf", "allOf", "prefixItems"]);
const SCHEMA_KEYWORDS = new Set([
  "items",
  "additionalProperties",
  "unevaluatedProperties",
  "unevaluatedItems",
  "not",
  "if",
  "then",
  "else",
  "contains",
  "propertyNames",
  "contentSchema",
]);
const DEFINITION_KEYWORDS = new Set(["$defs", "definitions"]);
const IN_PLACE_MAP_KEYWORDS = new Set(["dependentSchemas"]);
const IN_PLACE_LIST_KEYWORDS = new Set(["allOf", "anyOf", "oneOf"]);
const IN_PLACE_SINGLE_KEYWORDS = new Set(["if", "then", "else", "not"]);
const ANNOTATING_IN_PLACE_KEYWORDS = new Set([
  ...IN_PLACE_MAP_KEYWORDS,
  ...IN_PLACE_LIST_KEYWORDS,
  "if",
  "then",
  "else",
]);
const EXPLICIT_CLOSURE_KEYWORDS = ["additionalProperties", "unevaluatedProperties"];
const CONTEXT_SENSITIVE_REFERENCE_KEYWORDS = new Set([
  ...IN_PLACE_MAP_KEYWORDS,
  ...IN_PLACE_LIST_KEYWORDS,
  ...IN_PLACE_SINGLE_KEYWORDS,
  "contains",
]);
const REFERENCE_NONVALIDATION_SIBLINGS = new Set([
  "$anchor",
  "$comment",
  "$defs",
  "$id",
  "$schema",
  "default",
  "definitions",
  "deprecated",
  "description",
  "examples",
  "readOnly",
  "title",
  "writeOnly",
]);
const THEN = "then";

export class EnforcementUnsupportedError extends Error {
  readonly reason: string;
  readonly schemaPath: string;

  constructor(reason: string, message: string, schemaPath: string) {
    super(message);
    this.reason = reason;
    this.schemaPath = schemaPath;
  }
}

export class SchemaGraphError extends Error {
  readonly reason: string;

  constructor(reason: string, message: string) {
    super(message);
    this.reason = reason;
  }
}

export interface PreparedSchemaGraph {
  root: Schema;
  resources: Record<string, Schema>;
}

interface NodeInfo {
  baseUri: string;
  resourceUri: string;
  pointer: string;
  path: (string | number)[];
  reusableRoot: boolean;
  embeddedDirectResource: boolean;
}

interface PropertyEvaluators {
  names: Set<string>;
  patterns: Set<string>;
  wildcard: boolean;
}

function pointerToken(value: string | number): string {
  return String(value).replace(/~/g, "~0").replace(/\//g, "~1");
}

function appendPointer(pointer: string, ...parts: (string | number)[]): string {
  const suffix = parts.map(pointerToken).join("/");
  return suffix.length > 0 ? `${pointer}/${suffix}` : pointer;
}

function displayPath(path: (string | number)[]): string {
  return `#${appendPointer("", ...path)}`;
}

function splitFragment(uri: string): [string, string] {
  const index = uri.indexOf("#");
  return index < 0 ? [uri, ""] : [uri.slice(0, index), uri.slice(index + 1)];
}

function normalizeUri(uri: string): string {
  const [base, encodedFragment] = splitFragment(uri);
  if (encodedFragment.length === 0) return base;
  try {
    return `${base}#${decodeURIComponent(encodedFragment)}`;
  } catch (error) {
    throw new SchemaGraphError("reference", `invalid URI fragment in ${uri}: ${String(error)}`);
  }
}

function resolveUri(baseUri: string, reference: string): string {
  if (reference.startsWith("#")) {
    return normalizeUri(`${splitFragment(baseUri)[0]}${reference}`);
  }
  try {
    if (/^[A-Za-z][A-Za-z0-9+.-]*:/u.test(reference)) return normalizeUri(reference);
    return normalizeUri(new URL(reference, baseUri).href);
  } catch {
    throw new SchemaGraphError(
      "reference",
      `relative reference ${JSON.stringify(reference)} cannot be resolved against ${JSON.stringify(baseUri)}`,
    );
  }
}

class SchemaGraph {
  private readonly targets = new Map<string, Json>();
  private readonly resourceRoots = new Map<string, Json>();
  private readonly infos = new Map<Schema, NodeInfo>();
  private readonly inferredClosures = new Set<Schema>();
  // Cache only positive reachability; a cycle back-edge can make an interim false result
  // path-dependent while the outer traversal is still in progress.
  private readonly closureReachable = new Set<Schema>();

  constructor(root: Schema, resources: Record<string, Schema>) {
    this.visit(root, {
      baseUri: ROOT_RETRIEVAL_URI,
      resourceUri: ROOT_RETRIEVAL_URI,
      pointer: "",
      path: [],
      reusableRoot: false,
      mainRoot: true,
    });
    for (const [key, resource] of Object.entries(resources)) {
      if (!/^[A-Za-z][A-Za-z0-9+.-]*:/u.test(key) || key.includes("#")) {
        throw new SchemaGraphError(
          "resource_identity",
          `supplied resource key must be an absolute URI without a fragment: ${JSON.stringify(key)}`,
        );
      }
      const initialUri = normalizeUri(key);
      if (typeof resource.$id === "string") {
        const resolvedId = splitFragment(resolveUri(initialUri, resource.$id))[0];
        if (resolvedId !== splitFragment(initialUri)[0]) {
          throw new SchemaGraphError(
            "resource_identity",
            `supplied resource $id ${JSON.stringify(resource.$id)} does not match its key ${JSON.stringify(key)}`,
          );
        }
      }
      this.visit(resource, {
        baseUri: initialUri,
        resourceUri: splitFragment(initialUri)[0],
        pointer: "",
        path: ["resources", key],
        reusableRoot: true,
        mainRoot: false,
      });
    }
    this.checkReferenceTargets();
  }

  private registerTarget(uri: string, node: Json): void {
    const normalized = normalizeUri(uri);
    if (this.targets.has(normalized) && this.targets.get(normalized) !== node) {
      throw new SchemaGraphError("resource_identity", `duplicate schema target identity: ${uri}`);
    }
    this.targets.set(normalized, node);
  }

  private registerResource(uri: string, node: Json): void {
    const normalized = splitFragment(normalizeUri(uri))[0];
    if (this.resourceRoots.has(normalized) && this.resourceRoots.get(normalized) !== node) {
      throw new SchemaGraphError(
        "resource_identity",
        `duplicate schema resource identity: ${normalized}`,
      );
    }
    this.resourceRoots.set(normalized, node);
    this.registerTarget(normalized, node);
    this.registerTarget(`${normalized}#`, node);
  }

  private visit(
    node: Json,
    location: Omit<NodeInfo, "embeddedDirectResource"> & { mainRoot: boolean },
  ): void {
    if (isMapping(node)) {
      const previous = this.infos.get(node);
      if (previous !== undefined) {
        throw new SchemaGraphError(
          "shared_subschema",
          `schema object at ${displayPath(location.path)} is shared with ${displayPath(previous.path)}; deep-copy shared subschemas before validation`,
        );
      }
    }
    this.registerTarget(`${location.resourceUri}#${location.pointer}`, node);
    if (!isMapping(node)) return;

    let baseUri = location.baseUri;
    let resourceUri = location.resourceUri;
    let pointer = location.pointer;
    let reusableRoot = location.reusableRoot;
    let embeddedDirectResource = false;
    if (typeof node.$id === "string") {
      baseUri = resolveUri(baseUri, node.$id);
      resourceUri = splitFragment(baseUri)[0];
      pointer = "";
      embeddedDirectResource = !location.mainRoot && !location.reusableRoot;
      reusableRoot = reusableRoot || !location.mainRoot;
      this.registerResource(resourceUri, node);
    } else if (pointer === "") {
      this.registerResource(resourceUri, node);
    }

    if ("$dynamicRef" in node || "$dynamicAnchor" in node) {
      throw new EnforcementUnsupportedError(
        "dynamic_reference",
        "the enforced profile does not support $dynamicRef or $dynamicAnchor",
        displayPath(location.path),
      );
    }

    this.infos.set(node, {
      baseUri,
      resourceUri,
      pointer,
      path: location.path,
      reusableRoot,
      embeddedDirectResource,
    });
    if (typeof node.$anchor === "string") {
      this.registerTarget(`${resourceUri}#${node.$anchor}`, node);
    }

    for (const [key, value] of Object.entries(node)) {
      if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
        for (const [name, child] of Object.entries(value)) {
          this.visit(child, {
            baseUri,
            resourceUri,
            pointer: appendPointer(pointer, key, name),
            path: [...location.path, key, name],
            reusableRoot: DEFINITION_KEYWORDS.has(key),
            mainRoot: false,
          });
        }
      } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
        value.forEach((child, index) => {
          this.visit(child, {
            baseUri,
            resourceUri,
            pointer: appendPointer(pointer, key, index),
            path: [...location.path, key, index],
            reusableRoot: false,
            mainRoot: false,
          });
        });
      } else if (SCHEMA_KEYWORDS.has(key) && (isMapping(value) || typeof value === "boolean")) {
        this.visit(value, {
          baseUri,
          resourceUri,
          pointer: appendPointer(pointer, key),
          path: [...location.path, key],
          reusableRoot: false,
          mainRoot: false,
        });
      }
    }
  }

  private resolveRef(node: Schema, reference: string): Json {
    const info = this.infos.get(node) as NodeInfo;
    const uri = resolveUri(info.baseUri, reference);
    const target =
      this.targets.get(uri) ?? (!uri.includes("#") ? this.targets.get(`${uri}#`) : undefined);
    if (target === undefined) {
      throw new SchemaGraphError("reference", `unresolved reference: ${reference}`);
    }
    return target;
  }

  declaresProperties(node: Json, seen: Set<Schema> = new Set()): boolean {
    if (!isMapping(node)) return false;
    if (isMapping(node.properties)) return true;
    if (isMapping(node.patternProperties) && Object.keys(node.patternProperties).length > 0) {
      return true;
    }
    if (seen.has(node)) return false;
    const nextSeen = new Set(seen).add(node);
    if (
      typeof node.$ref === "string" &&
      this.declaresProperties(this.resolveRef(node, node.$ref), nextSeen)
    ) {
      return true;
    }
    for (const key of IN_PLACE_LIST_KEYWORDS) {
      const value = node[key];
      if (Array.isArray(value) && value.some((child) => this.declaresProperties(child, nextSeen))) {
        return true;
      }
    }
    if (
      isMapping(node.dependentSchemas) &&
      Object.values(node.dependentSchemas).some((child) => this.declaresProperties(child, nextSeen))
    ) {
      return true;
    }
    const conditionalKeys = "if" in node ? ["then", "else"] : [];
    return conditionalKeys.some((key) => this.declaresProperties(node[key], nextSeen));
  }

  private propertyEvaluators(
    node: Json,
    options: { includeAlternatives: boolean; includeConditionals: boolean },
    seen: Set<Schema> = new Set(),
  ): PropertyEvaluators {
    if (!isMapping(node) || seen.has(node)) {
      return { names: new Set(), patterns: new Set(), wildcard: false };
    }
    const nextSeen = new Set(seen).add(node);
    const names = new Set(isMapping(node.properties) ? Object.keys(node.properties) : []);
    const patterns = new Set(
      isMapping(node.patternProperties) ? Object.keys(node.patternProperties) : [],
    );
    let wildcard = EXPLICIT_CLOSURE_KEYWORDS.some((key) => key in node);
    const children: Json[] = [];
    if (typeof node.$ref === "string") children.push(this.resolveRef(node, node.$ref));
    if (Array.isArray(node.allOf)) children.push(...node.allOf);
    if (options.includeAlternatives) {
      for (const key of ["anyOf", "oneOf"]) {
        const value = node[key];
        if (Array.isArray(value)) children.push(...value);
      }
      if (isMapping(node.dependentSchemas)) children.push(...Object.values(node.dependentSchemas));
    }
    if (options.includeConditionals && "if" in node) {
      children.push(node.if, node[THEN], node.else);
    }
    for (const child of children) {
      const evaluators = this.propertyEvaluators(child, options, nextSeen);
      for (const name of evaluators.names) names.add(name);
      for (const pattern of evaluators.patterns) patterns.add(pattern);
      wildcard ||= evaluators.wildcard;
    }
    return { names, patterns, wildcard };
  }

  private conditionalMatcherEvaluators(
    node: Json,
    seen: Set<Schema> = new Set(),
  ): PropertyEvaluators {
    if (!isMapping(node) || seen.has(node)) {
      return { names: new Set(), patterns: new Set(), wildcard: false };
    }
    const nextSeen = new Set(seen).add(node);
    const result: PropertyEvaluators = {
      names: new Set(),
      patterns: new Set(),
      wildcard: false,
    };
    if ("if" in node) {
      const matcher = this.propertyEvaluators(node.if, {
        includeAlternatives: true,
        includeConditionals: true,
      });
      for (const name of matcher.names) result.names.add(name);
      for (const pattern of matcher.patterns) result.patterns.add(pattern);
      result.wildcard ||= matcher.wildcard;
    }

    const children: Json[] = [];
    if (typeof node.$ref === "string") children.push(this.resolveRef(node, node.$ref));
    for (const key of IN_PLACE_LIST_KEYWORDS) {
      const value = node[key];
      if (Array.isArray(value)) children.push(...value);
    }
    if (isMapping(node.dependentSchemas)) children.push(...Object.values(node.dependentSchemas));
    if ("if" in node) children.push(node[THEN], node.else);
    for (const child of children) {
      const matcher = this.conditionalMatcherEvaluators(child, nextSeen);
      for (const name of matcher.names) result.names.add(name);
      for (const pattern of matcher.patterns) result.patterns.add(pattern);
      result.wildcard ||= matcher.wildcard;
    }
    return result;
  }

  private conditionMatchersAreCovered(node: Schema): boolean {
    const matcher = this.conditionalMatcherEvaluators(node);
    if (matcher.names.size === 0 && matcher.patterns.size === 0 && !matcher.wildcard) return true;
    const covered = this.propertyEvaluators(node, {
      includeAlternatives: false,
      includeConditionals: false,
    });
    if (matcher.wildcard && !covered.wildcard) return false;
    for (const name of matcher.names) {
      if (covered.names.has(name)) continue;
      if ([...covered.patterns].some((pattern) => new RegExp(pattern, "u").test(name))) continue;
      return false;
    }
    return [...matcher.patterns].every((pattern) => covered.patterns.has(pattern));
  }

  private evaluatesObjectProperties(node: Json): boolean {
    const evaluators = this.propertyEvaluators(node, {
      includeAlternatives: true,
      includeConditionals: true,
    });
    return evaluators.names.size > 0 || evaluators.patterns.size > 0 || evaluators.wildcard;
  }

  private checkChildEvaluatorOverlaps(node: Schema): void {
    if (this.evaluatesObjectProperties(node.contains)) {
      const itemSchemas: [string, Json][] = [];
      if ("items" in node) {
        itemSchemas.push(["items", node.items]);
      }
      if (Array.isArray(node.prefixItems)) {
        node.prefixItems.forEach((child, index) => {
          itemSchemas.push([`prefixItems/${index}`, child]);
        });
      }
      for (const [keyword, child] of itemSchemas) {
        if (this.evaluationReachesInferredClosure(child)) {
          throw new EnforcementUnsupportedError(
            "child_evaluator_overlap",
            `contains and ${keyword} can evaluate the same array element; make closure explicit at every affected structured descendant or separate the item and match criteria`,
            displayPath((this.infos.get(node) as NodeInfo).path),
          );
        }
      }
    }

    const propertyEntries = isMapping(node.properties) ? Object.entries(node.properties) : [];
    const patternEntries = isMapping(node.patternProperties)
      ? Object.entries(node.patternProperties)
      : [];
    for (const [name, propertySchema] of propertyEntries) {
      for (const [pattern, patternSchema] of patternEntries) {
        if (
          new RegExp(pattern, "u").test(name) &&
          this.evaluatesObjectProperties(propertySchema) &&
          this.evaluatesObjectProperties(patternSchema) &&
          (this.evaluationReachesInferredClosure(propertySchema) ||
            this.evaluationReachesInferredClosure(patternSchema))
        ) {
          throw new EnforcementUnsupportedError(
            "child_evaluator_overlap",
            `property ${JSON.stringify(name)} is also matched by patternProperties pattern ${JSON.stringify(pattern)}; make closure explicit at every affected structured descendant in both value schemas or separate their property domains`,
            displayPath((this.infos.get(node) as NodeInfo).path),
          );
        }
      }
    }

    patternEntries.forEach(([firstPattern, firstSchema], index) => {
      for (const [secondPattern, secondSchema] of patternEntries.slice(index + 1)) {
        if (
          this.evaluatesObjectProperties(firstSchema) &&
          this.evaluatesObjectProperties(secondSchema) &&
          (this.evaluationReachesInferredClosure(firstSchema) ||
            this.evaluationReachesInferredClosure(secondSchema))
        ) {
          throw new EnforcementUnsupportedError(
            "child_evaluator_overlap",
            `structured patternProperties value schemas may evaluate the same property (${JSON.stringify(firstPattern)} and ${JSON.stringify(secondPattern)}); make closure explicit at every affected structured descendant in both value schemas or use one structured pattern`,
            displayPath((this.infos.get(node) as NodeInfo).path),
          );
        }
      }
    });
  }

  private checkReferenceTargets(): void {
    for (const [node, info] of this.infos) {
      if (typeof node.$ref !== "string") continue;
      const target = this.resolveRef(node, node.$ref);
      if (!isMapping(target)) continue;
      const targetInfo = this.infos.get(target);
      if (
        targetInfo !== undefined &&
        !targetInfo.reusableRoot &&
        !hasExplicitClosure(target) &&
        this.declaresProperties(target)
      ) {
        throw new EnforcementUnsupportedError(
          "reference_target_context",
          "a structured $ref target is also applied directly; move it to $defs or a supplied resource",
          displayPath(info.path),
        );
      }
    }
  }

  private evaluationReachesInferredClosure(node: Json, seen: Set<Schema> = new Set()): boolean {
    if (!isMapping(node)) {
      return false;
    }
    if (this.closureReachable.has(node)) {
      return true;
    }
    if (seen.has(node)) {
      return false;
    }
    if (this.inferredClosures.has(node)) {
      this.closureReachable.add(node);
      return true;
    }
    const nextSeen = new Set(seen).add(node);
    if (
      typeof node.$ref === "string" &&
      this.evaluationReachesInferredClosure(this.resolveRef(node, node.$ref), nextSeen)
    ) {
      this.closureReachable.add(node);
      return true;
    }
    for (const [key, value] of Object.entries(node)) {
      if (DEFINITION_KEYWORDS.has(key)) {
        continue;
      }
      if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
        if (
          Object.values(value).some((child) =>
            this.evaluationReachesInferredClosure(child, nextSeen),
          )
        ) {
          this.closureReachable.add(node);
          return true;
        }
      } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
        if (value.some((child) => this.evaluationReachesInferredClosure(child, nextSeen))) {
          this.closureReachable.add(node);
          return true;
        }
      } else if (
        SCHEMA_KEYWORDS.has(key) &&
        this.evaluationReachesInferredClosure(value, nextSeen)
      ) {
        this.closureReachable.add(node);
        return true;
      }
    }
    return false;
  }

  private static referenceHasValidationSiblings(node: Schema): boolean {
    return Object.keys(node).some(
      (key) => key !== "$ref" && !REFERENCE_NONVALIDATION_SIBLINGS.has(key),
    );
  }

  private checkContextSensitiveReferences(node: Json, compositionContext = false): void {
    if (!isMapping(node)) {
      return;
    }
    if (
      (compositionContext || SchemaGraph.referenceHasValidationSiblings(node)) &&
      typeof node.$ref === "string" &&
      this.evaluationReachesInferredClosure(this.resolveRef(node, node.$ref))
    ) {
      throw new EnforcementUnsupportedError(
        "composition_reference_context",
        "a $ref inside context-sensitive composition or beside validation siblings reaches a target that inferred closure would modify; add explicit closure to the target's structured descendants or use the reference at a pure application site",
        displayPath((this.infos.get(node) as NodeInfo).path),
      );
    }
    for (const [key, value] of Object.entries(node)) {
      let childContext = compositionContext || CONTEXT_SENSITIVE_REFERENCE_KEYWORDS.has(key);
      if (DEFINITION_KEYWORDS.has(key)) {
        childContext = false;
      }
      if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
        for (const child of Object.values(value)) {
          this.checkContextSensitiveReferences(child, childContext);
        }
      } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
        for (const child of value) {
          this.checkContextSensitiveReferences(child, childContext);
        }
      } else if (SCHEMA_KEYWORDS.has(key)) {
        this.checkContextSensitiveReferences(value, childContext);
      }
    }
  }

  checkPostTransformSafety(root: Schema, resources: Record<string, Schema>): void {
    for (const node of this.infos.keys()) {
      this.checkChildEvaluatorOverlaps(node);
    }
    this.checkContextSensitiveReferences(root);
    for (const resource of Object.values(resources)) {
      this.checkContextSensitiveReferences(resource);
    }
  }

  transform(node: Json, context: FragmentContext = null): Json {
    if (!isMapping(node)) return node;
    const info = this.infos.get(node) as NodeInfo;
    const out: Schema = {};
    for (const [key, value] of Object.entries(node)) {
      let childContext = childFragmentContext(context, key);
      if (NAME_MAP_KEYWORDS.has(key) && isMapping(value)) {
        if (DEFINITION_KEYWORDS.has(key)) childContext = null;
        out[key] = Object.fromEntries(
          Object.entries(value).map(([name, child]) => [name, this.transform(child, childContext)]),
        );
      } else if (SCHEMA_LIST_KEYWORDS.has(key) && Array.isArray(value)) {
        out[key] = value.map((child) => this.transform(child, childContext));
      } else if (SCHEMA_KEYWORDS.has(key)) {
        out[key] = this.transform(value, childContext);
      } else {
        out[key] = value;
      }
    }

    const explicit = hasExplicitClosure(out);
    const declares = this.declaresProperties(node);
    if (context === "nested_instance" && declares && !explicit) {
      throw new EnforcementUnsupportedError(
        "nested_instance_composition",
        "the enforced profile cannot safely infer closure for a nested instance inside in-place composition; add explicit closure at that object",
        displayPath(info.path),
      );
    }
    if (context === null && info.embeddedDirectResource && declares && !explicit) {
      throw new EnforcementUnsupportedError(
        "embedded_resource_context",
        "a structured embedded $id resource is applied directly and reused; add explicit closure or move it to $defs",
        displayPath(info.path),
      );
    }
    if (context === null && declares && !explicit && !this.conditionMatchersAreCovered(node)) {
      throw new EnforcementUnsupportedError(
        "conditional_annotation_scope",
        "condition-matcher properties must also be unconditionally evaluated at the closure site",
        displayPath(info.path),
      );
    }
    if (context !== null || info.reusableRoot || explicit || !declares) return out;

    const needsAnnotations =
      "$ref" in node || Object.keys(node).some((key) => ANNOTATING_IN_PLACE_KEYWORDS.has(key));
    this.inferredClosures.add(node);
    out[needsAnnotations ? "unevaluatedProperties" : "additionalProperties"] = false;
    return out;
  }
}

function hasExplicitClosure(node: Json): boolean {
  return isMapping(node) && EXPLICIT_CLOSURE_KEYWORDS.some((key) => key in node);
}

function childFragmentContext(context: FragmentContext, keyword: string): FragmentContext {
  if (DEFINITION_KEYWORDS.has(keyword)) return null;
  if (keyword === "contains") {
    return "same_instance";
  }
  if (
    IN_PLACE_MAP_KEYWORDS.has(keyword) ||
    IN_PLACE_LIST_KEYWORDS.has(keyword) ||
    IN_PLACE_SINGLE_KEYWORDS.has(keyword)
  ) {
    return context ?? "same_instance";
  }
  return context === null ? null : "nested_instance";
}

export function prepareSchemaGraph(
  root: Schema,
  resources: Record<string, Schema> = {},
): PreparedSchemaGraph {
  const graph = new SchemaGraph(root, resources);
  const transformedRoot = graph.transform(root) as Schema;
  const transformedResources = Object.fromEntries(
    Object.entries(resources).map(([key, resource]) => [key, graph.transform(resource) as Schema]),
  );
  graph.checkPostTransformSafety(root, resources);
  return {
    root: transformedRoot,
    resources: transformedResources,
  };
}

export function applyCheckedEnforcement(schema: Schema): Schema {
  return prepareSchemaGraph(schema).root;
}
