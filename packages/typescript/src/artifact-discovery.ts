/** Deterministic filesystem discovery for batch artifact validation. */
import { type BigIntStats, lstatSync, opendirSync, realpathSync, statSync } from "node:fs";
import { posix, win32 } from "node:path";
import { compareUnicodeCodePoints } from "./core/canonical-json.js";

export type DiscoveryProfile = "frontmatter-md" | "pure-yaml";
export type DiscoveryPathFlavor = "posix" | "windows";
export type DiscoveryFileKind = "file" | "directory" | "symlink" | "other";
export type DiscoveryInputReason =
  | "not_found"
  | "unreadable"
  | "directory_requires_recursive"
  | "no_matches"
  | "discovery_limit";
export type GlobPatternReason =
  | "empty"
  | "absolute"
  | "drive_qualified"
  | "backslash"
  | "dot_segment"
  | "unterminated_class"
  | "partial_globstar"
  | "match_work_limit";

const profileExtensions: Record<DiscoveryProfile, readonly string[]> = {
  "frontmatter-md": [".md", ".markdown"],
  "pure-yaml": [".yaml", ".yml"],
};

const inputMessages: Record<DiscoveryInputReason, string> = {
  not_found: "artifact path does not exist",
  unreadable: "artifact path cannot be read",
  directory_requires_recursive: "artifact directory requires --recursive",
  no_matches: "artifact directory contains no matching files",
  discovery_limit: "artifact discovery limit exceeded",
};

const drivePattern = /^[A-Za-z]:/;

/** Maximum directory depth below one recursive operand, whose root has depth zero. */
export const DISCOVERY_MAX_DEPTH = 64;

/** Maximum directory entries inspected below one recursive operand. */
export const DISCOVERY_MAX_ENTRIES = 100_000;

/**
 * Maximum predicate work in a fixed chunk bounded by two segment stars.
 *
 * Prefix and suffix chunks remain arbitrarily long because each is checked once. This
 * fixed bound makes segment matching O(m + C*n), where C is this constant.
 */
export const GLOB_MAX_INTERIOR_MATCH_COMPLEXITY = 256;
export const GLOB_MAX_PATTERN_CODEPOINTS = 262_144;
export const GLOB_MAX_TOTAL_PATTERN_CODEPOINTS = 1_048_576;
export const GLOB_MAX_PATTERNS = 64;
export const GLOB_MAX_TOTAL_TOKENS = 4096;
export const GLOB_MAX_TOTAL_MATCH_COMPLEXITY = 8192;
export const GLOB_MAX_INVOCATION_MATCH_WORK = 8_388_608;

/** A pattern falls outside the shared portable discovery-glob grammar. */
export class GlobPatternError extends Error {
  readonly pattern: string;
  readonly reason: GlobPatternReason;

  constructor(pattern: string, reason: GlobPatternReason) {
    super(`invalid glob ${JSON.stringify(pattern)}: ${reason}`);
    this.pattern = pattern;
    this.reason = reason;
  }
}

/** A discovery request combines options that cannot be interpreted safely. */
export class DiscoveryUsageError extends Error {}

class GlobWorkLimitExceeded extends Error {}

class GlobWorkBudget {
  private remaining = GLOB_MAX_INVOCATION_MATCH_WORK;

  charge(amount: number): void {
    this.remaining -= amount;
    if (this.remaining < 0) throw new GlobWorkLimitExceeded();
  }
}

/** Filesystem metadata required for kind checks and stable identity. */
export interface DiscoveryFileInfo {
  readonly kind: DiscoveryFileKind;
  readonly device: bigint | null;
  readonly inode: bigint | null;
}

/** Injectable synchronous filesystem operations used by discovery. */
export interface DiscoveryFileSystem {
  lstat(path: string): DiscoveryFileInfo;
  stat(path: string): DiscoveryFileInfo;
  /** Return at most `limit` names without materializing the rest of the directory. */
  readDirectory(path: string, limit: number): readonly string[];
  realpath(path: string): string;
}

