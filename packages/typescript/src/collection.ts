/** Bounded, read-only discovery and structural validation of a directory of artifacts. */

import { createHash } from "node:crypto";
import {
  closeSync,
  constants,
  type Dirent,
  fstatSync,
  lstatSync,
  opendirSync,
  openSync,
  readSync,
  realpathSync,
  type Stats,
} from "node:fs";
import { extname, isAbsolute, join, posix, relative, sep } from "node:path";
import { conformArtifact } from "./conform.js";
import { isMapping } from "./guards.js";
import { byCodePoint } from "./identity.js";
import {
  metadataToOutput,
  parseSchemaMetadata,
  type SchemaMetadata,
  SchemaMetadataError,
  type SchemaProfile,
} from "./models.js";
import { opensFrontmatterFence, PortableInputError, splitFrontmatter } from "./portable.js";
import { repairYamlText } from "./repair.js";
import { SchemaView } from "./schemaView.js";
import {
  inferEnvelopeKey,
  type ParsedDocument,
  parseFrontmatterText,
  parseYamlText,
  type RepairRecord,
  validateArtifact,
  validateStructural,
  YamlParseError,
} from "./validate.js";

export type RecordState = "valid" | "repaired" | "invalid" | "unbound" | "unreadable" | "malformed";
const SCHEMA_SUFFIXES = [".schema.yaml", ".schema.yml", ".schema.json"];
const ARTIFACT_SUFFIXES = new Set([".md", ".yaml", ".yml", ".json"]);
const SNAPSHOT_VERSION = 1;

export interface CollectionSchema {
  path: string;
  digest: string;
  contract: string | null;
  document: Record<string, unknown>;
}

export interface CollectionRecord {
  path: string;
  profile: SchemaProfile;
  state: RecordState;
  metadata?: SchemaMetadata;
  values?: Record<string, unknown>;
  host?: Record<string, unknown>;
  body?: string;
  schema?: string;
  errors?: readonly object[];
  repairs?: readonly RepairRecord[];
  envelope?: string | null;
}

interface ScanProblem {
  path: string;
  code: string;
}

interface ScannedFile {
  stamp: string;
  record?: CollectionRecord;
  recordYaml?: string;
  schema?: CollectionSchema;
  problem?: string;
}

export interface CollectionScan {
  records: readonly CollectionRecord[];
  schemas: readonly CollectionSchema[];
  problems: readonly ScanProblem[];
  complete: boolean;
  added: readonly string[];
  changed: readonly string[];
  removed: readonly string[];
  /** Refresh data for a trusted cache. The scan result can be serialized as JSON. */
  snapshot: {
    version: number;
    scope: string;
    files: ReadonlyArray<readonly [string, ScannedFile]>;
  };
}

export interface CollectionOptions {
  maxEntries?: number;
  maxFileBytes?: number;
  maxTotalBytes?: number;
  ignore?: (path: string, isDirectory: boolean) => boolean;
  previous?: CollectionScan;
  ignoreId?: string;
}

function portablePath(root: string, path: string): string {
  return relative(root, path).split(sep).join("/");
}

function sameFile(a: Stats, b: Stats): boolean {
  return (
    a.dev === b.dev &&
    a.ino === b.ino &&
    a.size === b.size &&
    a.mtimeMs === b.mtimeMs &&
    a.ctimeMs === b.ctimeMs
  );
}

function boundedRead(path: string, expected: Stats): string {
  const fd = openSync(
    path,
    constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0) | constants.O_NONBLOCK,
  );
  try {
    const before = fstatSync(fd);
    if (!before.isFile() || !sameFile(before, expected)) {
      throw new Error("file changed during scan");
    }
    const buffer = Buffer.alloc(before.size + 1);
    let offset = 0;
    while (offset < buffer.length) {
      const count = readSync(fd, buffer, offset, buffer.length - offset, null);
      if (count === 0) break;
      offset += count;
    }
    if (offset !== before.size || !sameFile(before, fstatSync(fd))) {
      throw new Error("file changed during scan");
    }
    return new TextDecoder("utf-8", { fatal: true }).decode(buffer.subarray(0, offset));
  } finally {
    closeSync(fd);
  }
}

