#!/usr/bin/env node
/**
 * Command-line interface for the TypeScript softschema implementation. Mirrors the
 * Python argparse CLI's behavior, exit codes (0 ok / 1 failure / 2 usage), and output
 * bytes so the shared golden corpus passes against both `softschema-py` and `softschema-ts`.
 */
import { existsSync, readFileSync, realpathSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Command, CommanderError } from "commander";
import { compileSchema } from "./compile.js";
import { regenerate } from "./generate.js";
import { loadZodModel } from "./model-loader.js";
import {
  type Contract,
  type ContractDescriptor,
  isSchemaStatus,
  metadataToOutput,
  parseSchemaMetadata,
  validateContractId,
  validateSchemaId,
} from "./models.js";
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
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type RawFrontmatter,
  readFrontmatter,
  readPureYamlArtifact,
  validateArtifact,
  YamlParseError,
} from "./validate.js";

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
const DOCTOR_OUTPUT_FORMATS = ["json", "text"] as const;

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
    name: "example-model",
    title: "Movie Page Model",
    path: "examples/movie_page/model.py",
    summary: "Pydantic model used by the example.",
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
    name: "python-design",
    title: "Python Package Design",
    path: "docs/softschema-python-design.md",
    summary: "Python package design decisions.",
  },
  { name: "readme", title: "README", path: "README.md", summary: "Short first-visitor overview." },
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
  "example-host",
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
      throw new UsageError(
        `multiple top-level frontmatter keys; pass --envelope to designate the softschema payload (candidates: ${err.candidates.join(", ")})`,
      );
    }
    throw err;
  }
}

interface ValidateOptions {
  contract?: string;
  envelope?: string;
  model?: string;
  profile?: string;
  schema?: string;
  status?: string;
}

function parseSchemaProfile(value: string): Contract["profile"] {
  if (value === "frontmatter-md" || value === "pure-yaml") return value;
  throw new UsageError(`invalid profile: ${value}`);
}

async function runValidate(path: string, opts: ValidateOptions): Promise<number> {
  try {
    // Without --model/--schema this is a metadata-only check: frontmatter parses,
    // the softschema: block is well-formed, and the envelope resolves; structural
    // and semantic layers are reported as skipped. Useful from the `soft` stage on.
    const profile = parseSchemaProfile(opts.profile ?? "frontmatter-md");
    if (opts.contract !== undefined) validateContractId(opts.contract);
    // Read the document once here; both binding inference and validateArtifact reuse
    // this normalized root. Readable parse failures are validation results (exit 1),
    // while access failures remain exit 2.
    let parsed: RawFrontmatter | undefined;
    let pureYaml: Record<string, unknown> | undefined;
    try {
      if (profile === "pure-yaml") pureYaml = readPureYamlArtifact(path);
      else parsed = readFrontmatter(path);
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
    if (profile === "frontmatter-md" && frontmatter === null && opts.contract === undefined) {
      throw new UsageError("missing --contract because the document has no YAML frontmatter");
    }
    const fm = frontmatter ?? {};
    const metadata = parseSchemaMetadata(fm.softschema ?? null);
    const contractId = opts.contract ?? metadata?.contractId;
    if (contractId === undefined) {
      throw new UsageError("missing --contract because the document has no softschema.contract");
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
    const semanticModel = opts.model !== undefined ? await loadZodModel(opts.model) : undefined;
    const descriptor: ContractDescriptor = {
      id: contractId,
      model: opts.model ?? null,
      envelopeKey,
      status,
      profile,
      schemaPath: opts.schema ?? null,
    };
    const contract = bindContract(descriptor, semanticModel ?? null);
    const result = validateArtifact(path, contract, {
      preParsed: parsed,
      preParsedYaml: pureYaml,
    });
    writeText(stableStringify(result.output));
    return result.ok ? 0 : 1;
  } catch (err) {
    // Exit 1 is reserved for a readable artifact that fails validation (the result path
    // above). A bug-indicator exception crashes; every other (user) error — missing or
    // unreadable file, malformed YAML, bad model spec — is a clean one-line stderr
    // message + exit 2 (see reportUserError). Never an uncaught stack trace for a user
    // mistake, never a masked exit 2 for a programmer bug.
    return reportUserError("validate", err);
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
    .argument("<path>")
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
    .action(async (path: string, opts: ValidateOptions) => {
      exitCode = await runValidate(path, opts);
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