function fileInfo(result: BigIntStats): DiscoveryFileInfo {
  let kind: DiscoveryFileKind;
  if (result.isFile()) kind = "file";
  else if (result.isDirectory()) kind = "directory";
  else if (result.isSymbolicLink()) kind = "symlink";
  else kind = "other";
  return { kind, device: result.dev, inode: result.ino };
}

/** Native Node.js/Bun synchronous filesystem adapter. */
export class NativeDiscoveryFileSystem implements DiscoveryFileSystem {
  lstat(path: string): DiscoveryFileInfo {
    return fileInfo(lstatSync(path, { bigint: true }));
  }

  stat(path: string): DiscoveryFileInfo {
    return fileInfo(statSync(path, { bigint: true }));
  }

  readDirectory(path: string, limit: number): readonly string[] {
    if (!Number.isSafeInteger(limit) || limit < 1) {
      throw new RangeError("directory read limit must be a positive safe integer");
    }
    const directory = opendirSync(path);
    const names: string[] = [];
    try {
      while (names.length < limit) {
        const entry = directory.readSync();
        if (entry === null) break;
        names.push(entry.name);
      }
    } finally {
      directory.closeSync();
    }
    return names;
  }

  realpath(path: string): string {
    return realpathSync.native(path);
  }
}

interface LiteralToken {
  readonly kind: "literal";
  readonly value: string;
}

interface AnyToken {
  readonly kind: "any";
}

interface StarToken {
  readonly kind: "star";
}

interface ClassToken {
  readonly kind: "class";
  readonly negated: boolean;
  readonly ranges: readonly (readonly [number, number])[];
}

type SegmentToken = LiteralToken | AnyToken | StarToken | ClassToken;

interface GlobstarSegment {
  readonly kind: "globstar";
}

interface TokenSegment {
  readonly kind: "tokens";
  readonly tokens: readonly SegmentToken[];
  readonly minCodePoints: number;
}

type GlobSegment = GlobstarSegment | TokenSegment;

function codePoint(value: string): number {
  const result = value.codePointAt(0);
  if (result === undefined) throw new Error("expected a non-empty Unicode scalar");
  return result;
}

function parseClass(
  pattern: string,
  characters: readonly string[],
  start: number,
): readonly [ClassToken, number] {
  const end = characters.indexOf("]", start + 1);
  if (end === -1) throw new GlobPatternError(pattern, "unterminated_class");
  let content = characters.slice(start + 1, end);
  const negated = content[0] === "!";
  if (negated) content = content.slice(1);
  const ranges: [number, number][] = [];
  let index = 0;
  while (index < content.length) {
    const firstCharacter = content[index] as string;
    if (index + 2 < content.length && content[index + 1] === "-") {
      const lastCharacter = content[index + 2] as string;
      const first = codePoint(firstCharacter);
      const last = codePoint(lastCharacter);
      if (first <= last) ranges.push([first, last]);
      else ranges.push([first, first], [codePoint("-"), codePoint("-")], [last, last]);
      index += 3;
    } else {
      const value = codePoint(firstCharacter);
      ranges.push([value, value]);
      index += 1;
    }
  }
  ranges.sort((left, right) => left[0] - right[0] || left[1] - right[1]);
  const normalized: [number, number][] = [];
  for (const [rangeStart, rangeEnd] of ranges) {
    const previous = normalized[normalized.length - 1];
    if (previous !== undefined && rangeStart <= previous[1] + 1) {
      previous[1] = Math.max(previous[1], rangeEnd);
    } else {
      normalized.push([rangeStart, rangeEnd]);
    }
  }
  return [{ kind: "class", negated, ranges: normalized }, end + 1];
}

