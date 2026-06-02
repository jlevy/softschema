/**
 * Command-line interface for the TypeScript softschema implementation. Mirrors the
 * Python argparse CLI's behavior, exit codes (0 ok / 1 failure / 2 usage), and output
 * bytes so the shared golden corpus passes against both `softschema-py` and `softschema-ts`.
 */
import { readFileSync } from "node:fs";
import { Command } from "commander";
import { parse as yamlParse } from "yaml";
import { regenerate } from "./generate.js";
import { type Contract, isSchemaStatus, metadataToOutput, parseSchemaMetadata } from "./models.js";
import { stableStringify } from "./settings.js";
import { validateArtifact } from "./validate.js";

const DOC_TOPICS: [string, string][] = [
  ["agents", "Repo-level agent instructions."],
  ["development", "Local development workflow."],
  ["example", "Copyable example overview."],
  ["example-artifact", "Copyable Markdown/YAML artifact."],
  ["example-host", "Host registry and validation helper."],
  ["example-model", "Pydantic model used by the example."],
  ["guide", "Concepts, mental model, and adoption path."],
  ["installation", "Installing uv and Python."],
  ["publishing", "Release and PyPI workflow."],
  ["python-design", "Python package design decisions."],
  ["readme", "Short first-visitor overview."],
  ["skill", "Portable agent skill instructions."],
  ["spec", "Language-neutral artifact format."],
];

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

function writeText(text: string): void {
  process.stdout.write(text);
  if (!text.endsWith("\n")) process.stdout.write("\n");
}

function readFrontmatterRaw(path: string): Record<string, unknown> | null {
  const lines = readFileSync(path, "utf8").split(/\r?\n/);
  if (lines[0]?.trim() !== "---") return null;
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i]?.trim() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) return null;
  return (yamlParse(lines.slice(1, end).join("\n")) ?? {}) as Record<string, unknown>;
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

function runValidate(path: string, opts: ValidateOptions): number {
  try {
    if (opts.model === undefined && opts.schema === undefined) {
      throw new UsageError("missing validation implementation; pass --model, --schema, or both");
    }
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
    const result = validateArtifact(path, contract);
    writeText(stableStringify(result.output));
    return result.ok ? 0 : 1;
  } catch (err) {
    if (err instanceof UsageError) {
      process.stderr.write(`softschema validate: ${err.message}\n`);
      return 2;
    }
    throw err;
  }
}

function runInspect(path: string): number {
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
  const width = Math.max(...DOC_TOPICS.map(([name]) => name.length));
  const lines = ["Available softschema docs:", ""];
  for (const [name, summary] of DOC_TOPICS) {
    lines.push(`  ${name.padEnd(width)}  ${summary}`);
  }
  lines.push(
    "",
    "Run `softschema docs <topic>` to print a document.",
    "Copy examples from the printed docs or from the repository files; the CLI does not scaffold or mutate projects.",
  );
  writeText(lines.join("\n"));
  return 0;
}

export function main(argv: string[] = process.argv): number {
  const program = new Command();
  program.name("softschema").description("Validate and explain soft schema Markdown/YAML artifacts.");
  let exitCode = 0;

  program
    .command("validate")
    .argument("<path>")
    .option("--contract <id>")
    .option("--envelope <key>")
    .option("--model <spec>")
    .option("--schema <path>")
    .option("--status <status>")
    .action((path: string, opts: ValidateOptions) => {
      exitCode = runValidate(path, opts);
    });

  program
    .command("inspect")
    .argument("<path>")
    .action((path: string) => {
      exitCode = runInspect(path);
    });

  const docs = program.command("docs");
  docs
    .argument("[topic]", "topic to print")
    .option("--list", "list bundled documentation topics")
    .action((_topic: string | undefined, opts: { list?: boolean }) => {
      if (opts.list) {
        exitCode = runDocsList();
      } else {
        exitCode = runDocsList();
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
    .action((opts: { brief?: boolean }) => {
      writeText(opts.brief ? SKILL_BRIEF : SKILL_BRIEF);
      exitCode = 0;
    });

  program.parse(argv);
  return exitCode;
}

const isMain = import.meta.main ?? process.argv[1]?.endsWith("cli.js");
if (isMain) {
  process.exit(main());
}
