#!/usr/bin/env node
/**
 * Command-line interface for the TypeScript softschema implementation. Mirrors the
 * Python argparse CLI's behavior, exit codes (0 ok / 1 failure / 2 usage), and output
 * bytes so the shared golden corpus passes against both `softschema-py` and `softschema-ts`.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Command } from "commander";
import { z } from "zod";
import { compileSchema } from "./compile.js";
import { regenerate } from "./generate.js";
import { type Contract, isSchemaStatus, metadataToOutput, parseSchemaMetadata } from "./models.js";
import { stableStringify } from "./settings.js";
import { readFrontmatter, validateArtifact, YamlParseError } from "./validate.js";

// The package root holds the bundled `resources/` dir (copied at build, shipped via the
// package `files`). Works whether running src/cli.ts (dev) or dist/cli.js (built/published).
const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

/**
 * Read a bundled doc/skill resource by its repo-relative path. Resolves from the package's
 * bundled `resources/` first (so it never depends on the working directory), with a
 * walk-up repo fallback for local development before the resources are built.
 */
function readResource(relPath: string): string {
  const bundled = join(PACKAGE_ROOT, "resources", relPath);
  if (existsSync(bundled)) return readFileSync(bundled, "utf8");
  let dir = PACKAGE_ROOT;
  for (let i = 0; i < 6; i++) {
    const candidate = join(dir, relPath);
    if (existsSync(candidate)) return readFileSync(candidate, "utf8");
    dir = resolve(dir, "..");
  }
  throw new Error(`bundled softschema resource not found: ${relPath}`);
}

interface DocTopic {
  name: string;
  title: string;
  path: string;
  summary: string;
}

// Sorted by name to match the Python CLI's `sorted(DOC_TOPICS)` output.
const DOC_TOPICS: DocTopic[] = [
  {
    name: "agents",
    title: "Agent Instructions",
    path: "AGENTS.md",
    summary: "Repo-level agent instructions.",
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
    summary: "Installing uv and Python.",
  },
  {
    name: "publishing",
    title: "Publishing",
    path: "docs/publishing.md",
    summary: "Release and PyPI workflow.",
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

const SKILL_BRIEF = `# Softschema Skill Brief

Use soft schemas when humans or agents write Markdown/YAML artifacts and tools need to
consume some values reliably.

- Read \`softschema docs guide\` for the mental model.
- Read \`softschema docs spec\` for the exact artifact format.
- Inspect \`softschema docs example\` and \`softschema docs example-artifact\` for the
  copyable movie example.
- Treat YAML/frontmatter as authoritative.
- Do not parse Markdown body prose or tables for consumed values.
- Use \`softschema.contract\` to name the payload contract.
- Keep examples copyable; do not scaffold or mutate a target project unless the user
  explicitly asks for that workflow.
`;

const SKILL_INSTALL_TARGETS = [
  ".agents/skills/softschema/SKILL.md",
  ".claude/skills/softschema/SKILL.md",
];

const SKILL_DO_NOT_EDIT_MARKER =
  "<!-- DO NOT EDIT: written by `softschema skill --install`.\nRe-run that command to update.\n-->\n";

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

function renderedSkill(): string {
  return readResource("skills/softschema/SKILL.md").replaceAll("<version>", packageVersion());
}

/** Insert the DO NOT EDIT marker after the closing frontmatter delimiter (matches Python). */
function installSkillPayload(rendered: string): string {
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

function runSkillInstall(): number {
  const payload = installSkillPayload(renderedSkill());
  const files = SKILL_INSTALL_TARGETS.map((relative) => {
    const target = join(process.cwd(), relative);
    const existing = existsSync(target) ? readFileSync(target, "utf8") : null;
    let status: string;
    if (existing === payload) {
      status = "unchanged";
    } else {
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, payload);
      status = existing !== null ? "updated" : "created";
    }
    return { path: relative, status };
  });
  writeText(stableStringify({ version: packageVersion(), base_dir: process.cwd(), files }));
  return 0;
}

function writeText(text: string): void {
  process.stdout.write(text);
  if (!text.endsWith("\n")) process.stdout.write("\n");
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
  const keys = envelopeKeys(frontmatter);
  if (keys.length === 1) return keys[0] as string;
  if (keys.length === 0) return null;
  throw new UsageError(
    `multiple top-level frontmatter keys; pass --envelope to designate the softschema payload (candidates: ${keys.join(", ")})`,
  );
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
    throw new UsageError(`cannot import ${JSON.stringify(spec)}: ${(err as Error).message}`);
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
    if (opts.model === undefined && opts.schema === undefined) {
      throw new UsageError("missing validation implementation; pass --model, --schema, or both");
    }
    const semanticModel = opts.model !== undefined ? await loadZodModel(opts.model) : undefined;
    const frontmatter = readFrontmatterRaw(path);
    if (frontmatter === null) {
      if (opts.contract === undefined) {
        throw new UsageError("missing --contract because the document has no YAML frontmatter");
      }
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
    const result = validateArtifact(path, contract, { semanticModel });
    writeText(stableStringify(result.output));
    return result.ok ? 0 : 1;
  } catch (err) {
    if (err instanceof UsageError) {
      process.stderr.write(`softschema validate: ${err.message}\n`);
      return 2;
    }
    // Any other failure (e.g. an unreadable or malformed schema sidecar) is reported as a
    // stable error line with exit 1, never an uncaught stack trace.
    process.stderr.write(`softschema validate: ${(err as Error).message}\n`);
    return 1;
  }
}

function runInspect(path: string): number {
  let frontmatter: Record<string, unknown> | null;
  try {
    frontmatter = readFrontmatterRaw(path);
  } catch (err) {
    if (err instanceof UsageError) {
      process.stderr.write(`softschema inspect: ${err.message}\n`);
      return 2;
    }
    throw err;
  }
  const metadata = frontmatter ? parseSchemaMetadata(frontmatter.softschema ?? null) : null;
  const output = {
    envelope_keys: frontmatter ? envelopeKeys(frontmatter) : [],
    has_frontmatter: frontmatter !== null,
    metadata: metadataToOutput(metadata),
    path,
  };
  writeText(stableStringify(output));
  return 0;
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
    process.stderr.write(`softschema compile: ${(err as Error).message}\n`);
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
      process.stderr.write(`error: ${path}: ${(err as Error).message}\n`);
      return 1;
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
    .description("Validate and explain soft schema Markdown/YAML artifacts.");
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
    .command("skill")
    .option("--brief", "print compact skill guidance")
    .option("--install", "write discoverable skill mirrors into .agents and .claude")
    .action((opts: { brief?: boolean; install?: boolean }) => {
      if (opts.install) {
        exitCode = runSkillInstall();
      } else if (opts.brief) {
        writeText(SKILL_BRIEF);
        exitCode = 0;
      } else {
        writeText(renderedSkill());
        exitCode = 0;
      }
    });

  await program.parseAsync(argv);
  return exitCode;
}

const isMain = import.meta.main ?? process.argv[1]?.endsWith("cli.js");
if (isMain) {
  main().then((code) => process.exit(code));
}