function parseSegment(pattern: string, segment: string): GlobSegment {
  if (segment === "**") return { kind: "globstar" };
  if (segment.includes("**")) throw new GlobPatternError(pattern, "partial_globstar");
  const characters = Array.from(segment);
  const tokens: SegmentToken[] = [];
  let index = 0;
  while (index < characters.length) {
    const value = characters[index] as string;
    if (value === "*") {
      tokens.push({ kind: "star" });
      index += 1;
    } else if (value === "?") {
      tokens.push({ kind: "any" });
      index += 1;
    } else if (value === "[") {
      const [token, nextIndex] = parseClass(pattern, characters, index);
      tokens.push(token);
      index = nextIndex;
    } else {
      tokens.push({ kind: "literal", value });
      index += 1;
    }
  }
  const starIndexes = tokens.flatMap((token, tokenIndex) =>
    token.kind === "star" ? [tokenIndex] : [],
  );
  for (let index = 1; index < starIndexes.length; index += 1) {
    const leftStar = starIndexes[index - 1] as number;
    const rightStar = starIndexes[index] as number;
    const complexity = tokens.slice(leftStar + 1, rightStar).reduce((total, token) => {
      if (token.kind === "class") return total + Math.max(1, token.ranges.length);
      return total + 1;
    }, 0);
    if (complexity > GLOB_MAX_INTERIOR_MATCH_COMPLEXITY) {
      throw new GlobPatternError(pattern, "match_work_limit");
    }
  }
  return {
    kind: "tokens",
    tokens,
    minCodePoints: tokens.filter((token) => token.kind !== "star").length,
  };
}

function validateGlob(pattern: string): void {
  if (globCodePointLength(pattern, GLOB_MAX_PATTERN_CODEPOINTS + 1) > GLOB_MAX_PATTERN_CODEPOINTS) {
    throw new GlobPatternError(pattern, "match_work_limit");
  }
  if (pattern === "") throw new GlobPatternError(pattern, "empty");
  if (pattern.startsWith("/")) throw new GlobPatternError(pattern, "absolute");
  if (drivePattern.test(pattern)) throw new GlobPatternError(pattern, "drive_qualified");
  if (pattern.includes("\\")) throw new GlobPatternError(pattern, "backslash");
  if (pattern.split("/").some((segment) => segment === "." || segment === "..")) {
    throw new GlobPatternError(pattern, "dot_segment");
  }
}

function globCodePointLength(pattern: string, stopAfter = Number.POSITIVE_INFINITY): number {
  let count = 0;
  for (const _character of pattern) {
    count += 1;
    if (count >= stopAfter) break;
  }
  return count;
}

function validCandidatePath(path: string): boolean {
  if (path === "" || path.startsWith("/") || path.includes("\\") || drivePattern.test(path)) {
    return false;
  }
  return path.split("/").every((segment) => segment !== "" && segment !== "." && segment !== "..");
}

function classMatches(token: ClassToken, value: string): boolean {
  const candidate = codePoint(value);
  let low = 0;
  let high = token.ranges.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if ((token.ranges[middle]?.[0] ?? 0) <= candidate) low = middle + 1;
    else high = middle;
  }
  const range = token.ranges[low - 1];
  const contained = range !== undefined && candidate <= range[1];
  return token.negated ? !contained : contained;
}

