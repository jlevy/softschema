import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { beforeAll, describe, expect, test } from "bun:test";
import ts from "typescript";

const PACKAGE_ROOT = resolve(import.meta.dir, "..");
const SOURCE_ROOT = join(PACKAGE_ROOT, "src");
const CORE_SOURCE = join(SOURCE_ROOT, "core", "index.ts");
const ROOT_SOURCE = join(SOURCE_ROOT, "index.ts");
const DIST_ROOT = join(PACKAGE_ROOT, "dist");

interface RuntimeDependency {
  dynamic: boolean;
  specifier: string;
}

const NODE_RUNTIME_GLOBALS = new Set([
  "Buffer",
  "Bun",
  "Deno",
  "Function",
  "__dirname",
  "__filename",
  "eval",
  "process",
  "require",
]);

function runtimeDependencies(path: string): RuntimeDependency[] {
  const source = readFileSync(path, "utf8");
  const file = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true);
  const dependencies: RuntimeDependency[] = [];
  const visit = (node: ts.Node): void => {
    if (ts.isImportDeclaration(node)) {
      if (!node.importClause?.isTypeOnly && ts.isStringLiteral(node.moduleSpecifier)) {
        dependencies.push({ dynamic: false, specifier: node.moduleSpecifier.text });
      }
    } else if (ts.isExportDeclaration(node)) {
      const allTypeOnly =
        node.isTypeOnly ||
        (node.exportClause !== undefined &&
          ts.isNamedExports(node.exportClause) &&
          node.exportClause.elements.every((element) => element.isTypeOnly));
      if (!allTypeOnly && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
        dependencies.push({ dynamic: false, specifier: node.moduleSpecifier.text });
      }
    } else if (
      ts.isCallExpression(node) &&
      node.expression.kind === ts.SyntaxKind.ImportKeyword
    ) {
      const argument = node.arguments[0];
      dependencies.push({
        dynamic: true,
        specifier: argument && ts.isStringLiteral(argument) ? argument.text : "<computed>",
      });
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return dependencies;
}

function forbiddenRuntimeGlobals(path: string): string[] {
  const source = readFileSync(path, "utf8");
  const file = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true);
  const found = new Set<string>();
  const visit = (node: ts.Node): void => {
    if (ts.isIdentifier(node) && NODE_RUNTIME_GLOBALS.has(node.text)) found.add(node.text);
    ts.forEachChild(node, visit);
  };
  visit(file);
  return [...found].sort();
}

function localSource(fromPath: string, specifier: string): string | null {
  if (!specifier.startsWith(".")) return null;
  const base = resolve(dirname(fromPath), specifier.replace(/\.js$/, ""));
  for (const candidate of [`${base}.ts`, join(base, "index.ts")]) {
    try {
      readFileSync(candidate);
      return candidate;
    } catch {
      // Try the next source form.
    }
  }
  throw new Error(`unresolved local source dependency ${specifier} from ${fromPath}`);
}

function localBuild(fromPath: string, specifier: string): string | null {
  if (!specifier.startsWith(".")) return null;
  const candidate = resolve(dirname(fromPath), specifier);
  try {
    readFileSync(candidate);
    return candidate;
  } catch {
    throw new Error(`unresolved built dependency ${specifier} from ${fromPath}`);
  }
}

beforeAll(() => {
  const build = spawnSync("bun", ["run", "build"], {
    cwd: PACKAGE_ROOT,
    encoding: "utf8",
  });
  if (build.status !== 0) throw new Error(`build failed: ${build.stderr}`);
}, 120_000);

