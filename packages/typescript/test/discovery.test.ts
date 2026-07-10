import {
  linkSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, test } from "bun:test";
import {
  CompiledGlob,
  DISCOVERY_MAX_DEPTH,
  DISCOVERY_MAX_ENTRIES,
  type DiscoveryFileInfo,
  type DiscoveryFileSystem,
  type DiscoveryInputReason,
  type DiscoveryRequest,
  DiscoveryUsageError,
  GlobPatternError,
  type GlobPatternReason,
  discoverArtifacts,
} from "../src/artifact-discovery.js";

const BATCH_VECTORS = resolve(import.meta.dir, "../../..", "tests", "batch");

interface GlobVector {
  id: string;
  pattern: string;
  matches: string[];
  misses: string[];
}

interface InvalidGlobVector {
  id: string;
  pattern: string;
  reason: GlobPatternReason;
}

type ExpectedDiscoveryEntry =
  | { kind: "artifact"; path: string; display_path: string }
  | { kind: "input_error"; reason: DiscoveryInputReason; message: string; source: string };

interface VectorNode {
  path: string;
  kind: DiscoveryFileInfo["kind"];
  device: string | null;
  inode: string | null;
  entries?: string[];
  target?: string;
  realpath?: string;
}

interface VectorFailure {
  operation: "lstat" | "stat" | "read_directory" | "realpath";
  path: string;
  code: "not_found" | "unreadable";
}

interface FilesystemVector {
  id: string;
  platform: "posix" | "windows";
  cwd: string;
  operands: string[];
  recursive: boolean;
  profile: "frontmatter-md" | "pure-yaml";
  includes: string[];
  excludes: string[];
  nodes: VectorNode[];
  failures: VectorFailure[];
  expected: ExpectedDiscoveryEntry[];
}

type LimitVector =
  | {
      id: string;
      shape: "depth";
      directory_depth: number;
      early_match?: boolean;
      following_operand?: boolean;
      expected: "artifact" | "discovery_limit";
    }
  | {
      id: string;
      shape: "entries";
      entry_count: number;
      matching_index: number | null;
      following_operand?: boolean;
      expected: "artifact" | "discovery_limit";
    };

function loadJson<T>(name: string): T {
  return JSON.parse(readFileSync(join(BATCH_VECTORS, name), "utf8")) as T;
}

function filesystemError(code: VectorFailure["code"], path: string): Error {
  const error = new Error(path) as NodeJS.ErrnoException;
  error.code = code === "not_found" ? "ENOENT" : "EACCES";
  return error;
}

class VectorFileSystem implements DiscoveryFileSystem {
  readonly calls: [string, string][] = [];
  private readonly nodes: Map<string, VectorNode>;
  private readonly failures: Map<string, VectorFailure["code"]>;

  constructor(vector: Pick<FilesystemVector, "nodes" | "failures">) {
    this.nodes = new Map(vector.nodes.map((node) => [node.path, node]));
    this.failures = new Map(
      vector.failures.map((failure) => [
        `${failure.operation}\0${failure.path}`,
        failure.code,
      ]),
    );
  }

  private fail(operation: VectorFailure["operation"], path: string): void {
    this.calls.push([operation, path]);
    const code = this.failures.get(`${operation}\0${path}`);
    if (code !== undefined) throw filesystemError(code, path);
  }

  private node(path: string): VectorNode {
    const node = this.nodes.get(path);
    if (node === undefined) throw filesystemError("not_found", path);
    return node;
  }

  private static info(node: VectorNode): DiscoveryFileInfo {
    return {
      kind: node.kind,
      device: node.device === null ? null : BigInt(node.device),
      inode: node.inode === null ? null : BigInt(node.inode),
    };
  }

  lstat(path: string): DiscoveryFileInfo {
    this.fail("lstat", path);
    return VectorFileSystem.info(this.node(path));
  }