function matchSegment(tokens: readonly SegmentToken[], value: string): boolean {
  const codePoints = Array.from(value);

  const fixedMatches = (fixed: readonly SegmentToken[], start: number): boolean => {
    for (const [offset, token] of fixed.entries()) {
      const candidate = codePoints[start + offset] as string;
      switch (token.kind) {
        case "any":
          break;
        case "literal":
          if (token.value !== candidate) return false;
          break;
        case "class":
          if (!classMatches(token, candidate)) return false;
          break;
        case "star":
          throw new Error("fixed glob chunk contains a star");
        default: {
          const exhaustive: never = token;
          throw new Error(`unhandled segment token: ${String(exhaustive)}`);
        }
      }
    }
    return true;
  };

  const starIndexes = tokens.flatMap((token, tokenIndex) =>
    token.kind === "star" ? [tokenIndex] : [],
  );
  if (starIndexes.length === 0) {
    return tokens.length === codePoints.length && fixedMatches(tokens, 0);
  }

  const required = tokens.length - starIndexes.length;
  if (codePoints.length < required) return false;

  const firstStar = starIndexes[0] as number;
  const lastStar = starIndexes[starIndexes.length - 1] as number;
  const prefix = tokens.slice(0, firstStar);
  const suffix = tokens.slice(lastStar + 1);
  const suffixStart = codePoints.length - suffix.length;
  if (!fixedMatches(prefix, 0) || !fixedMatches(suffix, suffixStart)) return false;

  // A star can absorb every gap, so choosing the earliest occurrence of each interior
  // fixed chunk cannot prevent a later match. Failed candidate starts advance once and
  // successful chunks never move the cursor backward. With the compile-time bound
  // above, this is exact O(m + C*n) work and O(m + n) memory.
  let cursor = prefix.length;
  for (let index = 1; index < starIndexes.length; index += 1) {
    const leftStar = starIndexes[index - 1] as number;
    const rightStar = starIndexes[index] as number;
    const chunk = tokens.slice(leftStar + 1, rightStar);
    const lastStart = suffixStart - chunk.length;
    while (cursor <= lastStart && !fixedMatches(chunk, cursor)) cursor += 1;
    if (cursor > lastStart) return false;
    cursor += chunk.length;
  }
  return true;
}

/** Compiled shared glob with complete-segment globstar semantics. */
export class CompiledGlob {
  readonly pattern: string;
  private readonly segments: readonly GlobSegment[];
  private readonly minSegments: number;
  private readonly tokenCount: number;
  private readonly workFactor: number;

  private constructor(pattern: string, segments: readonly GlobSegment[]) {
    this.pattern = pattern;
    this.segments = segments;
    this.minSegments = segments.filter((segment) => segment.kind !== "globstar").length;
    this.tokenCount = segments.reduce(
      (total, segment) => total + (segment.kind === "globstar" ? 1 : segment.tokens.length),
      0,
    );
    this.workFactor = segments.reduce(
      (total, segment) =>
        total +
        (segment.kind === "globstar"
          ? 1
          : segment.tokens.reduce(
              (subtotal, token) =>
                subtotal + (token.kind === "class" ? Math.max(1, token.ranges.length) : 1),
              0,
            )),
      0,
    );
  }

  /** Validate and compile one invocation pattern. */
  static compile(pattern: string): CompiledGlob {
    validateGlob(pattern);
    const segments: GlobSegment[] = [];
    for (const part of pattern.split("/")) {
      const segment = parseSegment(pattern, part);
      if (
        segment.kind === "globstar" &&
        segments.length > 0 &&
        segments[segments.length - 1]?.kind === "globstar"
      ) {
        continue;
      }
      segments.push(segment);
    }
    return new CompiledGlob(pattern, segments);
  }

  /** Match one normalized operand-relative path case-sensitively. */
  matches(path: string): boolean {
    return this.matchesForDiscovery(path);
  }

  private matchesForDiscovery(path: string, budget?: GlobWorkBudget): boolean {
    if (!validCandidatePath(path)) return false;
    const pathSegments = path.split("/");
    const pathSegmentLengths = pathSegments.map((segment) => Array.from(segment).length);
    budget?.charge(
      this.segments.length * (pathSegments.length + 1) +
        Math.max(1, this.workFactor) *
          Math.max(
            1,
            pathSegmentLengths.reduce((total, length) => total + length, 0),
          ),
    );
    if (pathSegments.length < this.minSegments) return false;
    let previous = Array.from({ length: pathSegments.length + 1 }, (_, index) => index === 0);
    for (const segment of this.segments) {
      const current = Array.from({ length: pathSegments.length + 1 }, () => false);
      if (segment.kind === "globstar") {
        current[0] = previous[0] as boolean;
        for (let pathIndex = 1; pathIndex <= pathSegments.length; pathIndex += 1) {
          current[pathIndex] =
            (previous[pathIndex] as boolean) || (current[pathIndex - 1] as boolean);
        }
      } else {
        for (let pathIndex = 1; pathIndex <= pathSegments.length; pathIndex += 1) {
          current[pathIndex] =
            (previous[pathIndex - 1] as boolean) &&
            (pathSegmentLengths[pathIndex - 1] as number) >= segment.minCodePoints &&
            matchSegment(segment.tokens, pathSegments[pathIndex - 1] as string);
        }
      }
      previous = current;
      if (!previous.some(Boolean)) return false;
    }
    return previous[pathSegments.length] as boolean;
  }

