#!/usr/bin/env node
/**
 * Command-line interface for the TypeScript softschema implementation. Mirrors the
 * Python argparse CLI's behavior, exit codes (0 ok / 1 failure / 2 usage), and output
 * bytes so the shared golden corpus passes against both `softschema-py` and `softschema-ts`.
 */
import { existsSync, readFileSync, realpathSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Command, CommanderError } from "commander";
import {
  type DiscoveryEntry,
  type DiscoveryInputError,
  discoverArtifacts,
} from "./artifact-discovery.js";
import { type BoundedFileExpectation, readBoundedFile } from "./bounded-file.js";
import { compileSchema } from "./compile.js";
import {
  type ArtifactInputResult,
  DEFAULT_VALIDATION_LIMITS,
  type DiagnosticResultV1,
  type DiagnosticV1,
  type DiagnosticValidationWire,
  diagnosticRuleId,
  type JsonObject,
  jsonPointer,
  PortableValueError,
  PortableYamlError,
  projectDiagnosticAggregate,
  projectDiagnosticResult,
  projectDiagnosticSarif,
  projectValidationWire,
  type SourceAnchor,
  SourceMap,
  serializeDiagnosticJsonl,
} from "./core/index.js";
import { structuralErrorOffendingProperty } from "./errors.js";
import { regenerate } from "./generate.js";
import { loadZodModel } from "./model-loader.js";
import {
  type Contract,
  type ContractDescriptor,
  isSchemaStatus,
  metadataToOutput,
  parseSchemaMetadata,
  SchemaMetadataError,
  validateContractId,
  validateSchemaId,
} from "./models.js";
import { isFileSystemError } from "./node-errors.js";
import { bindContract } from "./runtime-contract.js";
import { stableStringify } from "./settings.js";
import {
  installSkillPayload as buildInstallSkillPayload,
  executeSkillInstall,
  formatInstallPlanText,
  SkillInstallUsageError,
} from "./skill-installer.js";
import {
  artifactErrorRecord,
  captureValidatedSchemaSource,
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type RawFrontmatter,
  readFrontmatter,
  readFrontmatterWithLocations,
  readPureYamlArtifactWithLocations,
  resolveMetadataSchema,
  takeValidatedSchemaSource,
  validateArtifact,
  YamlParseError,
} from "./validate.js";
import { parsePortableYamlWithLocations } from "./yaml-value-domain.js";

