/**
 * Deprecated compatibility facade for the v0.2 Node.js/Bun root API.
 *
 * New runtime-neutral integrations should import `softschema/core`. New code that
 * needs path, YAML, Zod, or filesystem behavior should import `softschema/node`.
 */
export * from "./node.js";
