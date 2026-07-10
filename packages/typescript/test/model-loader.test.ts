import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, test } from "bun:test";
import {
  loadZodModel,
  parseModelSpecifier,
  resolveModelModuleUrl,
  validateModelModuleExtension,
} from "../src/model-loader.js";

const PACKAGE_ROOT = resolve(import.meta.dir, "..");
const MOVIE_MODEL = join(PACKAGE_ROOT, "test", "fixtures", "movie-model.mjs");
const PARITY_MODEL = join(PACKAGE_ROOT, "test", "fixtures", "parity.ts");

describe("model module specifiers", () => {
  test("the final colon separates a Windows drive path from its export", () => {
    expect(parseModelSpecifier("C:\\repo\\model.mjs:MoviePage")).toEqual({
      modulePath: "C:\\repo\\model.mjs",
      exportName: "MoviePage",
    });
  });

  test.each(["model.mjs", ":Export", "model.mjs:"])("rejects malformed spec %s", (spec) => {
    expect(() => parseModelSpecifier(spec)).toThrow("model spec must be path:export");
  });

  test("path URLs encode spaces, hashes, and percent signs", () => {
    const url = resolveModelModuleUrl("models/a space/model#100%.mjs", {
      cwd: "/workspace",
      platform: "linux",
    });
    expect(url.href).toBe("file:///workspace/models/a%20space/model%23100%25.mjs");
  });

  test("Windows drive-letter paths use Windows URL semantics on every test host", () => {
    const url = resolveModelModuleUrl("C:\\repo space\\model#%.mjs", {
      cwd: "D:\\work",
      platform: "win32",
    });
    expect(url.href).toBe("file:///C:/repo%20space/model%23%25.mjs");
  });
});

describe("Node and Bun model-module policy", () => {
  test.each(["model.js", "model.mjs"])("Node accepts built %s modules", (path) => {
    expect(() => validateModelModuleExtension(path, "node")).not.toThrow();
  });

  test("Node rejects direct TypeScript with an actionable migration", () => {
    expect(() => validateModelModuleExtension("model.ts", "node")).toThrow(
      "compile it to .js or .mjs, or run softschema with Bun",
    );
  });

  test("Bun accepts direct .ts model modules", () => {
    expect(() => validateModelModuleExtension("model.ts", "bun")).not.toThrow();
  });

  test.each(["model", "model.cjs", "model.mts", "model.tsx"])(
    "unsupported module extension is rejected: %s",
    (path) => {
      expect(() => validateModelModuleExtension(path, "bun")).toThrow(
        "model module must use .js, .mjs, or .ts under Bun",
      );
    },
  );

  test("an encoded local path is imported rather than interpreted as a URL fragment", async () => {
    const directory = mkdtempSync(join(tmpdir(), "softschema model path "));
    const moduleName = "model #100%.mjs";
    writeFileSync(
      join(directory, moduleName),
      `export { MoviePage } from ${JSON.stringify(pathToFileURL(MOVIE_MODEL).href)};\n`,
    );
    const model = await loadZodModel(`${moduleName}:MoviePage`, { cwd: directory, runtime: "node" });
    expect(model.safeParse({ title: "ok" }).success).toBe(true);
  });

  test("Bun executes a direct .ts source model", async () => {
    const model = await loadZodModel(`${PARITY_MODEL}:KitchenSink`, { runtime: "bun" });
    expect(typeof model.safeParse).toBe("function");
  });
});
