/** Runtime-aware local Zod model-module loading for the Node.js/Bun CLI adapter. */
import { resolve, win32 } from "node:path";
import { pathToFileURL } from "node:url";
import { z } from "zod";

export type ModelRuntime = "node" | "bun";

export interface ModelSpecifier {
  modulePath: string;
  exportName: string;
}

export interface ModelModuleUrlOptions {
  cwd?: string;
  platform?: NodeJS.Platform;
}

export interface LoadZodModelOptions extends ModelModuleUrlOptions {
  runtime?: ModelRuntime;
}

/** A stable user-facing model-module policy or import failure. */
export class ModelModuleUsageError extends Error {}

/** The runtime whose module loader will execute the model. */
export function currentModelRuntime(): ModelRuntime {
  return typeof process.versions.bun === "string" ? "bun" : "node";
}

/** Split `path:export` on its final colon so Windows drive letters remain intact. */
export function parseModelSpecifier(spec: string): ModelSpecifier {
  const separator = spec.lastIndexOf(":");
  const modulePath = separator < 0 ? "" : spec.slice(0, separator);
  const exportName = separator < 0 ? "" : spec.slice(separator + 1);
  if (modulePath.length === 0 || exportName.length === 0) {
    throw new ModelModuleUsageError(`model spec must be path:export, got ${JSON.stringify(spec)}`);
  }
  return { modulePath, exportName };
}

/** Enforce the documented Node built-module versus Bun source-module policy. */
export function validateModelModuleExtension(modulePath: string, runtime: ModelRuntime): void {
  const lower = modulePath.toLowerCase();
  if (lower.endsWith(".js") || lower.endsWith(".mjs")) return;
  if (lower.endsWith(".ts")) {
    if (runtime === "bun") return;
    throw new ModelModuleUsageError(
      `Node cannot import TypeScript model module ${JSON.stringify(modulePath)}; ` +
        "compile it to .js or .mjs, or run softschema with Bun",
    );
  }
  const supported = runtime === "bun" ? ".js, .mjs, or .ts" : ".js or .mjs";
  throw new ModelModuleUsageError(
    `model module must use ${supported} under ${runtime === "bun" ? "Bun" : "Node"}, ` +
      `got ${JSON.stringify(modulePath)}`,
  );
}

/** Resolve a local module path and convert it to an encoded file URL. */
export function resolveModelModuleUrl(
  modulePath: string,
  options: ModelModuleUrlOptions = {},
): URL {
  const cwd = options.cwd ?? process.cwd();
  const platform = options.platform ?? process.platform;
  if (platform === "win32") {
    const absolute = win32.resolve(cwd, modulePath);
    const native = pathToFileURL(absolute, { windows: true });
    // Node >=22 honors the explicit Windows option on every host. Bun currently
    // ignores it on non-Windows hosts, so retain a deterministic fallback for unit
    // tests and cross-runtime tooling that asks for Windows resolution explicitly.
    if (/^[A-Za-z]:\\/.test(absolute)) {
      const drivePrefix = `file:///${absolute.slice(0, 2)}/`.toLowerCase();
      if (native.href.toLowerCase().startsWith(drivePrefix)) return native;
      const segments = absolute.slice(3).split("\\").map(encodeURIComponent);
      return new URL(`file:///${absolute.slice(0, 2)}/${segments.join("/")}`);
    }
    if (absolute.startsWith("\\\\") && native.host.length === 0) {
      const [host = "", ...segments] = absolute.slice(2).split("\\");
      return new URL(`file://${host}/${segments.map(encodeURIComponent).join("/")}`);
    }
    return native;
  }
  return pathToFileURL(resolve(cwd, modulePath));
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Import a trusted local model module and require the selected export to be Zod. */
export async function loadZodModel(
  spec: string,
  options: LoadZodModelOptions = {},
): Promise<z.ZodType> {
  const parsed = parseModelSpecifier(spec);
  const runtime = options.runtime ?? currentModelRuntime();
  validateModelModuleExtension(parsed.modulePath, runtime);
  const moduleUrl = resolveModelModuleUrl(parsed.modulePath, options);
  let loaded: Record<string, unknown>;
  try {
    loaded = (await import(moduleUrl.href)) as Record<string, unknown>;
  } catch (error) {
    throw new ModelModuleUsageError(
      `cannot import ${JSON.stringify(spec)}: ${errorMessage(error)}`,
    );
  }
  const schema = loaded[parsed.exportName];
  if (schema === undefined) {
    throw new ModelModuleUsageError(
      `${JSON.stringify(spec)} has no export ${JSON.stringify(parsed.exportName)}`,
    );
  }
  if (!(schema instanceof z.ZodType)) {
    throw new ModelModuleUsageError(`${JSON.stringify(spec)} is not a Zod schema`);
  }
  return schema;
}