  static boundedMatch(pattern: CompiledGlob, path: string, budget: GlobWorkBudget): boolean {
    return pattern.matchesForDiscovery(path, budget);
  }

  static aggregateCost(pattern: CompiledGlob): { tokens: number; complexity: number } {
    return { tokens: pattern.tokenCount, complexity: pattern.workFactor };
  }
}

/** Complete deterministic artifact-discovery request. */
export interface DiscoveryRequest {
  readonly operands: readonly string[];
  readonly recursive: boolean;
  readonly profile: DiscoveryProfile;
  readonly includes: readonly string[];
  readonly excludes: readonly string[];
  readonly invocationDirectory: string;
  readonly pathFlavor: DiscoveryPathFlavor;
}

/** One readable file spelling selected for later validation. */
export interface DiscoveredArtifact {
  readonly kind: "artifact";
  readonly path: string;
  readonly displayPath: string;
}

/** Stable input failure found while inspecting one operand group. */
export interface DiscoveryInputError {
  readonly kind: "input_error";
  readonly reason: DiscoveryInputReason;
  readonly message: string;
  readonly source: string;
}

export type DiscoveryEntry = DiscoveredArtifact | DiscoveryInputError;

/** Ordered artifacts and input failures across all operand groups. */
export interface DiscoveryResult {
  readonly entries: readonly DiscoveryEntry[];
}

interface Candidate {
  readonly path: string;
  readonly displayPath: string;
  readonly info: DiscoveryFileInfo;
}

interface DirectoryWork {
  readonly path: string;
  readonly info: DiscoveryFileInfo;
  readonly depth: number;
}

type GroupEntry = Candidate | DiscoveryInputError;

class PathOperations {
  private readonly path;

  constructor(readonly flavor: DiscoveryPathFlavor) {
    this.path = flavor === "windows" ? win32 : posix;
  }

  absolute(path: string, cwd: string): string {
    if (this.flavor === "windows") {
      if (path.startsWith("\\\\") || path.startsWith("//")) return win32.normalize(path);
      const match = /^([A-Za-z]:)(.*)$/.exec(path);
      if (match !== null) {
        const drive = match[1] as string;
        const tail = match[2] as string;
        if (/^[\\/]/.test(tail)) return win32.normalize(path);
        const cwdDrive = /^([A-Za-z]:)/.exec(cwd)?.[1];
        if (cwdDrive?.toLowerCase() === drive.toLowerCase()) {
          return win32.normalize(win32.join(cwd, tail));
        }
        // A request carries one invocation directory, not Windows' hidden per-drive
        // current directories. Resolve another drive from its root so injected and
        // native adapters stay deterministic.
        return win32.normalize(`${drive}\\${tail.replace(/^[/\\]+/, "")}`);
      }
      if (/^[\\/]/.test(path)) {
        return win32.normalize(win32.join(win32.parse(cwd).root, path.replace(/^[/\\]+/, "")));
      }
    }
    if (this.path.isAbsolute(path)) return this.path.normalize(path);
    return this.path.normalize(this.path.join(cwd, path));
  }

  join(parent: string, child: string): string {
    return this.path.normalize(this.path.join(parent, child));
  }

  relative(path: string, start: string): string {
    return this.path.relative(start, path);
  }

  normalize(path: string): string {
    return this.path.normalize(path);
  }