function walk(
  root: string,
  maxEntries: number,
  ignore: CollectionOptions["ignore"],
  problems: ScanProblem[],
): { files: Map<string, Stats>; complete: boolean } {
  const files = new Map<string, Stats>();
  const directories = [root];
  let walked = 0;
  while (directories.length) {
    const directory = directories.pop() as string;
    let entries: Dirent[];
    try {
      if (realpathSync(directory) !== directory) continue;
      const listing = opendirSync(directory);
      entries = [];
      try {
        for (let entry = listing.readSync(); entry !== null; entry = listing.readSync()) {
          walked += 1;
          if (walked > maxEntries) return { files, complete: false };
          entries.push(entry);
        }
      } finally {
        listing.closeSync();
      }
    } catch {
      problems.push({ path: portablePath(root, directory) || ".", code: "directory_unreadable" });
      continue;
    }
    for (const entry of entries.sort((a, b) => byCodePoint(b.name, a.name))) {
      if (entry.name.startsWith(".") || entry.isSymbolicLink()) continue;
      const path = join(directory, entry.name);
      const name = portablePath(root, path);
      const isDirectory = entry.isDirectory();
      if (ignore?.(name, isDirectory)) continue;
      if (isDirectory) {
        directories.push(path);
      } else if (entry.isFile() && ARTIFACT_SUFFIXES.has(extname(path))) {
        try {
          files.set(name, lstatSync(path));
        } catch {
          problems.push({ path: name, code: "entry_unreadable" });
        }
      }
    }
  }
  return { files, complete: problems.length === 0 };
}

function readRecord(path: string, text: string): Pick<ScannedFile, "record" | "recordYaml"> {
  const profile = path.endsWith(".md") ? "frontmatter-md" : "pure-yaml";
  const split = profile === "frontmatter-md" ? splitFrontmatter(text) : null;
  if (profile === "frontmatter-md" && !opensFrontmatterFence(text)) return {};
  let yaml = split?.metadataText ?? text;
  if (!yaml.includes("softschema") && !yaml.includes("\\")) return {};
  let parsed: ParsedDocument;
  let repairs: RepairRecord[] = [];
  try {
    parsed =
      profile === "frontmatter-md" ? parseFrontmatterText(text, path) : parseYamlText(text, path);
  } catch (error) {
    if (!(error instanceof PortableInputError || error instanceof YamlParseError)) throw error;
    const repaired =
      profile === "pure-yaml" || split ? repairYamlText(yaml.replaceAll("\r\n", "\n")) : null;
    if (!repaired?.ok || repaired.text === null) {
      return {
        record: { path, profile, state: "unreadable", errors: [{ kind: "yaml_parse_error" }] },
      };
    }
    yaml = repaired.text;
    parsed = { hasFence: split !== null, value: parseYamlText(yaml, path).value };
    repairs = repaired.records;
  }
  const document = parsed.value;
  if (!isMapping(document) || !Object.hasOwn(document, "softschema")) return {};
  let metadata: SchemaMetadata | null;
  try {
    metadata = parseSchemaMetadata(document.softschema);
  } catch (error) {
    if (!(error instanceof SchemaMetadataError)) throw error;
    metadata = null;
  }
  if (!metadata) {
    return {
      record: {
        path,
        profile,
        state: "malformed",
        errors: [{ kind: "document_softschema_invalid" }],
      },
    };
  }
  const declaration = metadataToOutput({ ...metadata, schema: null });
  const extracted = validateArtifact(
    path,
    {
      id: metadata.contractId,
      profile,
      status: metadata.status ?? "soft",
      model: null,
      envelopeKey: null,
      schemaPath: null,
    },
    {
      document: { hasFence: parsed.hasFence, value: { ...document, softschema: declaration } },
    },
  );
  const values = extracted.values;
  if (values === null) {
    return {
      record: { path, profile, state: "malformed", metadata, errors: extracted.structural.errors },
    };
  }
  const host =
    metadata.envelope === null
      ? {}
      : Object.fromEntries(
          Object.entries(document).filter(
            ([key]) => key !== "softschema" && key !== metadata.envelope,
          ),
        );
  return {
    record: {
      path,
      profile,
      state: "unbound",
      metadata,
      values,
      host,
      body: split ? text.slice(split.bodyOffset) : "",
      repairs,
      envelope:
        metadata.envelope ?? (profile === "frontmatter-md" ? inferEnvelopeKey(document) : null),
    },
    recordYaml: yaml,
  };
}