  stat(path: string): DiscoveryFileInfo {
    this.fail("stat", path);
    const seen = new Set<string>();
    let current = path;
    while (true) {
      if (seen.has(current)) throw filesystemError("unreadable", path);
      seen.add(current);
      const node = this.node(current);
      if (node.kind !== "symlink") return VectorFileSystem.info(node);
      current = node.target as string;
    }
  }

  readDirectory(path: string, limit: number): readonly string[] {
    this.fail("read_directory", path);
    const node = this.node(path);
    if (node.kind !== "directory") throw filesystemError("unreadable", path);
    return (node.entries ?? []).slice(0, limit);
  }

  realpath(path: string): string {
    this.fail("realpath", path);
    const seen = new Set<string>();
    let current = path;
    while (true) {
      if (seen.has(current)) throw filesystemError("unreadable", path);
      seen.add(current);
      const node = this.node(current);
      if (node.realpath !== undefined) return node.realpath;
      if (node.kind !== "symlink") return current;
      current = node.target as string;
    }
  }
}

function wideEntryName(index: number, matchingIndex: number | null): string {
  const extension = index === matchingIndex ? ".md" : ".txt";
  return `entry-${index.toString().padStart(6, "0")}${extension}`;
}

class LimitVectorFileSystem implements DiscoveryFileSystem {
  private readonly root = "/work/root";
  readonly reads: [path: string, requested: number, materialized: number][] = [];

  constructor(private readonly vector: LimitVector) {}

  lstat(path: string): DiscoveryFileInfo {
    if (path === "/work/after.md") return { kind: "file", device: 32n, inode: 1n };
    if (path === this.root) return { kind: "directory", device: 30n, inode: 1n };
    if (!path.startsWith(`${this.root}/`)) throw filesystemError("not_found", path);
    const relative = path.slice(this.root.length + 1);
    if (this.vector.shape === "depth") {
      const parts = relative.split("/");
      const leaf = parts.at(-1);
      if (leaf === "a-early.md" || leaf === "leaf.md") {
        return { kind: "file", device: 30n, inode: 10_000n };
      }
      return { kind: "directory", device: 30n, inode: BigInt(parts.length + 1) };
    }
    if (relative.includes("/") || !relative.startsWith("entry-")) {
      throw filesystemError("not_found", path);
    }
    const index = Number(relative.slice(6, 12));
    return { kind: "file", device: 31n, inode: BigInt(index + 1) };
  }

  stat(path: string): DiscoveryFileInfo {
    return this.lstat(path);
  }

  readDirectory(path: string, limit: number): readonly string[] {
    const vector = this.vector;
    let names: readonly string[];
    if (vector.shape === "depth") {
      const relative = path.slice(this.root.length + 1);
      const depth = path === this.root ? 0 : relative.split("/").length;
      if (depth < vector.directory_depth) {
        const child = `d${depth.toString().padStart(3, "0")}`;
        names = depth === 0 && vector.early_match === true ? [child, "a-early.md"] : [child];
      } else names = ["leaf.md"];
      names = names.slice(0, limit);
    } else {
      if (path !== this.root) throw filesystemError("unreadable", path);
      const materialized = Math.min(vector.entry_count, limit);
      names = Array.from({ length: materialized }, (_, offset) => {
        const index = vector.entry_count - offset - 1;
        return wideEntryName(index, vector.matching_index);
      });
    }
    this.reads.push([path, limit, names.length]);
    return names;
  }

  realpath(path: string): string {
    return path;
  }
}

function expectedLimitResult(vector: LimitVector): ExpectedDiscoveryEntry[] {
  if (vector.shape === "depth") {
    const relativeDirectory = Array.from({ length: vector.directory_depth }, (_, index) =>
      `d${index.toString().padStart(3, "0")}`,
    ).join("/");
    if (vector.expected === "artifact") {
      const relative = `root/${relativeDirectory}/leaf.md`;
      return [{ kind: "artifact", path: `/work/${relative}`, display_path: relative }];
    }
    return [
      {
        kind: "input_error",
        reason: "discovery_limit",
        message: "artifact discovery limit exceeded",
        source: `root/${relativeDirectory}`,
      },
    ];
  }
  if (vector.expected === "artifact") {
    if (vector.matching_index === null) {
      throw new Error(`artifact limit vector ${vector.id} requires matching_index`);
    }
    const name = wideEntryName(vector.matching_index, vector.matching_index);
    return [{ kind: "artifact", path: `/work/root/${name}`, display_path: `root/${name}` }];
  }
  return [
    {
      kind: "input_error",
      reason: "discovery_limit",
      message: "artifact discovery limit exceeded",
      source: "root",
    },
  ];
}