  isAbsolute(path: string): boolean {
    return this.path.isAbsolute(path);
  }

  display(path: string, cwd: string): string {
    const relative = this.relative(path, cwd);
    const separator = this.flavor === "windows" ? "\\" : "/";
    const contained =
      !this.isAbsolute(relative) && relative !== ".." && !relative.startsWith(`..${separator}`);
    return (contained ? relative : path).replaceAll("\\", "/");
  }
}

function inputError(reason: DiscoveryInputReason, source: string): DiscoveryInputError {
  return { kind: "input_error", reason, message: inputMessages[reason], source };
}

function reasonFromError(error: unknown): DiscoveryInputReason {
  if (typeof error === "object" && error !== null && "code" in error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT" || code === "ENOTDIR") return "not_found";
  }
  return "unreadable";
}

function groupSort(left: GroupEntry, right: GroupEntry): number {
  const leftDisplay = "displayPath" in left ? left.displayPath : left.source;
  const rightDisplay = "displayPath" in right ? right.displayPath : right.source;
  const displayOrder = compareUnicodeCodePoints(leftDisplay, rightDisplay);
  if (displayOrder !== 0) return displayOrder;
  const kindOrder = compareUnicodeCodePoints(
    "info" in left ? "artifact" : left.kind,
    "info" in right ? "artifact" : right.kind,
  );
  if (kindOrder !== 0) return kindOrder;
  const leftPath = "path" in left ? left.path : left.source;
  const rightPath = "path" in right ? right.path : right.source;
  return compareUnicodeCodePoints(leftPath, rightPath);
}

function eligible(
  relativePath: string,
  profile: DiscoveryProfile,
  includes: readonly CompiledGlob[],
  excludes: readonly CompiledGlob[],
  workBudget: GlobWorkBudget,
): boolean {
  if (!profileExtensions[profile].some((extension) => relativePath.endsWith(extension))) {
    return false;
  }
  if (
    includes.length > 0 &&
    !includes.some((pattern) => CompiledGlob.boundedMatch(pattern, relativePath, workBudget))
  ) {
    return false;
  }
  return !excludes.some((pattern) => CompiledGlob.boundedMatch(pattern, relativePath, workBudget));
}

