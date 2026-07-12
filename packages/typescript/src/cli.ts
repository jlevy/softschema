#!/usr/bin/env node
import { createHash } from "node:crypto";
/**
 * Command-line interface for the TypeScript softschema implementation. Mirrors the
 * Python argparse CLI's behavior, exit codes (0 ok / 1 failure / 2 usage), and output
 * bytes so the shared golden corpus passes against both `softschema-py` and `softschema-ts`.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Command, CommanderError } from "commander";
import { z } from "zod";
import { compileSchema } from "./compile.js";
import { regenerate } from "./generate.js";
import { type Contract, isSchemaStatus, metadataToOutput, parseSchemaMetadata } from "./models.js";
import { stableStringify } from "./settings.js";
import {
  EnvelopeAmbiguityError,
  inferEnvelopeKey,
  type RawFrontmatter,
  readFrontmatter,
  validateArtifact,
  YamlParseError,
} from "./validate.js";

// The package root holds the bundled `resources/` dir (copied at build, shipped via the
// package `files`). Works whether running src/cli.ts (dev) or dist/cli.js (built/published).
const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const BRIEF_MARKER_START = "<!-- BEGIN SOFTSCHEMA BRIEF -->";
const BRIEF_MARKER_END = "<!-- END SOFTSCHEMA BRIEF -->";
const RUNNER_COMMANDS = ["softschema", "uvx", "npx"] as const;
const RUNNER_INVOCATIONS: Record<(typeof RUNNER_COMMANDS)[number], string> = {
  softschema: "softschema",
  uvx: "uvx softschema@0.2.2",
  npx: "npx -y softschema@0.2.2",
};

const AGENT_HELP_EPILOG = `IMPORTANT for agents:
  To set up softschema for this repo as a skill, run one command from the repo root:
    uvx softschema@0.2.2 skill --install --scope project --agent portable --agent claude
    # or
    npx -y softschema@0.2.2 skill --install --scope project --agent portable --agent claude
  Then read \`softschema skill --brief\` and \`softschema docs --list\` for operating rules
  and bundled docs.`;

/**
 * Read a doc/skill resource by its repo-relative path. Local checkout runs prefer the
 * source file so tests catch source drift; installed packages fall back to bundled
 * `resources/`, so they never depend on the working directory.
 */
function readResource(relPath: string): string {
  const modulePath = fileURLToPath(import.meta.url);
  const expectedSource = join(PACKAGE_ROOT, "src", "cli.ts");
  if (existsSync(expectedSource) && realpathSync(expectedSource) === realpathSync(modulePath)) {
    const source = join(PACKAGE_ROOT, "../..", relPath);
    if (existsSync(source)) return readFileSync(source, "utf8");
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
  "example-model",
  "example-host",
  "example-schema",
];

export const SKILL_INSTALL_TARGETS = {
  portable: ".agents/skills/softschema/SKILL.md",
  claude: ".claude/skills/softschema/SKILL.md",
} as const;

// The format=fNN stamp lets a future installer recognize this managed surface and refuse
// to clobber a newer format. The package version is intentionally omitted so the
// committed mirrors stay deterministic across dev builds (matches the Python marker).
const SKILL_MARKER_RE =
  /<!-- DO NOT EDIT format=f02 source-sha256=([0-9a-f]{64}): written by `softschema skill --install`\.\nRe-run that command to update\.\n-->\n\n/;

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
  const digest = createHash("sha256").update(rendered).digest("hex");
  const marker =
    `<!-- DO NOT EDIT format=f02 source-sha256=${digest}: written by ` +
    "`softschema skill --install`.\nRe-run that command to update.\n-->\n";
  const lines = rendered.split("\n");
  let delimiters = 0;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i]?.trim() === "---") {
      delimiters += 1;
      if (delimiters === 2) {
        lines.splice(i + 1, 0, marker);
        break;
      }
    }
  }
  return lines.join("\n");
}