function pointer(record: CollectionRecord): string {
  const ref = record.metadata?.schema;
  if (!ref || isAbsolute(ref) || ref.includes("\\") || /^[A-Za-z]:/.test(ref)) return "";
  const path = posix.normalize(posix.join(posix.dirname(record.path), ref));
  return path === ".." || path.startsWith("../") ? "" : path;
}

function bind(
  record: CollectionRecord,
  recordYaml: string | undefined,
  schemas: Map<string, CollectionSchema>,
  byContract: Map<string, Map<string, CollectionSchema>>,
  prior: CollectionRecord | undefined,
  priorDigest: string | undefined,
): CollectionRecord {
  if (!record.metadata || !record.values) return record;
  const contract = record.metadata.contractId;
  let schema = schemas.get(pointer(record));
  if (!schema || (schema.contract !== null && schema.contract !== contract)) {
    const candidates = byContract.get(contract);
    schema = candidates?.size === 1 ? candidates.values().next().value : undefined;
    if (!schema) {
      return {
        ...record,
        errors: [{ kind: candidates?.size ? "schema_ambiguous" : "schema_unbound" }],
      };
    }
  }
  if (prior?.schema === schema.path && priorDigest === schema.digest) return prior;
  const verdict = validateStructural(record.values, schema.document, {
    strictExtras: record.metadata.status === "enforced",
  });
  if (verdict.execution === "completed" && !verdict.ok && recordYaml) {
    const conformed = conformArtifact(record.path, {
      schema: schema.document,
      profile: "pure-yaml",
      envelopeKey: record.envelope ?? null,
      text: recordYaml,
      write: false,
    });
    if (conformed.changed && conformed.text !== null) {
      const { value: root } = parseYamlText(conformed.text, record.path);
      if (isMapping(root)) {
        const values = record.envelope
          ? root[record.envelope]
          : Object.fromEntries(Object.entries(root).filter(([key]) => key !== "softschema"));
        const final = validateStructural(values, schema.document, {
          strictExtras: record.metadata.status === "enforced",
        });
        if (isMapping(values) && final.execution === "completed" && final.ok) {
          return {
            ...record,
            state: "repaired",
            schema: schema.path,
            values,
            repairs: [...(record.repairs ?? []), ...conformed.records],
          };
        }
      }
    }
  }
  let state: RecordState = "unbound";
  if (verdict.execution === "completed") {
    state = verdict.ok ? (record.repairs?.length ? "repaired" : "valid") : "invalid";
  }
  return { ...record, state, schema: schema.path, errors: verdict.errors };
}

function scanFile(path: string, stamp: string, text: string): ScannedFile {
  if (!SCHEMA_SUFFIXES.some((suffix) => path.endsWith(suffix))) {
    return { stamp, ...readRecord(path, text) };
  }
  try {
    const { value: document } = parseYamlText(text, path);
    if (!isMapping(document)) return { stamp, problem: "schema_invalid" };
    const contract = new SchemaView(document).contractId;
    const digest = createHash("sha256").update(text).digest("hex");
    return { stamp, schema: { path, digest, contract, document } };
  } catch (error) {
    if (!(error instanceof PortableInputError || error instanceof SchemaMetadataError)) throw error;
    return { stamp, problem: "schema_invalid" };
  }
}