function discoverDirectory(
  root: string,
  rootInfo: DiscoveryFileInfo,
  request: DiscoveryRequest,
  operations: PathOperations,
  filesystem: DiscoveryFileSystem,
  includes: readonly CompiledGlob[],
  excludes: readonly CompiledGlob[],
  workBudget: GlobWorkBudget,
): { entries: GroupEntry[]; foundCandidateOrFailure: boolean } {
  const entries: GroupEntry[] = [];
  let foundCandidateOrFailure = false;
  let inspectedEntries = 0;
  let budgetExceeded = false;
  const visitedDirectories = new Set<string>();
  const stack: DirectoryWork[] = [{ path: root, info: rootInfo, depth: 0 }];
  while (stack.length > 0) {
    const work = stack.pop();
    if (work === undefined) throw new Error("directory traversal stack unexpectedly empty");
    const displayDirectory = operations.display(work.path, request.invocationDirectory);
    let directoryIdentity: string;
    try {
      directoryIdentity = identity(work.path, work.info, operations, filesystem);
    } catch (error) {
      foundCandidateOrFailure = true;
      entries.push(inputError(reasonFromError(error), displayDirectory));
      continue;
    }
    if (visitedDirectories.has(directoryIdentity)) continue;
    visitedDirectories.add(directoryIdentity);
    const remainingEntries = DISCOVERY_MAX_ENTRIES - inspectedEntries;
    let names: readonly string[];
    try {
      names = filesystem.readDirectory(work.path, remainingEntries + 1);
    } catch (error) {
      foundCandidateOrFailure = true;
      entries.push(inputError(reasonFromError(error), displayDirectory));
      continue;
    }
    if (names.length > remainingEntries) {
      foundCandidateOrFailure = true;
      entries.push(inputError("discovery_limit", displayDirectory));
      budgetExceeded = true;
      stack.length = 0;
      continue;
    }
    names = Array.from(names).sort(compareUnicodeCodePoints);
    const childDirectories: DirectoryWork[] = [];
    for (const name of names) {
      const child = operations.join(work.path, name);
      const displayPath = operations.display(child, request.invocationDirectory);
      inspectedEntries += 1;
      const relativePath = operations.relative(child, root).replaceAll("\\", "/");
      let info: DiscoveryFileInfo;
      try {
        info = filesystem.lstat(child);
      } catch (error) {
        foundCandidateOrFailure = true;
        entries.push(inputError(reasonFromError(error), displayPath));
        continue;
      }
      if (info.kind === "symlink") continue;
      if (info.kind === "directory") {
        const childDepth = work.depth + 1;
        if (childDepth > DISCOVERY_MAX_DEPTH) {
          foundCandidateOrFailure = true;
          entries.push(inputError("discovery_limit", displayPath));
          budgetExceeded = true;
          break;
        }
        childDirectories.push({ path: child, info, depth: childDepth });
        continue;
      }
      try {
        if (!eligible(relativePath, request.profile, includes, excludes, workBudget)) continue;
      } catch (error) {
        if (!(error instanceof GlobWorkLimitExceeded)) throw error;
        foundCandidateOrFailure = true;
        entries.push(inputError("discovery_limit", displayPath));
        budgetExceeded = true;
        break;
      }
      foundCandidateOrFailure = true;
      if (info.kind === "file") entries.push({ path: child, displayPath, info });
      else entries.push(inputError("unreadable", displayPath));
    }
    if (budgetExceeded) stack.length = 0;
    else stack.push(...childDirectories.reverse());
  }
  const retainedEntries = budgetExceeded
    ? entries.filter((entry): entry is DiscoveryInputError => !("info" in entry))
    : entries;
  retainedEntries.sort(groupSort);
  return { entries: retainedEntries, foundCandidateOrFailure };
}

function identity(
  path: string,
  info: DiscoveryFileInfo,
  operations: PathOperations,
  filesystem: DiscoveryFileSystem,
): string {
  if (info.device !== null && info.inode !== null && info.inode !== 0n) {
    return `file_id:${info.device}:${info.inode}`;
  }
  return `realpath:${operations.normalize(filesystem.realpath(path))}`;
}

function appendCandidate(
  candidate: Candidate,
  entries: DiscoveryEntry[],
  identities: Set<string>,
  operations: PathOperations,
  filesystem: DiscoveryFileSystem,
): void {
  let fileIdentity: string;
  try {
    fileIdentity = identity(candidate.path, candidate.info, operations, filesystem);
  } catch (error) {
    entries.push(inputError(reasonFromError(error), candidate.displayPath));
    return;
  }
  if (identities.has(fileIdentity)) return;
  identities.add(fileIdentity);
  entries.push({ kind: "artifact", path: candidate.path, displayPath: candidate.displayPath });
}

