#!/usr/bin/env node
/**
 * Command-line interface for the TypeScript softschema implementation. Mirrors the
 * Python argparse CLI's behavior, exit codes (0 ok / 1 failure / 2 usage), and output
 * bytes so the shared golden corpus passes against both `softschema-py` and `softschema-ts`.
 */
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
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
  uvx: "uvx softschema@latest",
  npx: "npx softschema@latest",
};

const AGENT_HELP_EPILOG = `IMPORTANT for agents:
  To set up softschema for this repo as a skill, run one command from the repo root:
    uvx softschema@latest skill --install
    # or
    npx softschema@latest skill --install
  Then read \`softschema skill --brief\` and \`softschema docs --list\` for operating rules
  and bundled docs.`;

/**
 * Read a doc/skill resource by its repo-relative path. Local checkout runs prefer the
 * source file so tests catch source drift; installed packages fall back to bundled
 * `resources/`, so they never depend on the working directory.
 */
const MAX_RESOURCE_WALK_DEPTH = 6;

function readResource(relPath: string): string {
  let dir = PACKAGE_ROOT;
  for (let i = 0; i < MAX_RESOURCE_WALK_DEPTH; i++) {
    const candidate = join(dir, relPath);
    if (existsSync(candidate)) return readFileSync(candidate, "utf8");
    dir = resolve(dir, "..");
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
    name: "guide",
    title: "Softschema Guide",
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
    title: "Softschema Skill",
    path: "skills/softschema/SKILL.md",
    summary: "Portable agent skill instructions.",
  },
  {
    name: "spec",
    title: "Softschema Spec",
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

const COPYABLE_EXAMPLES = ["example", "example-artifact", "example-model", "example-host"];

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
  return `# Softschema Skill Brief\n\n${extractMarkedSection(renderedSkill()).trim()}\n`;
}

/** Insert the DO NOT EDIT marker after the closing frontmatter delimiter (matches Python). */
export function installSkillPayload(rendered: string): string {
  const lines = rendered.split("\n");
  let delimiters = 0;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i]?.trim() === "---") {
      delimiters += 1;
      if (delimiters === 2) {
        lines.splice(i + 1, 0, SKILL_DO_NOT_EDIT_MARKER);
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

function runSkillInstall(): number {
  const payload = installSkillPayload(renderedSkill());
  const baseDir = resolveInstallBase(process.cwd());
  const files = SKILL_INSTALL_TARGETS.map((relative) => {
    const target = join(baseDir, relative);
    const existing = existsSync(target) ? readFileSync(target, "utf8") : null;
    let status: string;
    if (existing === payload) {
      status = "unchanged";
    } else {
      const dir = dirname(target);
      mkdirSync(dir, { recursive: true });
      // Atomic write: write to a temp file in the same directory, then rename.
      // fs.renameSync is atomic on the same filesystem (POSIX guarantee).
      const tmp = join(dir, `.softschema-tmp-${process.pid}-${Date.now()}`);
      writeFileSync(tmp, payload);
      renameSync(tmp, target);
      status = existing !== null ? "updated" : "created";
    }
    return { path: relative, status };
  });
  writeText(stableStringify({ version: packageVersion(), base_dir: baseDir, files }));
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
): string | null {
  if (override !== undefined) return override;
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
    mod = (await import(resolve(spec.slice(0, idx)))) as Record<string, unknown>;
  } catch (err) {
    throw new UsageError(`cannot import ${JSON.stringify(spec)}: ${errMessage(err)}`);
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
      envelopeKey: inferEnvelope(fm, opts.envelope),
      status,
      profile: "frontmatter-md",
      schemaPath: opts.schema ?? null,
    };
    const result = validateArtifact(path, contract, { semanticModel, preParsed: parsed });
    writeText(stableStringify(result.output));
    return result.ok ? 0 : 1;
  } catch (err) {
    // IO/parse/usage failures (missing or unreadable file, malformed YAML, bad model
    // spec) are reported as a stable one-line stderr message with exit 2, matching the
    // Python CLI's error boundary. Exit 1 is reserved for a readable artifact that fails
    // validation (the result path above). Never an uncaught stack trace.
    process.stderr.write(`softschema validate: ${errMessage(err)}\n`);
    return 2;
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
    // Missing/unreadable file, malformed YAML, or a malformed softschema block are all
    // user errors: a one-line stderr message and exit 2, matching the Python CLI.
    process.stderr.write(`softschema inspect: ${errMessage(err)}\n`);
    return 2;
  }
}

async function runCompile(
  spec: string,
  opts: { contract?: string; out: string; check?: boolean },
): Promise<number> {
  try {
    const schema = await loadZodModel(spec);
    const result = compileSchema(schema, opts.out, {
      contractId: opts.contract ?? null,
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
    process.stderr.write(`softschema compile: ${errMessage(err)}\n`);
    return 2;
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
      // Runtime errors (missing file, bad marker) are usage failures: exit 2 with the
      // command prefix, matching the Python CLI. Exit 1 is reserved for drift.
      process.stderr.write(`softschema generate: ${path}: ${errMessage(err)}\n`);
      return 2;
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

function runDocsList(): number {
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
  writeText(lines.join("\n"));
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
  } catch {
    process.stderr.write(`softschema docs: resource not found: ${found.path}\n`);
    return 2;
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
    .argument("<model>", "Zod schema as module:export")
    .requiredOption("--out <path>")
    .option("--contract <id>")
    .option("--check", "do not write; exit 1 on drift")
    .action(async (model: string, opts: { out: string; contract?: string; check?: boolean }) => {
      exitCode = await runCompile(model, opts);
    });

  program
    .command("validate")
    .argument("<path>")
    .option("--contract <id>")
    .option("--envelope <key>")
    .option("--model <spec>")
    .option("--schema <path>")
    .option("--status <status>")
    .action(async (path: string, opts: ValidateOptions) => {
      exitCode = await runValidate(path, opts);
    });

  program
    .command("inspect")
    .argument("<path>")
    .action((path: string) => {
      exitCode = runInspect(path);
    });

  program
    .command("docs")
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
    .argument("<paths...>")
    .option("--check", "do not write; exit 1 if any section is stale")
    .action((paths: string[], opts: { check?: boolean }) => {
      exitCode = runGenerate(paths, opts);
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
    .option("--brief", "print compact skill guidance")
    .option("--install", "write discoverable skill mirrors into .agents and .claude")
    .action((opts: { brief?: boolean; install?: boolean }) => {
      if (opts.install) {
        exitCode = runSkillInstall();
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
      return err.exitCode;
    }
    // Top-level backstop (mirrors the Python CLI's per-command error boundary): no
    // command handler should leak a stack trace. Report a clean one-line message and
    // exit 2 for any otherwise-unhandled error.
    process.stderr.write(`softschema: ${errMessage(err)}\n`);
    return 2;
  }
  return exitCode;
}

const isMain = import.meta.main ?? process.argv[1]?.endsWith("cli.js");
if (isMain) {
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