describe("portable core boundary", () => {
  test("transitive source graph has no runtime, YAML, model, CLI, or dynamic-import adapter", () => {
    const pending = [CORE_SOURCE];
    const visited = new Set<string>();
    while (pending.length > 0) {
      const path = pending.pop();
      if (path === undefined || visited.has(path)) continue;
      visited.add(path);
      expect(forbiddenRuntimeGlobals(path), `${path} uses a runtime-only global`).toEqual([]);
      for (const dependency of runtimeDependencies(path)) {
        expect(dependency.dynamic, `${path} dynamically imports ${dependency.specifier}`).toBe(false);
        expect(
          dependency.specifier.startsWith("node:"),
          `${path} imports Node builtin ${dependency.specifier}`,
        ).toBe(false);
        const local = localSource(path, dependency.specifier);
        expect(local, `${path} imports runtime dependency ${dependency.specifier}`).not.toBeNull();
        if (local !== null) pending.push(local);
      }
    }
    expect(visited.size).toBeGreaterThan(1);
    for (const adapter of [
      "cli.ts",
      "compile.ts",
      "generate.ts",
      "schemaView.ts",
      "settings.ts",
      "skill-installer.ts",
      "validate.ts",
      "yaml-value-domain.ts",
    ]) {
      expect([...visited].some((path) => path.endsWith(adapter)), adapter).toBe(false);
    }
  });

  test("published core imports in Node without loading Node adapters", () => {
    const packageJson = JSON.parse(
      readFileSync(join(PACKAGE_ROOT, "package.json"), "utf8"),
    ) as { exports: Record<string, { import: string; types: string }> };
    expect(packageJson.exports["./core"]).toEqual({
      types: "./dist/core/index.d.ts",
      import: "./dist/core/index.js",
    });
    const coreUrl = pathToFileURL(join(DIST_ROOT, "core", "index.js")).href;
    const imported = spawnSync(
      "node",
      [
        "--input-type=module",
        "--eval",
        `const core = await import(${JSON.stringify(coreUrl)}); process.stdout.write(typeof core.validateContractId);`,
      ],
      { encoding: "utf8" },
    );
    expect(imported.stderr).toBe("");
    expect(imported.stdout).toBe("function");
    expect(imported.status).toBe(0);

    const pending = [join(DIST_ROOT, "core", "index.js")];
    const visited = new Set<string>();
    while (pending.length > 0) {
      const path = pending.pop();
      if (path === undefined || visited.has(path)) continue;
      visited.add(path);
      expect(forbiddenRuntimeGlobals(path), `${path} uses a runtime-only global`).toEqual([]);
      for (const dependency of runtimeDependencies(path)) {
        expect(dependency.dynamic, `${path} dynamically imports ${dependency.specifier}`).toBe(false);
        expect(
          dependency.specifier.startsWith("node:"),
          `${path} imports Node builtin ${dependency.specifier}`,
        ).toBe(false);
        const local = localBuild(path, dependency.specifier);
        expect(local, `${path} imports runtime package ${dependency.specifier}`).not.toBeNull();
        if (local !== null) pending.push(local);
      }
    }
    expect(visited.size).toBeGreaterThan(1);
  });
});

describe("Node compatibility facade", () => {
  test("the package root exposes exactly the explicit Node adapter", async () => {
    const rootFile = ts.createSourceFile(
      ROOT_SOURCE,
      readFileSync(ROOT_SOURCE, "utf8"),
      ts.ScriptTarget.Latest,
      true,
    );
    const statements = rootFile.statements.filter(
      (statement) => !ts.isEmptyStatement(statement),
    );
    expect(statements).toHaveLength(1);
    const facade = statements[0];
    expect(facade && ts.isExportDeclaration(facade)).toBe(true);
    if (!facade || !ts.isExportDeclaration(facade)) return;
    expect(facade.exportClause).toBeUndefined();
    expect(
      facade.moduleSpecifier && ts.isStringLiteral(facade.moduleSpecifier)
        ? facade.moduleSpecifier.text
        : null,
    ).toBe("./node.js");

    const packageJson = JSON.parse(
      readFileSync(join(PACKAGE_ROOT, "package.json"), "utf8"),
    ) as { exports: Record<string, { import: string; types: string }> };
    expect(packageJson.exports["./node"]).toEqual({
      types: "./dist/node.d.ts",
      import: "./dist/node.js",
    });
    const rootModule = await import(pathToFileURL(join(DIST_ROOT, "index.js")).href);
    const nodeModule = await import(pathToFileURL(join(DIST_ROOT, "node.js")).href);
    expect(Object.keys(rootModule).sort()).toEqual(Object.keys(nodeModule).sort());
  });
});
