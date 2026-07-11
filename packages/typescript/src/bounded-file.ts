/** Bounded reads for untrusted artifact and schema files. */
import {
  closeSync,
  constants,
  fstatSync,
  lstatSync,
  openSync,
  readSync,
  realpathSync,
} from "node:fs";
import { PortableValueError } from "./core/value-domain.js";

/** Maximum allocation for each incremental file read. */
const FILE_READ_CHUNK_BYTES = 64 * 1024;
/** Extra byte that distinguishes the exact limit from oversized input. */
const LIMIT_SENTINEL_BYTES = 1;

/** Return only file-open flags supported by the target platform. */
export function fileOpenFlags(platform: NodeJS.Platform = process.platform): number {
  if (platform === "win32") return constants.O_RDONLY;
  return constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK;
}

/** Canonical path and file identity authorized before a bounded read. */
export interface BoundedFileExpectation {
  readonly canonicalPath: string;
  readonly device: bigint;
  readonly inode: bigint;
  readonly size: bigint;
  readonly modifiedNs: bigint;
  readonly changedNs: bigint;
}

/** Bytes plus the canonical identity that supplied them. */
export interface BoundedFileRead {
  readonly data: Uint8Array;
  readonly expectation: BoundedFileExpectation;
}

function nonRegularFileError(path: string): NodeJS.ErrnoException {
  const error = new Error(`bounded input must be a regular file: ${path}`) as NodeJS.ErrnoException;
  error.code = "EINVAL";
  error.errno = -22;
  error.path = path;
  error.syscall = "open";
  return error;
}

function stalePathError(path: string): NodeJS.ErrnoException {
  const error = new Error(
    `bounded input changed before it could be opened: ${path}`,
  ) as NodeJS.ErrnoException;
  error.code = "ESTALE";
  error.errno = -116;
  error.path = path;
  error.syscall = "open";
  return error;
}

function matchesExpected(
  value: {
    readonly dev: bigint;
    readonly ino: bigint;
    readonly size: bigint;
    readonly mtimeNs: bigint;
    readonly ctimeNs: bigint;
  },
  expected: BoundedFileExpectation,
): boolean {
  return (
    value.ino !== 0n &&
    expected.inode !== 0n &&
    value.dev === expected.device &&
    value.ino === expected.inode &&
    value.size === expected.size &&
    value.mtimeNs === expected.modifiedNs &&
    value.ctimeNs === expected.changedNs
  );
}

function sameSnapshot(
  left: {
    readonly dev: bigint;
    readonly ino: bigint;
    readonly size: bigint;
    readonly mtimeNs: bigint;
    readonly ctimeNs: bigint;
  },
  right: {
    readonly dev: bigint;
    readonly ino: bigint;
    readonly size: bigint;
    readonly mtimeNs: bigint;
    readonly ctimeNs: bigint;
  },
): boolean {
  return (
    left.ino !== 0n &&
    right.ino !== 0n &&
    left.dev === right.dev &&
    left.ino === right.ino &&
    left.size === right.size &&
    left.mtimeNs === right.mtimeNs &&
    left.ctimeNs === right.ctimeNs
  );
}

/** Read one identity-stable regular file without blocking on special nodes. */
export function readBoundedFile(
  path: string,
  maxBytes: number,
  expected?: BoundedFileExpectation,
): BoundedFileRead {
  // Callers own containment policy. An expectation binds an earlier authorization
  // decision to this open; repeated canonical checks catch persistent parent swaps,
  // while descriptor identity catches substitutions around the open itself.
  const sourcePath = realpathSync.native(path);
  if (expected !== undefined && sourcePath !== expected.canonicalPath) {
    throw stalePathError(path);
  }
  const sourceStat = lstatSync(sourcePath, { bigint: true });
  if (!sourceStat.isFile()) throw nonRegularFileError(path);
  if (sourceStat.ino === 0n) throw stalePathError(path);
  if (sourceStat.size > BigInt(maxBytes)) {
    throw new PortableValueError("maximum resource size exceeded");
  }
  if (expected !== undefined && !matchesExpected(sourceStat, expected)) {
    throw stalePathError(path);
  }
  if (realpathSync.native(path) !== sourcePath) throw stalePathError(path);
  const handle = openSync(sourcePath, fileOpenFlags());
  const limit = maxBytes + LIMIT_SENTINEL_BYTES;
  const capacity = Math.max(
    1,
    sourceStat.size >= BigInt(limit) ? limit : Number(sourceStat.size) + LIMIT_SENTINEL_BYTES,
  );
  const buffer = Buffer.alloc(capacity);
  let total = 0;
  try {
    const openedStat = fstatSync(handle, { bigint: true });
    if (!openedStat.isFile()) throw nonRegularFileError(path);
    if (
      openedStat.dev !== sourceStat.dev ||
      openedStat.ino !== sourceStat.ino ||
      openedStat.size !== sourceStat.size
    ) {
      throw stalePathError(path);
    }
    // Windows can expose timestamps with different representations through path
    // and descriptor stat calls. Compare each interface only with itself.
    if (!sameSnapshot(sourceStat, lstatSync(sourcePath, { bigint: true }))) {
      throw stalePathError(path);
    }
    if (realpathSync.native(path) !== sourcePath) throw stalePathError(path);
    while (total < capacity) {
      const remaining = capacity - total;
      const count = readSync(
        handle,
        buffer,
        total,
        Math.min(FILE_READ_CHUNK_BYTES, remaining),
        null,
      );
      if (count === 0) break;
      total += count;
    }
    let finalStat = fstatSync(handle, { bigint: true });
    // Compare a second descriptor pass as defense in depth for runtimes or filesystems
    // that cannot expose a dependable change timestamp for a same-size rewrite. This
    // does not claim an atomic snapshot against a hostile writer that deliberately
    // coordinates both passes.
    if (process.platform === "win32" && BigInt(total) === openedStat.size) {
      const verification = Buffer.allocUnsafe(Math.min(FILE_READ_CHUNK_BYTES, capacity));
      let verified = 0;
      while (verified < total) {
        const count = readSync(
          handle,
          verification,
          0,
          Math.min(verification.byteLength, total - verified),
          verified,
        );
        if (
          count === 0 ||
          Buffer.compare(
            verification.subarray(0, count),
            buffer.subarray(verified, verified + count),
          ) !== 0
        ) {
          throw stalePathError(path);
        }
        verified += count;
      }
      finalStat = fstatSync(handle, { bigint: true });
    }
    if (!sameSnapshot(finalStat, openedStat) || BigInt(total) !== openedStat.size) {
      throw stalePathError(path);
    }
    if (
      !sameSnapshot(sourceStat, lstatSync(sourcePath, { bigint: true })) ||
      realpathSync.native(path) !== sourcePath
    ) {
      throw stalePathError(path);
    }
  } finally {
    closeSync(handle);
  }
  if (total > maxBytes) throw new PortableValueError("maximum resource size exceeded");
  return {
    data: Uint8Array.from(buffer.subarray(0, total)),
    expectation: {
      canonicalPath: sourcePath,
      device: sourceStat.dev,
      inode: sourceStat.ino,
      size: sourceStat.size,
      modifiedNs: sourceStat.mtimeNs,
      changedNs: sourceStat.ctimeNs,
    },
  };
}

/** Read bytes through {@link readBoundedFile}. */
export function readBoundedBytes(
  path: string,
  maxBytes: number,
  expected?: BoundedFileExpectation,
): Uint8Array {
  return readBoundedFile(path, maxBytes, expected).data;
}