describe("portable discovery globs", () => {
  const vectors = loadJson<{ valid: GlobVector[]; invalid: InvalidGlobVector[] }>(
    "glob-vectors.json",
  );

  test("matches every shared valid vector", () => {
    for (const vector of vectors.valid) {
      const compiled = CompiledGlob.compile(vector.pattern);
      for (const candidate of vector.matches) {
        expect(compiled.matches(candidate), `${vector.id}: ${candidate}`).toBe(true);
      }
      for (const candidate of vector.misses) {
        expect(compiled.matches(candidate), `${vector.id}: ${candidate}`).toBe(false);
      }
    }
  });

  test("rejects every shared invalid vector with its stable reason", () => {
    for (const vector of vectors.invalid) {
      try {
        CompiledGlob.compile(vector.pattern);
        throw new Error(`expected invalid glob ${vector.id}`);
      } catch (error) {
        expect(error).toBeInstanceOf(GlobPatternError);
        if (!(error instanceof GlobPatternError)) throw error;
        expect(error.reason).toBe(vector.reason);
        expect(error.message).toBe(`invalid glob ${JSON.stringify(vector.pattern)}: ${vector.reason}`);
      }
    }
  });
});

describe("artifact discovery", () => {
  const vectors = loadJson<{ cases: FilesystemVector[] }>("filesystem-vectors.json");

  test("matches every shared virtual-filesystem vector", () => {
    for (const vector of vectors.cases) {
      const filesystem = new VectorFileSystem(vector);
      const request: DiscoveryRequest = {
        operands: vector.operands,
        recursive: vector.recursive,
        profile: vector.profile,
        includes: vector.includes,
        excludes: vector.excludes,
        invocationDirectory: vector.cwd,
        pathFlavor: vector.platform,
      };
      const result = discoverArtifacts(request, filesystem);
      const normalized = result.entries.map((entry) =>
        entry.kind === "artifact"
          ? { kind: entry.kind, path: entry.path, display_path: entry.displayPath }
          : entry,
      );
      expect(normalized, vector.id).toEqual(vector.expected);
    }
  });

  test("enforces every shared discovery limit vector", () => {
    const vectors = loadJson<{
      limits: { max_depth: number; max_entries: number };
      cases: LimitVector[];
    }>("discovery-limit-vectors.json");
    expect(vectors.limits).toEqual({
      max_depth: DISCOVERY_MAX_DEPTH,
      max_entries: DISCOVERY_MAX_ENTRIES,
    });
    for (const vector of vectors.cases) {
      const filesystem = new LimitVectorFileSystem(vector);
      const result = discoverArtifacts(
        {
          operands: vector.following_operand === true ? ["root", "after.md"] : ["root"],
          recursive: true,
          profile: "frontmatter-md",
          includes: [],
          excludes: [],
          invocationDirectory: "/work",
          pathFlavor: "posix",
        },
        filesystem,
      );
      expect(filesystem.reads.every(([, requested, materialized]) => materialized <= requested)).toBe(
        true,
      );
      if (vector.shape === "entries") {
        const expectedMaterialized = Math.min(
          vector.entry_count,
          vectors.limits.max_entries + 1,
        );
        expect(filesystem.reads).toEqual([
          ["/work/root", vectors.limits.max_entries + 1, expectedMaterialized],
        ]);
      }
      const normalized = result.entries.map((entry) =>
        entry.kind === "artifact"
          ? { kind: entry.kind, path: entry.path, display_path: entry.displayPath }
          : entry,
      );
      const expected = expectedLimitResult(vector);
      if (vector.following_operand === true) {
        expected.push({
          kind: "artifact",
          path: "/work/after.md",
          display_path: "after.md",
        });
      }
      expect(normalized, vector.id).toEqual(expected);
    }
  });

  test("validates the request before filesystem access", () => {
    const filesystem = new VectorFileSystem({ nodes: [], failures: [] });
    const base: DiscoveryRequest = {
      operands: ["content"],
      recursive: false,
      profile: "frontmatter-md",
      includes: ["*.md"],
      excludes: [],
      invocationDirectory: "/work",
      pathFlavor: "posix",
    };
    expect(() => discoverArtifacts({ ...base, operands: [], includes: [] }, filesystem)).toThrow(
      "at least one operand",
    );
    expect(filesystem.calls).toEqual([]);
    expect(() => discoverArtifacts(base, filesystem)).toThrow(DiscoveryUsageError);
    expect(filesystem.calls).toEqual([]);
    expect(() =>
      discoverArtifacts(
        { ...base, recursive: true, includes: ["bad**glob"] },
        filesystem,
      ),
    ).toThrow(GlobPatternError);
    expect(filesystem.calls).toEqual([]);
  });

  test("native filesystem discovery includes hidden entries", () => {
    const cwd = mkdtempSync(join(tmpdir(), "softschema-discovery-"));
    try {
      const root = join(cwd, "content");
      mkdirSync(root);
      writeFileSync(join(root, ".hidden.md"), "hidden");
      writeFileSync(join(root, "visible.markdown"), "visible");
      writeFileSync(join(root, "ignored.yml"), "ignored");
      const result = discoverArtifacts({
        operands: [root],
        recursive: true,
        profile: "frontmatter-md",
        includes: [],
        excludes: [],
        invocationDirectory: cwd,
        pathFlavor: process.platform === "win32" ? "windows" : "posix",
      });
      expect(
        result.entries
          .filter((entry) => entry.kind === "artifact")
          .map((entry) => entry.displayPath),
      ).toEqual(["content/.hidden.md", "content/visible.markdown"]);
    } finally {
      rmSync(cwd, { recursive: true, force: true });
    }
  });

  test("native filesystem discovery deduplicates hardlinks", () => {
    const cwd = mkdtempSync(join(tmpdir(), "softschema-discovery-"));
    try {
      const root = join(cwd, "content");
      mkdirSync(root);
      const source = join(root, "source.md");
      writeFileSync(source, "source");
      linkSync(source, join(root, "alias.md"));
      const result = discoverArtifacts({
        operands: [root],
        recursive: true,
        profile: "frontmatter-md",
        includes: [],
        excludes: [],
        invocationDirectory: cwd,
        pathFlavor: process.platform === "win32" ? "windows" : "posix",
      });
      expect(
        result.entries
          .filter((entry) => entry.kind === "artifact")
          .map((entry) => entry.displayPath),
      ).toEqual(["content/alias.md"]);
    } finally {
      rmSync(cwd, { recursive: true, force: true });
    }
  });

  test("native not-a-directory failures are not-found input errors", () => {
    const cwd = mkdtempSync(join(tmpdir(), "softschema-discovery-"));
    try {
      const parent = join(cwd, "content.md");
      writeFileSync(parent, "content");
      const result = discoverArtifacts({
        operands: [join(parent, "child.md")],
        recursive: false,
        profile: "frontmatter-md",
        includes: [],
        excludes: [],
        invocationDirectory: cwd,
        pathFlavor: process.platform === "win32" ? "windows" : "posix",
      });
      expect(result.entries).toEqual([
        {
          kind: "input_error",
          reason: "not_found",
          message: "artifact path does not exist",
          source: "content.md/child.md",
        },
      ]);
    } finally {
      rmSync(cwd, { recursive: true, force: true });
    }
  });
});