// The package root holds the bundled `resources/` dir (copied at build, shipped via the
// package `files`). Resolve symlinks so npm/pnpm bins retain the installed package identity.
const MODULE_PATH = realpathSync(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = resolve(dirname(MODULE_PATH), "..");

const BRIEF_MARKER_START = "<!-- BEGIN SOFTSCHEMA BRIEF -->";
const BRIEF_MARKER_END = "<!-- END SOFTSCHEMA BRIEF -->";
const DOCTOR_OPERATIONS = [
  "compile",
  "docs",
  "doctor",
  "generate",
  "inspect",
  "prime",
  "skill",
  "validate",
] as const;
const DOCTOR_OUTPUT_FORMATS = ["json", "jsonl", "sarif", "text"] as const;

const SOURCE_MODULE_PATHS = [
  "packages/typescript/src/cli.ts",
  "packages/typescript/dist/cli.js",
] as const;
const SOURCE_CHECKOUT_MARKERS = [
  "pyproject.toml",
  "packages/python/src/softschema/cli.py",
  "skills/softschema/SKILL.md",
] as const;

/** Return the repo root only when this module has the exact source-tree identity. */
function sourceCheckoutRoot(modulePath: string): string | null {
  const packageRoot = resolve(dirname(modulePath), "..");
  const repoRoot = resolve(packageRoot, "../..");
  const isSourceModule = SOURCE_MODULE_PATHS.some((relativePath) => {
    const expected = join(repoRoot, relativePath);
    return existsSync(expected) && realpathSync(expected) === modulePath;
  });
  if (!isSourceModule) return null;
  if (
    !SOURCE_CHECKOUT_MARKERS.every((marker) => {
      const candidate = join(repoRoot, marker);
      return existsSync(candidate) && statSync(candidate).isFile();
    })
  ) {
    return null;
  }
  return repoRoot;
}

const SOURCE_CHECKOUT_ROOT = sourceCheckoutRoot(MODULE_PATH);

/** Read a reviewed source resource in this checkout, otherwise the installed package bundle. */
function readResource(relPath: string): string {
  if (SOURCE_CHECKOUT_ROOT !== null) {
    const candidate = join(SOURCE_CHECKOUT_ROOT, relPath);
    if (existsSync(candidate)) return readFileSync(candidate, "utf8");
  }
  const bundled = join(PACKAGE_ROOT, "resources", relPath);
  if (existsSync(bundled)) return readFileSync(bundled, "utf8");
  throw new Error(`bundled softschema resource not found: ${relPath}`);
}

export interface DocTopic {
  name: string;
  title: string;
  path: string;
  summary: string;
}

// Sorted by name to match the Python CLI's `sorted(DOC_TOPICS)` output.
// `agents` (AGENTS.md) and `publishing` (release runbook) are intentionally not bundled
// topics: both are repo/maintainer-internal and have no use inside an installed package.
export const DOC_TOPICS: DocTopic[] = [
  {
    name: "agent-compatibility",
    title: "Coding Agent Compatibility",
    path: "docs/agent-compatibility.md",
    summary: "Discovery and instruction paths for major coding agents.",
  },
  {
    name: "api",
    title: "API Reference",
    path: "docs/api.md",
    summary: "Stable library and command-line surfaces.",
  },
  {
    name: "changelog",
    title: "Changelog",
    path: "CHANGELOG.md",
    summary: "Release history and user-visible changes.",
  },
  {
    name: "development",
    title: "Development",
    path: "docs/development.md",
    summary: "Local development workflow.",
  },
  {
    name: "example",
    title: "Movie Page Example",
    path: "examples/movie_page/README.md",
    summary: "Copyable example overview.",
  },
  {
    name: "example-artifact",
    title: "Movie Page Artifact",
    path: "examples/movie_page/spirited-away.md",
    summary: "Copyable Markdown/YAML artifact.",
  },
  {
    name: "example-host",
    title: "Movie Page Host Integration",
    path: "examples/movie_page/host_integration.py",
    summary: "Host registry and validation helper.",
  },
  {
    name: "example-host-ts",
    title: "Movie Page TypeScript Host Integration",
    path: "examples/movie_page/host_integration.ts",
    summary: "TypeScript host registry and validation helper.",
  },
  {
    name: "example-model",
    title: "Movie Page Model",
    path: "examples/movie_page/model.py",
    summary: "Pydantic model used by the example.",
  },
  {
    name: "example-model-ts",
    title: "Movie Page TypeScript Model",
    path: "examples/movie_page/model.ts",
    summary: "Zod model used by the paired example.",
  },
  {
    name: "example-pure-yaml",
    title: "Movie Page Pure YAML Artifact",
    path: "examples/movie_page/spirited-away.yaml",
    summary: "Copyable pure YAML artifact.",
  },
  {
    name: "example-schema",
    title: "Movie Page Compiled Schema",
    path: "examples/movie_page/movie-page.schema.yaml",
    summary: "Compiled JSON Schema for the example.",
  },
  {
    name: "guide",
    title: "softschema Guide",
    path: "docs/softschema-guide.md",
    summary: "Concepts, mental model, and adoption path.",
  },
  {
    name: "installation",
    title: "Installation",
    path: "docs/installation.md",
    summary: "Installing softschema for Node or Python.",
  },
  {
    name: "migration-0.3",
    title: "Migration to 0.3",
    path: "docs/migration-0.3.md",
    summary: "Compatibility and migration guidance for 0.3.",
  },
  {
    name: "python-design",
    title: "Python Package Design",
    path: "docs/softschema-python-design.md",
    summary: "Python package design decisions.",
  },
  { name: "readme", title: "README", path: "README.md", summary: "Short first-visitor overview." },
  {
    name: "security",
    title: "Security Policy",
    path: "SECURITY.md",
    summary: "Supported versions, trust boundaries, and vulnerability reporting.",
  },
  {
    name: "skill",
    title: "softschema Skill",
    path: "skills/softschema/SKILL.md",
    summary: "Portable agent skill instructions.",
  },
  {
    name: "spec",
    title: "softschema Spec",
    path: "docs/softschema-spec.md",
    summary: "Language-neutral artifact format.",
  },
  {
    name: "typescript-design",
    title: "TypeScript Package Design",
    path: "docs/softschema-typescript-design.md",
    summary: "TypeScript package design decisions.",
  },
];

const COPYABLE_EXAMPLES = [
  "example",
  "example-artifact",
  "example-pure-yaml",
  "example-model",
  "example-model-ts",
  "example-host",
  "example-host-ts",
  "example-schema",
];

export const SKILL_INSTALL_TARGETS = [
  ".agents/skills/softschema/SKILL.md",
  ".claude/skills/softschema/SKILL.md",
] as const;

// The format=fNN stamp lets a future installer recognize this managed surface and refuse
// to clobber a newer format. The package version is intentionally omitted so the
// committed mirrors stay deterministic across dev builds (matches the Python marker).
export const SKILL_DO_NOT_EDIT_MARKER =
  "<!-- DO NOT EDIT format=f01: written by `softschema skill --install`.\nRe-run that command to update.\n-->\n";

function packageVersion(): string {
  try {
    const pkg = JSON.parse(readFileSync(join(PACKAGE_ROOT, "package.json"), "utf8")) as {
      version?: string;
    };
    return pkg.version ?? "unknown";
  } catch {
    return "unknown";
  }
}

/** Safely extract a message from an unknown thrown value. */
function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/**
 * Bug-indicator exceptions: a programmer error (calling a non-function, reading a
 * property of undefined, an out-of-range value), never a user mistake. These must
 * surface as a crash with a stack trace, not be masked as a clean exit 2. Mirrors the
 * Python CLI excluding TypeError/KeyError from its user-error boundary.
 */
export function isProgrammerBug(err: unknown): boolean {
  return err instanceof TypeError || err instanceof RangeError || err instanceof ReferenceError;
}

/**
 * The per-command error boundary, mirroring the Python CLI's `_run_cmd`. Rethrows
 * bug-indicator exceptions so a programmer bug thrown anywhere inside a command helper
 * (validateArtifact, compileSchema, regenerate, metadata parsing, ...) crashes instead
 * of being reported as a clean user error; every other (user) error — missing or
 * unreadable file, malformed YAML, bad model spec, `UsageError` — becomes a stable
 * one-line stderr message and exit 2. `prefix` is the command label after `softschema `
 * (e.g. `validate`, or `generate: <path>`), matching each command's existing wording.
 */
export function reportUserError(prefix: string, err: unknown): number {
  if (isProgrammerBug(err)) throw err;
  process.stderr.write(`softschema ${prefix}: ${errMessage(err)}\n`);
  return 2;
}

function renderedSkill(): string {
  return readResource("skills/softschema/SKILL.md");
}

function extractMarkedSection(text: string): string {
  const start = text.indexOf(BRIEF_MARKER_START);
  const end = text.indexOf(BRIEF_MARKER_END);
  if (start === -1 || end === -1 || end <= start) {
    throw new Error("skills/softschema/SKILL.md is missing the brief marker block");
  }
  return text.slice(start + BRIEF_MARKER_START.length, end);
}

function renderedSkillBrief(): string {
  return `# softschema Skill Brief\n\n${extractMarkedSection(renderedSkill()).trim()}\n`;
}

/** Insert the DO NOT EDIT marker after the closing frontmatter delimiter (matches Python). */
export function installSkillPayload(rendered: string): string {
  return buildInstallSkillPayload(rendered, SKILL_DO_NOT_EDIT_MARKER);
}

interface SkillOptions {
  brief?: boolean;
  install?: boolean;
  project?: boolean;
  global?: boolean;
  dir?: string;
  agent?: string[];
  allAgents?: boolean;
  noRepoCheck?: boolean;
  dryRun?: boolean;
  json?: boolean;
  text?: boolean;
}

function collectAgent(value: string, previous: string[]): string[] {
  return [...previous, value];
}

function collectPattern(value: string, previous: string[]): string[] {
  return [...previous, value];
}

function runSkillInstall(opts: SkillOptions): number {
  try {
    if (opts.json === true && opts.text === true) {
      throw new SkillInstallUsageError("--json and --text are mutually exclusive");
    }
    const { code, report } = executeSkillInstall(
      {
        project: opts.project,
        globalScope: opts.global,
        directory: opts.dir,
        agents: opts.agent,
        allAgents: opts.allAgents,
        noRepoCheck: opts.noRepoCheck,
        dryRun: opts.dryRun,
      },
      {
        renderedSkill: renderedSkill(),
        marker: SKILL_DO_NOT_EDIT_MARKER,
        packageVersion: packageVersion(),
        cwd: process.cwd(),
      },
    );
    writeText(opts.text === true ? formatInstallPlanText(report) : stableStringify(report));
    return code;
  } catch (err) {
    return reportUserError("skill", err);
  }
}

function writeText(text: string): void {
  process.stdout.write(text);
  if (!text.endsWith("\n")) process.stdout.write("\n");
}

interface ReleaseMetadata {
  discovery_protocol: string;
  logical_version: string;
  release_state: "development" | "candidate" | "released";
  packages: {
    python: { pin: string };
    npm: { pin: string };
  };
  artifact_formats: { supported: string[] };
  conformance: {
    version: string;
    status: "unavailable" | "candidate" | "release_asset";
  };
}

interface DoctorReport {
  protocol_version: string;
  package: {
    name: "softschema";
    version: string;
    release_state: ReleaseMetadata["release_state"];
  };
  runtime: {
    name: "node" | "bun";
    version: string;
  };
  capabilities: {
    operations: string[];
    artifact_formats: string[];
    model_loaders: string[];
    output_formats: string[];
    conformance: ReleaseMetadata["conformance"];
  };
  build: Record<string, unknown>;
}

function releaseMetadata(): ReleaseMetadata {
  return JSON.parse(readResource("release-metadata.json")) as ReleaseMetadata;
}

function buildMetadata(): Record<string, unknown> {
  return JSON.parse(readResource("build-metadata.json")) as Record<string, unknown>;
}

function doctorReport(): DoctorReport {
  const release = releaseMetadata();
  const bunVersion = process.versions.bun;
  return {
    protocol_version: release.discovery_protocol,
    package: {
      name: "softschema",
      version: release.logical_version,
      release_state: release.release_state,
    },
    runtime: {
      name: bunVersion === undefined ? "node" : "bun",
      version: bunVersion ?? process.versions.node,
    },
    capabilities: {
      operations: [...DOCTOR_OPERATIONS],
      artifact_formats: [...release.artifact_formats.supported].sort(),
      model_loaders: ["json-schema", "zod"],
      output_formats: [...DOCTOR_OUTPUT_FORMATS],
      conformance: release.conformance,
    },
    build: buildMetadata(),
  };
}

function doctorText(report: DoctorReport): string {
  const { capabilities, package: packageInfo, runtime } = report;
  return [
    `softschema discovery protocol: ${report.protocol_version}`,
    `package: ${packageInfo.name} ${packageInfo.version} (${packageInfo.release_state})`,
    `runtime: ${runtime.name} ${runtime.version}`,
    `operations: ${capabilities.operations.join(", ")}`,
    `artifact formats: ${capabilities.artifact_formats.join(", ")}`,
    `model loaders: ${capabilities.model_loaders.join(", ")}`,
    `output formats: ${capabilities.output_formats.join(", ")}`,
    `conformance: ${capabilities.conformance.version} (${capabilities.conformance.status})`,
    `build: ${String(report.build.build_id)}`,
  ].join("\n");
}

function agentHelpEpilog(): string {
  const release = releaseMetadata();
  return `IMPORTANT for agents:
  To set up softschema for this repo as a skill, run one exact-pinned command from the repo root:
    uvx --from 'softschema==${release.packages.python.pin}' softschema skill --install
    # or
    npx --yes softschema@${release.packages.npm.pin} skill --install
    # or
    bunx --bun softschema@${release.packages.npm.pin} skill --install
  Then run \`softschema doctor --json\`, and read \`softschema skill --brief\` and
  \`softschema docs --list\` for capabilities, operating rules, and bundled docs.`;
}

function readFrontmatterRaw(path: string): Record<string, unknown> | null {
  // Reuse the single frontmatter parser from validate.ts so the fence-scanning and
  // empty-frontmatter handling cannot drift between the two entry points. Surface a
  // malformed-YAML failure as a usage error (exit 2) with the message, mirroring the
  // Python CLI's FmFormatError handling, rather than letting it escape as a stack trace.
  try {
    const fm = readFrontmatter(path);
    return fm.hasFence ? (fm.value as Record<string, unknown>) : null;
  } catch (err) {
    if (err instanceof YamlParseError) {
      throw new UsageError(`Error parsing YAML metadata: ${err.message}`);
    }
    throw err;
  }
}

function envelopeKeys(frontmatter: Record<string, unknown>): string[] {
  return Object.keys(frontmatter).filter((k) => k !== "softschema");
}

class UsageError extends Error {}

class BindingUsageError extends UsageError {
  constructor(
    message: string,
    readonly diagnosticCode: string,
    readonly diagnosticMessage: string,
    readonly diagnosticPath: string,
  ) {
    super(message);
  }
}

function inferEnvelope(
  frontmatter: Record<string, unknown>,
  override: string | undefined,
  declared: string | null,
): string | null {
  // Envelope precedence: --envelope flag > document softschema.envelope > inference.
  if (override !== undefined) return override;
  if (declared !== null) return declared;
  try {
    return inferEnvelopeKey(frontmatter);
  } catch (err) {
    if (err instanceof EnvelopeAmbiguityError) {
      throw new BindingUsageError(
        `multiple top-level frontmatter keys; pass --envelope to designate the softschema payload (candidates: ${err.candidates.join(", ")})`,
        "envelope_ambiguous",
        "artifact payload envelope is ambiguous",
        "",
      );
    }
    throw err;
  }
}

interface ValidateOptions {
  contract?: string;
  exclude?: string[];
  envelope?: string;
  format?: string;
  include?: string[];
  model?: string;
  profile?: string;
  recursive?: boolean;
  schema?: string;
  status?: string;
}

function parseSchemaProfile(value: string): Contract["profile"] {
  if (value === "frontmatter-md" || value === "pure-yaml") return value;
  throw new UsageError(`invalid profile: ${value}`);
}

type ValidateOutputFormat = "json" | "jsonl" | "sarif";

function parseValidateOutputFormat(value: string | undefined): ValidateOutputFormat {
  if (value === undefined || value === "json") return "json";
  if (value === "jsonl" || value === "sarif") return value;
  throw new UsageError(`invalid format: ${value}`);
}

interface ValidationBinding {
  contractId: string;
  status: Contract["status"];
  envelopeKey: string | null;
}

function inferValidationBinding(
  frontmatter: Record<string, unknown> | null,
  opts: ValidateOptions,
  profile: Contract["profile"],
): ValidationBinding {
  if (profile === "frontmatter-md" && frontmatter === null && opts.contract === undefined) {
    throw new BindingUsageError(
      "missing --contract because the document has no YAML frontmatter",
      "contract_unknown",
      "artifact contract is not registered",
      "/softschema/contract",
    );
  }
  const fm = frontmatter ?? {};
  const metadata = parseSchemaMetadata(fm.softschema ?? null);
  const contractId = opts.contract ?? metadata?.contractId;
  if (contractId === undefined) {
    throw new BindingUsageError(
      "missing --contract because the document has no softschema.contract",
      "contract_unknown",
      "artifact contract is not registered",
      "/softschema/contract",
    );
  }
  validateContractId(contractId);
  let status: Contract["status"] = "soft";
  if (opts.status !== undefined) {
    if (!isSchemaStatus(opts.status)) throw new UsageError(`invalid status: ${opts.status}`);
    status = opts.status;
  } else if (metadata?.status) {
    status = metadata.status;
  }
  const envelopeKey =
    profile === "pure-yaml"
      ? (opts.envelope ?? metadata?.envelope ?? null)
      : inferEnvelope(fm, opts.envelope, metadata?.envelope ?? null);
  return { contractId, status, envelopeKey };
}

interface PreparedBatchArtifact {
  readonly kind: "prepared";
  readonly path: string;
  readonly source: string;
  readonly root: Record<string, unknown> | null;
  readonly sourceMap: SourceMap;
  readonly sourceFile: BoundedFileExpectation;
  readonly binding: ValidationBinding;
}

interface SchemaDiagnosticSource {
  readonly source: string;
  readonly sourceMap: SourceMap;
}

interface CachedSchemaSource {
  readonly expectation: BoundedFileExpectation;
  readonly sourceMap: SourceMap;
}

function isPreparedBatchArtifact(
  item: PreparedBatchArtifact | DiagnosticResultV1,
): item is PreparedBatchArtifact {
  return "kind" in item && item.kind === "prepared";
}

async function runValidate(paths: string[], opts: ValidateOptions): Promise<number> {
  try {
    // Without --model/--schema this is a metadata-only check: frontmatter parses,
    // the softschema: block is well-formed, and the envelope resolves; structural
    // and semantic layers are reported as skipped. Useful from the `soft` stage on.
    const profile = parseSchemaProfile(opts.profile ?? "frontmatter-md");
    const outputFormat = parseValidateOutputFormat(opts.format);
    if (opts.contract !== undefined) validateContractId(opts.contract);
    if (opts.status !== undefined && !isSchemaStatus(opts.status)) {
      throw new UsageError(`invalid status: ${opts.status}`);
    }
    const discovery = discoverArtifacts({
      operands: paths,
      recursive: opts.recursive === true,
      profile,
      includes: opts.include ?? [],
      excludes: opts.exclude ?? [],
      invocationDirectory: process.cwd(),
      pathFlavor: process.platform === "win32" ? "windows" : "posix",
    });
    const explicitDirectory = paths.length === 1 && isDirectoryOperand(paths[0] as string);
    if (isLegacyValidateRequest(paths, discovery.entries, outputFormat, explicitDirectory)) {
      return await runValidateLegacy(paths[0] as string, opts, profile);
    }
    return await runValidateDiagnostic(discovery.entries, opts, profile, outputFormat);
  } catch (err) {
    // Exit 1 is reserved for a readable artifact that fails validation (the result path
    // above). A bug-indicator exception crashes; every other (user) error — missing or
    // unreadable file, malformed YAML, bad model spec — is a clean one-line stderr
    // message + exit 2 (see reportUserError). Never an uncaught stack trace for a user
    // mistake, never a masked exit 2 for a programmer bug.
    return reportUserError("validate", err);
  }
}

function isLegacyValidateRequest(
  paths: readonly string[],
  entries: readonly DiscoveryEntry[],
  outputFormat: ValidateOutputFormat,
  explicitDirectory: boolean,
): boolean {
  if (paths.length !== 1 || explicitDirectory || outputFormat !== "json" || entries.length !== 1) {
    return false;
  }
  const entry = entries[0] as DiscoveryEntry;
  return entry.kind === "artifact" || entry.reason === "not_found";
}

function isDirectoryOperand(path: string): boolean {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

async function runValidateLegacy(
  path: string,
  opts: ValidateOptions,
  profile: Contract["profile"],
): Promise<number> {
  // Read the document once here; both binding inference and validateArtifact reuse
  // this normalized root. Readable parse failures are validation results (exit 1),
  // while access failures remain exit 2.
  let parsed: RawFrontmatter | undefined;
  let pureYaml: Record<string, unknown> | undefined;
  let sourceFile: BoundedFileExpectation;
  try {
    if (profile === "pure-yaml") {
      const located = readPureYamlArtifactWithLocations(path);
      pureYaml = located.value;
      sourceFile = located.sourceFile;
    } else {
      const located = readFrontmatterWithLocations(path);
      parsed = { hasFence: located.hasFence, value: located.value };
      sourceFile = located.sourceFile;
    }
  } catch (err) {
    const record = artifactErrorRecord(path, err);
    if (record !== null) {
      writeText(stableStringify(record));
      return record.kind === "input_error" ? 2 : 1;
    }
    throw err;
  }
  const frontmatter =
    profile === "pure-yaml"
      ? (pureYaml as Record<string, unknown>)
      : (parsed as RawFrontmatter).hasFence
        ? ((parsed as RawFrontmatter).value as Record<string, unknown>)
        : null;
  const binding = inferValidationBinding(frontmatter, opts, profile);
  const semanticModel = opts.model !== undefined ? await loadZodModel(opts.model) : undefined;
  const descriptor: ContractDescriptor = {
    id: binding.contractId,
    model: opts.model ?? null,
    envelopeKey: binding.envelopeKey,
    status: binding.status,
    profile,
    schemaPath: opts.schema ?? null,
  };
  const contract = bindContract(descriptor, semanticModel ?? null);
  const result = validateArtifact(path, contract, {
    preParsed: parsed,
    preParsedYaml: pureYaml,
    preParsedSource: sourceFile,
  });
  writeText(stableStringify(result.output));
  return result.ok ? 0 : 1;
}

async function runValidateDiagnostic(
  entries: readonly DiscoveryEntry[],
  opts: ValidateOptions,
  profile: Contract["profile"],
  outputFormat: ValidateOutputFormat,
): Promise<number> {
  const prepared: (PreparedBatchArtifact | DiagnosticResultV1)[] = [];
  for (const entry of entries) {
    if (entry.kind === "input_error") {
      prepared.push(inputDiagnosticResult(entry));
      continue;
    }
    let root: Record<string, unknown> | null;
    let sourceMap: SourceMap;
    let sourceFile: BoundedFileExpectation;
    try {
      if (profile === "pure-yaml") {
        const located = readPureYamlArtifactWithLocations(entry.path);
        root = located.value;
        sourceMap = located.sourceMap;
        sourceFile = located.sourceFile;
      } else {
        const located = readFrontmatterWithLocations(entry.path);
        root = located.hasFence ? (located.value as Record<string, unknown>) : null;
        sourceMap = located.sourceMap;
        sourceFile = located.sourceFile;
      }
    } catch (error) {
      const record = artifactErrorRecord(entry.displayPath, error, { includeLocation: true });
      if (record === null) throw error;
      prepared.push(artifactErrorDiagnosticResult(record));
      continue;
    }
    let binding: ValidationBinding;
    try {
      binding = inferValidationBinding(root, opts, profile);
    } catch (error) {
      if (
        !(error instanceof UsageError) &&
        !(error instanceof SchemaMetadataError) &&
        !(error instanceof EnvelopeAmbiguityError)
      ) {
        throw error;
      }
      prepared.push(bindingDiagnosticResult(entry.displayPath, profile, root, sourceMap, error));
      continue;
    }
    prepared.push({
      kind: "prepared",
      path: entry.path,
      source: entry.displayPath,
      root,
      sourceMap,
      sourceFile,
      binding,
    });
  }

  const hasPrepared = prepared.some(isPreparedBatchArtifact);
  const semanticModel =
    opts.model !== undefined && hasPrepared ? await loadZodModel(opts.model) : null;
  const results: DiagnosticResultV1[] = [];
  const schemaMaps = new Map<string, CachedSchemaSource>();
  for (const item of prepared) {
    if (!isPreparedBatchArtifact(item)) {
      results.push(item);
      continue;
    }
    const descriptor: ContractDescriptor = {
      id: item.binding.contractId,
      model: opts.model ?? null,
      envelopeKey: item.binding.envelopeKey,
      status: item.binding.status,
      profile,
      schemaPath: opts.schema ?? null,
    };
    const contract = bindContract(descriptor, semanticModel);
    const validationResult = captureValidatedSchemaSource(() =>
      validateArtifact(item.path, contract, {
        ...(profile === "pure-yaml"
          ? { preParsedYaml: item.root }
          : { preParsed: { hasFence: item.root !== null, value: item.root } }),
        validationLimits: DEFAULT_VALIDATION_LIMITS,
        preParsedSource: item.sourceFile,
      }),
    );
    const validatedSchemaSource = takeValidatedSchemaSource(validationResult.output.structural);
    const input = artifactInputSuccess(item.source, profile, item.root);
    const structuralOffendingProperties = validationResult.output.structural.errors.map((error) =>
      structuralErrorOffendingProperty(error),
    );
    const validation = projectValidationWire(validationResult.output);
    const schemaSource = validation.structural.errors.some(
      (error) => error.kind === "schema_invalid",
    )
      ? schemaDiagnosticSource(
          item.path,
          opts.schema,
          validation,
          schemaMaps,
          item.sourceFile,
          validatedSchemaSource,
        )
      : null;
    const diagnostics = validationDiagnostics(
      validation,
      item.source,
      item.sourceMap,
      item.binding.envelopeKey,
      schemaSource,
      structuralOffendingProperties,
    );
    results.push(projectDiagnosticResult(input, validation, diagnostics));
  }

  const aggregate = projectDiagnosticAggregate(profile, DEFAULT_VALIDATION_LIMITS, results);
  if (outputFormat === "jsonl") writeText(serializeDiagnosticJsonl(aggregate));
  else if (outputFormat === "sarif") writeText(stableStringify(projectDiagnosticSarif(aggregate)));
  else writeText(stableStringify(aggregate));
  return aggregate.summary.exit_code;
}

function artifactInputSuccess(
  source: string,
  profile: Contract["profile"],
  root: Record<string, unknown> | null,
): ArtifactInputResult {
  const values = Object.fromEntries(
    Object.entries(root ?? {}).filter(([key]) => key !== "softschema"),
  ) as JsonObject;
  return { kind: "artifact_input", ok: true, source, profile, values };
}

function inputDiagnosticResult(entry: DiscoveryInputError): DiagnosticResultV1 {
  const input: ArtifactInputResult = {
    kind: "input_error",
    reason: entry.reason,
    message: entry.message,
    source: entry.source,
  };
  return projectDiagnosticResult(input, null, [
    {
      category: "input",
      rule_id: diagnosticRuleId("input_error", entry.reason),
      severity: "error",
      message: entry.message,
      source: entry.source,
    },
  ]);
}

function artifactErrorDiagnosticResult(input: ArtifactInputResult): DiagnosticResultV1 {
  if (input.kind === "artifact_input") throw new Error("expected a failed artifact input");
  const category = input.kind === "input_error" ? "input" : "parse";
  const family = input.kind === "input_error" ? "input_error" : "parse_error";
  const diagnostic: DiagnosticV1 = {
    category,
    rule_id: diagnosticRuleId(family, input.reason),
    severity: "error",
    message: input.message,
    source: input.source,
  };
  if (input.kind === "parse_error") {
    if (input.path !== undefined) diagnostic.path = input.path;
    if (input.line !== undefined) diagnostic.line = input.line;
    if (input.column !== undefined) diagnostic.column = input.column;
  }
  return projectDiagnosticResult(input, null, [diagnostic]);
}

function bindingDiagnosticResult(
  source: string,
  profile: Contract["profile"],
  root: Record<string, unknown> | null,
  sourceMap: SourceMap,
  error: Error,
): DiagnosticResultV1 {
  let code: string;
  let message: string;
  let path: string;
  if (error instanceof BindingUsageError) {
    code = error.diagnosticCode;
    message = error.diagnosticMessage;
    path = error.diagnosticPath;
  } else {
    code = "metadata_invalid";
    message = "artifact softschema metadata is invalid";
    path = "/softschema";
  }
  const diagnostic: DiagnosticV1 = {
    category: "binding",
    rule_id: diagnosticRuleId("artifact", code),
    severity: "error",
    message,
    source,
    path,
  };
  addSourceLocation(diagnostic, sourceMap, path);
  return projectDiagnosticResult(artifactInputSuccess(source, profile, root), null, [diagnostic]);
}

const ARTIFACT_DIAGNOSTIC_MESSAGES: Readonly<Record<string, string>> = {
  contract_unknown: "artifact contract is not registered",
  no_frontmatter: "artifact has no frontmatter",
  frontmatter_not_mapping: "artifact frontmatter must be a mapping",
  metadata_invalid: "artifact softschema metadata is invalid",
  document_softschema_invalid: "artifact softschema metadata is invalid",
  document_contract_mismatch: "artifact contract does not match the selected contract",
  envelope_mismatch: "artifact payload envelope does not match the selected contract",
  envelope_ambiguous: "artifact payload envelope is ambiguous",
  envelope_missing: "artifact payload envelope is missing",
  envelope_not_mapping: "artifact payload envelope must be a mapping",
  values_not_mapping: "artifact payload must be a mapping",
  schema_missing: "compiled schema is unavailable",
};

function validationDiagnostics(
  validation: DiagnosticValidationWire,
  source: string,
  sourceMap: SourceMap,
  envelopeKey: string | null,
  schemaSource: SchemaDiagnosticSource | null,
  structuralOffendingProperties: readonly (string | undefined)[],
): DiagnosticV1[] {
  const diagnostics: DiagnosticV1[] = [];
  for (const [errorIndex, rawError] of validation.structural.errors.entries()) {
    const error = rawError as unknown as Record<string, unknown>;
    const kind = typeof error.kind === "string" ? error.kind : "artifact";
    if (kind === "schema_invalid") {
      const reason = typeof error.reason === "string" ? error.reason : "compile";
      const diagnostic: DiagnosticV1 = {
        category: "schema",
        rule_id: diagnosticRuleId("schema_invalid", reason),
        severity: "error",
        message: String(error.message),
        source,
      };
      const schemaDisplay = schemaSource?.source ?? validationSchemaSource(validation);
      if (schemaDisplay !== null) diagnostic.schema_source = schemaDisplay;
      if (typeof error.schema_path === "string") {
        diagnostic.schema_path = error.schema_path;
        if (schemaSource !== null) {
          addSourceLocation(diagnostic, schemaSource.sourceMap, error.schema_path);
        }
      }
      diagnostics.push(diagnostic);
      continue;
    }
    if (kind === "schema_violation") {
      const validator = typeof error.validator === "string" ? error.validator : "validation";
      const objectPath = payloadPointer(error.path, envelopeKey);
      const isExtraProperty =
        validator === "additionalProperties" || validator === "unevaluatedProperties";
      const offendingProperty = isExtraProperty
        ? structuralOffendingProperties[errorIndex]
        : undefined;
      const errorPath = Array.isArray(error.path) ? error.path : [];
      const path =
        offendingProperty === undefined
          ? objectPath
          : payloadPointer([...errorPath, offendingProperty], envelopeKey);
      const diagnostic: DiagnosticV1 = {
        category: "structural",
        rule_id: diagnosticRuleId("schema_violation", validator),
        severity: "error",
        message: String(error.message),
        source,
        path,
      };
      addSourceLocation(
        diagnostic,
        sourceMap,
        path,
        offendingProperty === undefined ? "value" : "key",
      );
      diagnostics.push(diagnostic);
      continue;
    }
    const path = artifactDiagnosticPointer(kind, error, envelopeKey, validation);
    const diagnostic: DiagnosticV1 = {
      category: "structural",
      rule_id: diagnosticRuleId("artifact", kind),
      severity: "error",
      message: ARTIFACT_DIAGNOSTIC_MESSAGES[kind] ?? String(error.message),
      source,
      path,
    };
    addSourceLocation(diagnostic, sourceMap, path);
    diagnostics.push(diagnostic);
  }

  for (const error of validation.semantic.errors) {
    const path = payloadPointer(error.path, envelopeKey);
    const diagnostic: DiagnosticV1 = {
      category: "semantic",
      rule_id: diagnosticRuleId("semantic", error.code),
      severity: "error",
      message: error.message,
      source,
      path,
    };
    addSourceLocation(diagnostic, sourceMap, path);
    diagnostics.push(diagnostic);
  }

  for (const warning of validation.warnings) {
    const path =
      warning.code === "document-contract-mismatch"
        ? "/softschema/contract"
        : warning.code === "document-status-mismatch"
          ? "/softschema/status"
          : "/softschema";
    const diagnostic: DiagnosticV1 = {
      category: "warning",
      rule_id: diagnosticRuleId("warning", warning.code),
      severity: warning.severity,
      message: warning.message,
      source,
      path,
    };
    addSourceLocation(diagnostic, sourceMap, path);
    diagnostics.push(diagnostic);
  }
  return diagnostics;
}

function schemaDiagnosticSource(
  artifactPath: string,
  explicitSchema: string | undefined,
  validation: DiagnosticValidationWire,
  cache: Map<string, CachedSchemaSource>,
  sourceFile: BoundedFileExpectation,
  validatedSource?: { readonly path: string; readonly sourceMap: SourceMap },
): SchemaDiagnosticSource | null {
  if (validatedSource !== undefined) {
    return {
      source: displayPath(validatedSource.path),
      sourceMap: validatedSource.sourceMap,
    };
  }
  const selected = explicitSchema ?? validation.document_metadata?.schema ?? undefined;
  if (selected === undefined) return null;
  let expected: BoundedFileExpectation | undefined;
  let schemaPath: string | undefined;
  if (explicitSchema === undefined) {
    const bound = resolveMetadataSchema(selected, artifactPath, sourceFile);
    if (bound.path === null) return null;
    schemaPath = bound.path;
    expected = bound.expectation;
  } else {
    const candidates = [resolve(selected), resolve(dirname(artifactPath), selected)];
    for (const candidate of candidates) {
      try {
        if (statSync(candidate).isFile()) {
          schemaPath = realpathSync(candidate);
          break;
        }
      } catch (error) {
        if (!isFileSystemError(error)) throw error;
      }
    }
  }
  if (schemaPath === undefined) return null;

  let sourceMap: SourceMap;
  let encoded: Uint8Array;
  let actualExpectation: BoundedFileExpectation;
  try {
    const source = readBoundedFile(
      schemaPath,
      DEFAULT_VALIDATION_LIMITS.maxResourceBytes,
      expected,
    );
    encoded = source.data;
    actualExpectation = source.expectation;
  } catch (error) {
    if (!(error instanceof PortableValueError) && !isFileSystemError(error)) throw error;
    return { source: displayPath(schemaPath), sourceMap: SourceMap.empty() };
  }
  const cached = cache.get(schemaPath);
  if (
    cached !== undefined &&
    cached.expectation.canonicalPath === actualExpectation.canonicalPath &&
    cached.expectation.device === actualExpectation.device &&
    cached.expectation.inode === actualExpectation.inode &&
    cached.expectation.size === actualExpectation.size &&
    cached.expectation.modifiedNs === actualExpectation.modifiedNs &&
    cached.expectation.changedNs === actualExpectation.changedNs
  ) {
    sourceMap = cached.sourceMap;
  } else {
    let text: string;
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(encoded);
    } catch {
      return { source: displayPath(schemaPath), sourceMap: SourceMap.empty() };
    }
    try {
      sourceMap = parsePortableYamlWithLocations(
        text,
        {},
        { encodedSize: encoded.byteLength },
      ).sourceMap;
    } catch (error) {
      if (!(error instanceof PortableValueError) && !(error instanceof PortableYamlError)) {
        throw error;
      }
      sourceMap = SourceMap.empty();
    }
    cache.set(schemaPath, { expectation: actualExpectation, sourceMap });
  }
  return { source: displayPath(schemaPath), sourceMap };
}

function displayPath(path: string): string {
  const fromCwd = relative(process.cwd(), path);
  const contained =
    fromCwd !== ".." && !fromCwd.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`);
  return (contained ? fromCwd : path).replaceAll("\\", "/");
}

function validationSchemaSource(validation: DiagnosticValidationWire): string | null {
  const selected = validation.contract?.schema_path ?? validation.document_metadata?.schema;
  return selected?.replaceAll("\\", "/") ?? null;
}

function payloadPointer(path: unknown, envelopeKey: string | null): string {
  const parts: (string | number)[] = envelopeKey === null ? [] : [envelopeKey];
  if (Array.isArray(path)) {
    for (const part of path) {
      if (typeof part === "string" || typeof part === "number") parts.push(part);
    }
  }
  return jsonPointer(parts);
}

function artifactDiagnosticPointer(
  kind: string,
  error: Readonly<Record<string, unknown>>,
  envelopeKey: string | null,
  validation: DiagnosticValidationWire,
): string {
  if (kind === "metadata_invalid" || kind === "document_softschema_invalid") {
    return "/softschema";
  }
  if (kind === "document_contract_mismatch") return "/softschema/contract";
  if (kind === "schema_missing") {
    return validation.document_metadata?.schema !== null &&
      validation.document_metadata?.schema !== undefined
      ? "/softschema/schema"
      : "";
  }
  if (kind === "envelope_not_mapping" || kind === "values_not_mapping") {
    return envelopeKey === null ? "" : jsonPointer([envelopeKey]);
  }
  if (kind === "envelope_mismatch" && typeof error.expected_key === "string") return "";
  return "";
}

function addSourceLocation(
  diagnostic: DiagnosticV1,
  sourceMap: SourceMap,
  path: string,
  anchor: SourceAnchor = "value",
): void {
  const span = sourceMap.span(path, { anchor });
  if (span !== undefined) {
    diagnostic.line = span.start.line;
    diagnostic.column = span.start.column;
  }
}

function runInspect(path: string): number {
  try {
    const frontmatter = readFrontmatterRaw(path);
    const metadata = frontmatter ? parseSchemaMetadata(frontmatter.softschema ?? null) : null;
    const output = {
      envelope_keys: frontmatter ? envelopeKeys(frontmatter) : [],
      has_frontmatter: frontmatter !== null,
      metadata: metadataToOutput(metadata),
      path,
    };
    writeText(stableStringify(output));
    return 0;
  } catch (err) {
    // Missing/unreadable file, malformed YAML, or a malformed softschema block are user
    // errors (exit 2); a bug-indicator exception crashes. See reportUserError.
    return reportUserError("inspect", err);
  }
}

async function runCompile(
  spec: string,
  opts: { contract?: string; schemaId?: string; out: string; check?: boolean },
): Promise<number> {
  try {
    const contractId = opts.contract;
    if (contractId === undefined) throw new UsageError("compilation requires --contract");
    validateContractId(contractId);
    if (opts.schemaId !== undefined) validateSchemaId(opts.schemaId);
    const schema = await loadZodModel(spec);
    const result = compileSchema(schema, opts.out, {
      contractId,
      schemaId: opts.schemaId ?? null,
      checkOnly: opts.check,
    });
    writeText(
      stableStringify({
        drift: result.drift,
        drift_diff: result.driftDiff,
        out_path: result.outPath,
        schema_sha256: result.schemaSha256,
        schema_yaml: result.schemaYaml,
      }),
    );
    return result.drift ? 1 : 0;
  } catch (err) {
    return reportUserError("compile", err);
  }
}

function runGenerate(paths: string[], opts: { check?: boolean }): number {
  let anyDrift = false;
  const files: Record<string, unknown>[] = [];
  for (const path of paths) {
    let result: ReturnType<typeof regenerate>;
    try {
      result = regenerate(path, { check: opts.check });
    } catch (err) {
      // Exit 1 is reserved for drift; a bug-indicator exception crashes. Other runtime
      // errors (missing file, bad marker) are usage failures: exit 2, keeping the path
      // in the message to match the Python CLI. See reportUserError.
      return reportUserError(`generate: ${path}`, err);
    }
    anyDrift = anyDrift || result.drift;
    files.push({
      path,
      sections: result.sections,
      drift: result.drift,
      drift_details: result.driftDetails,
    });
  }
  writeText(stableStringify({ check: Boolean(opts.check), drift: anyDrift, files }));
  return opts.check && anyDrift ? 1 : 0;
}

function docsListText(): string {
  const width = Math.max(...DOC_TOPICS.map((t) => t.name.length));
  const lines = ["Available softschema docs:", ""];
  for (const t of DOC_TOPICS) {
    lines.push(`  ${t.name.padEnd(width)}  ${t.summary}`);
  }
  lines.push(
    "",
    "Run `softschema docs <topic>` to print a document.",
    "Copy examples from the printed docs or from the repository files; the CLI does not scaffold or mutate projects.",
  );
  return lines.join("\n");
}

function runDocsList(): number {
  writeText(docsListText());
  return 0;
}

// Full agent context for a fresh session: the skill operating rules plus the bundled docs
// index. Byte-identical to the Python `prime` command (same SKILL.md, same docs listing).
function primeText(): string {
  return `${renderedSkill().trimEnd()}\n\n${docsListText()}`;
}

function runPrime(): number {
  writeText(primeText());
  return 0;
}

function runDocsListJson(): number {
  writeText(
    stableStringify({
      topics: DOC_TOPICS.map((t) => ({
        name: t.name,
        title: t.title,
        path: t.path,
        summary: t.summary,
      })),
      copyable_examples: COPYABLE_EXAMPLES,
      scaffolding: false,
    }),
  );
  return 0;
}

function runDocsTopic(topic: string, asJson: boolean): number {
  const found = DOC_TOPICS.find((t) => t.name === topic);
  if (found === undefined) {
    process.stderr.write(`softschema docs: unknown topic ${JSON.stringify(topic)}\n`);
    return 2;
  }
  let content: string;
  try {
    content = readResource(found.path);
  } catch (err) {
    // Surface the original failure (e.g. "bundled ... resource not found", a permission
    // error) rather than a generic one; matches the Python CLI's `softschema docs: <exc>`.
    // A bug-indicator exception crashes instead (see reportUserError).
    return reportUserError("docs", err);
  }
  if (asJson) {
    writeText(
      stableStringify({
        name: found.name,
        title: found.title,
        path: found.path,
        summary: found.summary,
        content,
      }),
    );
  } else {
    writeText(content);
  }
  return 0;
}

export async function main(argv: string[] = process.argv): Promise<number> {
  const program = new Command();
  program
    .name("softschema")
    .description("Validate and explain soft schema Markdown/YAML artifacts.")
    .version(`softschema ${packageVersion()}`, "--version")
    .addHelpText("afterAll", `\n${agentHelpEpilog()}`)
    .exitOverride();
  let exitCode = 0;

  program
    .command("compile")
    .description("Compile a Zod schema")
    .argument("<model>", "trusted Zod module as path:export (.js/.mjs in Node; .ts is Bun-only)")
    .requiredOption("--out <path>", "output path for the compiled schema")
    .option("--contract <id>", "required logical contract ID stored in x-softschema.contract")
    .option(
      "--schema-id <uri>",
      "canonical absolute HTTPS or URN identifier stored in JSON Schema $id",
    )
    .option("--check", "do not write; exit 1 on drift")
    .action(
      async (
        model: string,
        opts: { out: string; contract?: string; schemaId?: string; check?: boolean },
      ) => {
        exitCode = await runCompile(model, opts);
      },
    );

  program
    .command("validate")
    .description(
      "Validate an artifact. A self-describing artifact (softschema.contract, " +
        "schema, envelope) needs no flags; flags override the document",
    )
    .argument("<paths...>")
    .option(
      "--profile <PROFILE>",
      "Artifact storage profile: frontmatter-md or pure-yaml (default: frontmatter-md).",
    )
    .option("--contract <id>", "override the document contract ID")
    .option(
      "--envelope <key>",
      "override the envelope key (softschema.envelope or single-key inference)",
    )
    .option(
      "--model <spec>",
      "Zod schema as path:export for semantic validation. Node loads built .js/.mjs; " +
        "direct .ts is Bun-only. Imports and runs local code; use only trusted models",
    )
    .option(
      "--schema <path>",
      "compiled JSON Schema (YAML or JSON). Optional override; without it the " +
        "document's softschema.schema binding is used when present",
    )
    .option("--status <status>", "override the document status")
    .option("--recursive", "discover profile-matching artifacts below directory operands")
    .option(
      "--include <glob>",
      "include a recursive operand-relative glob; repeat for multiple patterns",
      collectPattern,
      [],
    )
    .option(
      "--exclude <glob>",
      "exclude a recursive operand-relative glob; repeat for multiple patterns",
      collectPattern,
      [],
    )
    .option("--format <format>", "output format: json, jsonl, or sarif (default: json)")
    .action(async (paths: string[], opts: ValidateOptions) => {
      exitCode = await runValidate(paths, opts);
    });

  program
    .command("inspect")
    .description("Inspect artifact metadata")
    .argument("<path>")
    .action((path: string) => {
      exitCode = runInspect(path);
    });

  program
    .command("docs")
    .description("Print bundled docs and examples")
    .argument("[topic]", "topic to print")
    .option("--list", "list bundled documentation topics")
    .option("--json", "emit topic metadata (and content when a topic is selected) as JSON")
    .action((topic: string | undefined, opts: { list?: boolean; json?: boolean }) => {
      if (opts.list || topic === undefined) {
        exitCode = opts.json ? runDocsListJson() : runDocsList();
      } else {
        exitCode = runDocsTopic(topic, Boolean(opts.json));
      }
    });

  program
    .command("generate")
    .description("Regenerate softschema:generated sections")
    .argument("<paths...>")
    .option("--check", "do not write; exit 1 if any section is stale")
    .action((paths: string[], opts: { check?: boolean }) => {
      exitCode = runGenerate(paths, opts);
    });

  program
    .command("prime")
    .description("Print the full agent context: skill rules and the bundled docs index")
    .action(() => {
      exitCode = runPrime();
    });

  program
    .command("doctor")
    .description("Report the versioned discovery protocol and runtime capabilities")
    .option("--json", "emit the environment report as JSON")
    .action((opts: { json?: boolean }) => {
      const report = doctorReport();
      writeText(opts.json ? stableStringify(report) : doctorText(report));
      exitCode = 0;
    });

  program
    .command("skill")
    .description("Print or install the agent skill")
    .option("--brief", "print compact skill guidance")
    .option("--install", "install the bundled skill after scope and ownership preflight")
    .option("--project", "install into a project target (explicitly permits --dir)")
    .option("--global", "install into selected agents' personal skill roots")
    .option("--dir <path>", "project directory to resolve; requires explicit --project")
    .option(
      "--agent <name>",
      "install only the named agent target; repeat for multiple agents",
      collectAgent,
      [],
    )
    .option("--all-agents", "install all nine supported agent targets")
    .option("--no-repo-check", "permit an explicit project destination outside Git")
    .option("--dry-run", "print the complete plan without creating a filesystem entry")
    .option("--json", "emit the install plan as JSON (the compatibility default)")
    .option("--text", "emit the install plan as stable human-readable text")
    .action((opts: SkillOptions) => {
      if (opts.install) {
        exitCode = runSkillInstall(opts);
      } else if (
        opts.project === true ||
        opts.global === true ||
        opts.dir !== undefined ||
        (opts.agent?.length ?? 0) > 0 ||
        opts.allAgents === true ||
        opts.noRepoCheck === true ||
        opts.dryRun === true ||
        opts.json === true ||
        opts.text === true
      ) {
        exitCode = reportUserError(
          "skill",
          new SkillInstallUsageError("installer options require --install"),
        );
      } else if (opts.brief) {
        writeText(renderedSkillBrief());
        exitCode = 0;
      } else {
        writeText(renderedSkill());
        exitCode = 0;
      }
    });

  try {
    await program.parseAsync(argv);
  } catch (err) {
    if (err instanceof CommanderError) {
      // --help and --version throw when exitOverride is active; honour the exit code
      // Commander intended (0 for help/version, non-zero for usage errors).
      return err.exitCode === 0 ? 0 : 2;
    }
    // Surface programmer bugs as a crash instead of masking them as a clean exit 2 (a
    // backstop; each command's catch already rethrows these via reportUserError).
    if (isProgrammerBug(err)) {
      throw err;
    }
    // Top-level backstop (mirrors the Python CLI's per-command error boundary): no
    // command handler should leak a stack trace from a user mistake. Report a clean
    // one-line message and exit 2 for any otherwise-unhandled (user) error.
    process.stderr.write(`softschema: ${errMessage(err)}\n`);
    return 2;
  }
  return exitCode;
}

// True only when this module is the process entrypoint (`softschema ...` or
// `node dist/cli.js`), never when imported as a library via the `./cli` subpath.
// `import.meta.main` does not exist in Node ESM (the bundler lowers it to an
// always-true CommonJS check), so we compare URLs instead. npm/npx install the bin
// as a symlink, so argv[1] is resolved through `realpathSync` to match the module's
// real URL. `realpathSync` throws if argv[1] is not a real path (e.g. a `node -e`
// snippet's trailing args), in which case this module is not the entrypoint.
function isMainModule(): boolean {
  const entry = process.argv[1];
  if (entry === undefined) return false;
  try {
    return pathToFileURL(realpathSync(entry)).href === import.meta.url;
  } catch {
    return false;
  }
}

if (isMainModule()) {
  // EPIPE on stdout/stderr: silently exit 0 (expected when piped to head, etc.).
  for (const stream of [process.stdout, process.stderr]) {
    stream.on("error", (err: NodeJS.ErrnoException) => {
      if (err.code === "EPIPE") {
        process.exitCode = 0;
        process.exit(0);
      }
    });
  }
  // SIGINT: exit 128 + 2 = 130 (standard POSIX convention).
  process.on("SIGINT", () => {
    process.exit(130);
  });

  main().then((code) => {
    process.exitCode = code;
  });
}