function validateRequest(request: DiscoveryRequest): {
  includes: readonly CompiledGlob[];
  excludes: readonly CompiledGlob[];
} {
  if (request.operands.length === 0) {
    throw new DiscoveryUsageError("artifact discovery requires at least one operand");
  }
  if (request.profile !== "frontmatter-md" && request.profile !== "pure-yaml") {
    throw new DiscoveryUsageError(`invalid discovery profile: ${String(request.profile)}`);
  }
  if (request.pathFlavor !== "posix" && request.pathFlavor !== "windows") {
    throw new DiscoveryUsageError(`invalid path flavor: ${String(request.pathFlavor)}`);
  }
  if (!request.recursive && (request.includes.length > 0 || request.excludes.length > 0)) {
    throw new DiscoveryUsageError("include and exclude patterns require recursive discovery");
  }
  const compiled: CompiledGlob[] = [];
  let totalTokens = 0;
  let totalComplexity = 0;
  let totalCodePoints = 0;
  for (const pattern of [...request.includes, ...request.excludes]) {
    totalCodePoints += globCodePointLength(pattern, GLOB_MAX_PATTERN_CODEPOINTS + 1);
    if (totalCodePoints > GLOB_MAX_TOTAL_PATTERN_CODEPOINTS) {
      throw new GlobPatternError(pattern, "match_work_limit");
    }
    const item = CompiledGlob.compile(pattern);
    compiled.push(item);
    const cost = CompiledGlob.aggregateCost(item);
    totalTokens += cost.tokens;
    totalComplexity += cost.complexity;
    if (
      compiled.length > GLOB_MAX_PATTERNS ||
      totalTokens > GLOB_MAX_TOTAL_TOKENS ||
      totalComplexity > GLOB_MAX_TOTAL_MATCH_COMPLEXITY
    ) {
      throw new GlobPatternError(pattern, "match_work_limit");
    }
  }
  return {
    includes: compiled.slice(0, request.includes.length),
    excludes: compiled.slice(request.includes.length),
  };
}

/**
 * Discover files and stable input errors without following directory symlinks.
 *
 * Inspection and later filesystem operations are separate. A directory can be replaced
 * between lstat and readDirectory, and an artifact can be replaced after lstat but before
 * the caller reads it. This adapter therefore does not claim race-free no-follow
 * semantics; callers must still handle read-time failures. Per-operand identity tracking
 * and resource limits bound recursive traversal.
 */
export function discoverArtifacts(
  request: DiscoveryRequest,
  filesystem: DiscoveryFileSystem = new NativeDiscoveryFileSystem(),
): DiscoveryResult {
  const patterns = validateRequest(request);
  const operations = new PathOperations(request.pathFlavor);
  if (!operations.isAbsolute(request.invocationDirectory)) {
    throw new DiscoveryUsageError("invocation directory must be absolute");
  }
  const cwd = operations.normalize(request.invocationDirectory);
  const normalizedRequest: DiscoveryRequest = { ...request, invocationDirectory: cwd };
  const entries: DiscoveryEntry[] = [];
  const identities = new Set<string>();
  const globWorkBudget = new GlobWorkBudget();

  for (const operand of request.operands) {
    const path = operations.absolute(operand, cwd);
    const displayPath = operations.display(path, cwd);
    let info: DiscoveryFileInfo;
    try {
      info = filesystem.lstat(path);
    } catch (error) {
      entries.push(inputError(reasonFromError(error), displayPath));
      continue;
    }
    if (info.kind === "symlink") {
      let targetInfo: DiscoveryFileInfo;
      try {
        targetInfo = filesystem.stat(path);
      } catch (error) {
        entries.push(inputError(reasonFromError(error), displayPath));
        continue;
      }
      if (targetInfo.kind !== "file") {
        entries.push(inputError("unreadable", displayPath));
        continue;
      }
      appendCandidate(
        { path, displayPath, info: targetInfo },
        entries,
        identities,
        operations,
        filesystem,
      );
      continue;
    }
    if (info.kind === "file") {
      appendCandidate({ path, displayPath, info }, entries, identities, operations, filesystem);
      continue;
    }
    if (info.kind !== "directory") {
      entries.push(inputError("unreadable", displayPath));
      continue;
    }
    if (!request.recursive) {
      entries.push(inputError("directory_requires_recursive", displayPath));
      continue;
    }
    const group = discoverDirectory(
      path,
      info,
      normalizedRequest,
      operations,
      filesystem,
      patterns.includes,
      patterns.excludes,
      globWorkBudget,
    );
    if (!group.foundCandidateOrFailure) {
      entries.push(inputError("no_matches", displayPath));
      continue;
    }
    for (const item of group.entries) {
      if ("info" in item) {
        appendCandidate(item, entries, identities, operations, filesystem);
      } else {
        entries.push(item);
      }
    }
  }
  return { entries };
}