/** Previous scans with the same bounds and ignore identity reuse their unchanged inputs. */
export function scanCollection(input: string, options: CollectionOptions = {}): CollectionScan {
  const { maxEntries = 50_000, maxFileBytes = 1024 ** 2, maxTotalBytes = 64 * 1024 ** 2 } = options;
  if (![maxEntries, maxFileBytes, maxTotalBytes].every((n) => Number.isSafeInteger(n) && n > 0)) {
    throw new Error("collection bounds must be positive integers");
  }
  let root: string;
  try {
    root = realpathSync(input);
    if (!lstatSync(root).isDirectory()) throw new Error();
  } catch {
    throw new Error("collection root must be a directory");
  }
  const scope = JSON.stringify([
    root,
    Boolean(options.ignore),
    options.ignoreId ?? null,
    maxEntries,
    maxFileBytes,
    maxTotalBytes,
  ]);
  const previous =
    options.previous?.snapshot.version === SNAPSHOT_VERSION &&
    options.previous.snapshot.scope === scope &&
    (!options.ignore || options.ignoreId !== undefined)
      ? options.previous
      : undefined;
  const saved = new Map(previous?.snapshot.files);
  const priorRecords = new Map(previous?.records.map((record) => [record.path, record]));
  const priorDigests = new Map(previous?.schemas.map((schema) => [schema.path, schema.digest]));
  const scanned = new Map<string, ScannedFile>();
  const problems: ScanProblem[] = [];
  const discovered = walk(root, maxEntries, options.ignore, problems);
  let complete = discovered.complete;
  let remaining = maxTotalBytes;
  const records: CollectionRecord[] = [];
  const schemas = new Map<string, CollectionSchema>();
  const byContract = new Map<string, Map<string, CollectionSchema>>();
  for (const path of [...discovered.files.keys()].sort(byCodePoint)) {
    const status = discovered.files.get(path) as Stats;
    if (status.size > maxFileBytes) {
      problems.push({ path, code: "file_too_large" });
      complete = false;
      continue;
    }
    if (status.size > remaining) {
      complete = false;
      break;
    }
    remaining -= status.size;
    const stamp = [status.dev, status.ino, status.size, status.mtimeMs, status.ctimeMs].join(":");
    let entry = saved.get(path);
    if (!entry || entry.stamp !== stamp) {
      const fullPath = join(root, path);
      let text: string;
      try {
        if (realpathSync(fullPath) !== fullPath) throw new Error("file changed during scan");
        text = boundedRead(fullPath, status);
      } catch {
        problems.push({ path, code: "file_unreadable" });
        complete = false;
        continue;
      }
      entry = scanFile(path, stamp, text);
    }
    scanned.set(path, entry);
    if (entry.problem) problems.push({ path, code: entry.problem });
    if (entry.schema) {
      const schema = entry.schema;
      schemas.set(path, schema);
      if (schema.contract) {
        const variants = byContract.get(schema.contract) ?? new Map<string, CollectionSchema>();
        if (!variants.has(schema.digest)) variants.set(schema.digest, schema);
        byContract.set(schema.contract, variants);
      }
    }
    if (entry.record) records.push(entry.record);
  }
  return {
    records: records.map((record) => {
      const prior =
        scanned.get(record.path) === saved.get(record.path)
          ? priorRecords.get(record.path)
          : undefined;
      return bind(
        record,
        scanned.get(record.path)?.recordYaml,
        schemas,
        byContract,
        prior,
        priorDigests.get(prior?.schema ?? ""),
      );
    }),
    schemas: [...schemas.values()],
    problems,
    complete,
    added: [...scanned.keys()].filter((name) => !saved.has(name)),
    changed: [...scanned.keys()].filter(
      (name) => saved.has(name) && scanned.get(name) !== saved.get(name),
    ),
    removed: complete ? [...saved.keys()].filter((name) => !scanned.has(name)) : [],
    snapshot: { version: SNAPSHOT_VERSION, scope, files: [...scanned] },
  };
}

/** Report verdicts and counts without exposing payload or body values. */
export function collectionSummary(scan: CollectionScan): {
  complete: boolean;
  contracts: Record<string, number>;
  states: Record<string, number>;
  schemas: number;
  problems: ScanProblem[];
} {
  const counts = new Map<string, number>();
  const states: Record<string, number> = {};
  const problems = [...scan.problems];
  for (const record of scan.records) {
    states[record.state] = (states[record.state] ?? 0) + 1;
    if (record.metadata) {
      const key = record.metadata.contractId;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    for (const error of record.errors ?? []) {
      const code = "code" in error ? error.code : "kind" in error ? error.kind : "invalid";
      problems.push({ path: record.path, code: String(code) });
    }
  }
  problems.sort((a, b) => byCodePoint(a.path, b.path) || byCodePoint(a.code, b.code));
  return {
    complete: scan.complete,
    contracts: Object.fromEntries(counts),
    states,
    schemas: scan.schemas.length,
    problems,
  };
}