/** Resolve the install base: the nearest ancestor containing `.git`, else the cwd. */
function resolveInstallBase(start: string): string {
  let dir = resolve(start);
  for (;;) {
    if (existsSync(join(dir, ".git"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) return resolve(start);
    dir = parent;
  }
}

function managedSkillSource(existing: string): string | null {
  const match = SKILL_MARKER_RE.exec(existing);
  if (match?.index === undefined || match[1] === undefined) return null;
  const source = existing.slice(0, match.index) + existing.slice(match.index + match[0].length);
  return createHash("sha256").update(source).digest("hex") === match[1] ? source : null;
}

function runSkillInstall(opts: { scope?: string; agent?: string[]; dryRun?: boolean }): number {
  if (
    (opts.scope !== "project" && opts.scope !== "personal") ||
    opts.agent === undefined ||
    opts.agent.length === 0 ||
    opts.agent.some((agent) => agent !== "portable" && agent !== "claude")
  ) {
    throw new UsageError(
      "skill --install requires --scope project|personal and at least one --agent portable|claude",
    );
  }
  const payload = installSkillPayload(renderedSkill());
  const baseDir = opts.scope === "project" ? resolveInstallBase(process.cwd()) : homedir();
  const pending: { target: string; status: "created" | "updated" }[] = [];
  const files = [...new Set(opts.agent)].map((agent) => {
    const relative = SKILL_INSTALL_TARGETS[agent as keyof typeof SKILL_INSTALL_TARGETS];
    const target = join(baseDir, relative);
    const existing = existsSync(target) ? readFileSync(target, "utf8") : null;
    let status: string;
    if (existing === payload) {
      status = "unchanged";
    } else if (existing !== null && managedSkillSource(existing) === null) {
      throw new UsageError(`refusing to overwrite unmanaged or modified skill: ${target}`);
    } else {
      status = existing !== null ? "would_update" : "would_create";
      pending.push({ target, status: existing !== null ? "updated" : "created" });
    }
    return { path: relative, status };
  });
  if (!opts.dryRun) {
    for (const item of pending) {
      const dir = dirname(item.target);
      mkdirSync(dir, { recursive: true });
      const tmp = join(dir, `.softschema-tmp-${process.pid}-${Date.now()}`);
      writeFileSync(tmp, payload);
      renameSync(tmp, item.target);
      const output = files.find((file) => join(baseDir, file.path) === item.target);
      if (output !== undefined) output.status = item.status;
    }
  }
  writeText(
    stableStringify({
      version: packageVersion(),
      base_dir: baseDir,
      dry_run: Boolean(opts.dryRun),
      files,
    }),
  );
  return 0;
}

function writeText(text: string): void {
  process.stdout.write(text);
  if (!text.endsWith("\n")) process.stdout.write("\n");
}

interface RunnerReport {
  name: (typeof RUNNER_COMMANDS)[number];
  available: boolean;
  path: string | null;
}

interface DoctorReport {
  version: string;
  runners: RunnerReport[];
  recommended_invocation: string | null;
}

function findExecutable(name: string): string | null {
  const pathValue = process.env.PATH ?? "";
  for (const dir of pathValue.split(delimiter)) {
    if (dir === "") continue;
    const candidate = join(dir, name);
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

function doctorReport(): DoctorReport {
  const runners = RUNNER_COMMANDS.map((name) => {
    const path = findExecutable(name);
    return { name, available: path !== null, path };
  });
  const recommended = runners.find((runner) => runner.available)?.name;
  return {
    version: packageVersion(),
    runners,
    recommended_invocation: recommended === undefined ? null : RUNNER_INVOCATIONS[recommended],
  };
}

function doctorText(report: DoctorReport): string {
  const lines = [`softschema version: ${report.version}`, "available runners:"];
  for (const runner of report.runners) {
    const path = runner.path === null ? "" : ` (${runner.path})`;
    lines.push(`  ${runner.name}: ${runner.available ? "yes" : "no"}${path}`);
  }
  lines.push(`recommended invocation: ${report.recommended_invocation ?? "unavailable"}`);
  if (report.recommended_invocation === null) {
    lines.push("Install uv or Node, then retry.");
  }
  return lines.join("\n");
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
  schema?: string;
  status?: string;
}

/** Import `path:export` and confirm the export is a Zod schema before use. */
async function loadZodModel(spec: string): Promise<z.ZodType> {
  const idx = spec.lastIndexOf(":");
  if (idx <= 0) throw new UsageError(`model spec must be path:export, got ${JSON.stringify(spec)}`);
  const exportName = spec.slice(idx + 1);
  let mod: Record<string, unknown>;
  try {
    mod = (await import(pathToFileURL(resolve(spec.slice(0, idx))).href)) as Record<
      string,
      unknown
    >;
  } catch (err) {
    const runtime = process.versions.bun === undefined ? "Node" : "Bun";
    throw new UsageError(
      `cannot import ${JSON.stringify(spec)} with ${runtime}: ${errMessage(err)}. ` +
        "Node model paths must name built JavaScript (.js or .mjs); Bun may load TypeScript directly.",
    );
  }
  const schema = mod[exportName];
  if (schema === undefined) {
    throw new UsageError(`${JSON.stringify(spec)} has no export ${JSON.stringify(exportName)}`);
  }
  if (!(schema instanceof z.ZodType)) {
    throw new UsageError(`${JSON.stringify(spec)} is not a Zod schema`);
  }
  return schema;
}

async function runValidate(path: string, opts: ValidateOptions): Promise<number> {
  try {
    // Without --model/--schema this is a metadata-only check: frontmatter parses,
    // the softschema: block is well-formed, and the envelope resolves; structural
    // and semantic layers are reported as skipped. Useful from the `soft` stage on.
    const semanticModel = opts.model !== undefined ? await loadZodModel(opts.model) : undefined;
    // Read the document once here; both binding inference and validateArtifact reuse
    // this parse (passed as `preParsed`), so the file is parsed a single time.
    let parsed: RawFrontmatter;
    try {
      parsed = readFrontmatter(path);
    } catch (err) {
      if (err instanceof YamlParseError) {
        throw new UsageError(`Error parsing YAML metadata: ${err.message}`);
      }
      throw err;
    }
    const frontmatter = parsed.hasFence ? (parsed.value as Record<string, unknown>) : null;
    if (frontmatter === null && opts.contract === undefined) {
      throw new UsageError("missing --contract because the document has no YAML frontmatter");
    }
    const fm = frontmatter ?? {};
    const metadata = parseSchemaMetadata(fm.softschema ?? null);
    const contractId = opts.contract ?? metadata?.contractId;
    if (contractId === undefined) {
      throw new UsageError("missing --contract because the document has no softschema.contract");
    }
    let status: Contract["status"] = "soft";
    if (opts.status !== undefined) {
      if (!isSchemaStatus(opts.status)) throw new UsageError(`invalid status: ${opts.status}`);
      status = opts.status;
    } else if (metadata?.status) {
      status = metadata.status;
    }
    const contract: Contract = {
      id: contractId,
      model: opts.model ?? null,
      envelopeKey: inferEnvelope(fm, opts.envelope, metadata?.envelope ?? null),
      status,
      profile: "frontmatter-md",
      schemaPath: opts.schema ?? null,
    };
    const result = validateArtifact(path, contract, { semanticModel, preParsed: parsed });
    writeText(stableStringify(result));
    return result.outcome === "valid" ? 0 : result.outcome === "invalid" ? 1 : 2;
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
  opts: { contract: string; schemaId?: string; out: string; check?: boolean },
): Promise<number> {
  try {
    const schema = await loadZodModel(spec);
    const result = compileSchema(schema, opts.out, {
      contractId: opts.contract,
      schemaId: opts.schemaId,
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
    .addHelpText("afterAll", `\n${AGENT_HELP_EPILOG}`)
    .exitOverride();
  let exitCode = 0;

  program
    .command("compile")
    .description("Compile a Zod schema")
    .argument("<model>", "Zod schema as module:export")
    .requiredOption("--out <path>", "output path for the compiled schema")
    .requiredOption("--contract <id>", "logical contract ID stored in x-softschema")
    .option("--schema-id <uri>", "optional absolute JSON Schema resource URI")
    .option("--check", "do not write; exit 1 on drift")
    .action(
      async (
        model: string,
        opts: { out: string; contract: string; schemaId?: string; check?: boolean },
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
    .option("--contract <id>", "override the document contract ID")
    .option(
      "--envelope <key>",
      "override the envelope key (softschema.envelope or single-key inference)",
    )
    .option(
      "--model <spec>",
      "Zod schema as module:export for semantic validation. Optional. Imports and " +
        "runs local code; use only with trusted models",
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
    .description("Report softschema version and runner availability")
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
    .option("--install", "install the skill for each --agent at the selected --scope")
    .option("--scope <scope>", "install scope: project or personal")
    .option(
      "--agent <agent>",
      "target agent: portable or claude (repeatable)",
      (value, previous: string[]) => [...previous, value],
      [],
    )
    .option("--dry-run", "preview installation without writing")
    .action(
      (opts: {
        brief?: boolean;
        install?: boolean;
        scope?: string;
        agent?: string[];
        dryRun?: boolean;
      }) => {
        if (opts.install) {
          exitCode = runSkillInstall(opts);
        } else if (opts.brief) {
          writeText(renderedSkillBrief());
          exitCode = 0;
        } else {
          writeText(renderedSkill());
          exitCode = 0;
        }
      },
    );

  try {
    await program.parseAsync(argv);
  } catch (err) {
    if (err instanceof CommanderError) {
      // --help and --version throw when exitOverride is active; honour the exit code
      // Commander intended (0 for help/version, non-zero for usage errors).
      return err.exitCode;
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
