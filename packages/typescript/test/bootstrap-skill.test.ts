/** Shared doctor-v1 and deterministic bootstrap parity gates. */

import { afterEach, beforeEach, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import type { AnySchema } from "ajv";
import Ajv2020 from "ajv/dist/2020.js";
import { main } from "../src/cli.js";

const ROOT = resolve(import.meta.dir, "../../..");
const CONFORMANCE = join(ROOT, "conformance");
const argv = (...args: string[]) => ["bun", "cli.ts", ...args];

let stdout = "";
let originalWrite: typeof process.stdout.write;

interface DoctorReport {
  build: unknown;
  package: { name: string; version: string; release_state: string };
  protocol_version: string;
  runtime: { name: string; version: string };
  capabilities: {
    artifact_formats: string[];
    conformance: { version: string; status: string };
    model_loaders: string[];
    operations: string[];
    output_formats: string[];
  };
}

interface ReleaseMetadata {
  discovery_protocol: string;
  logical_version: string;
  release_state: string;
  packages: { python: { pin: string }; npm: { pin: string } };
  artifact_formats: { current: string; supported: string[] };
  conformance: { version: string; status: string };
}

interface ActivationMatrix {
  observations: Array<{ agent: string; activation_observed: boolean }>;
  activation_cases: Array<{ expected_activation: boolean }>;
}

beforeEach(() => {
  stdout = "";
  originalWrite = process.stdout.write.bind(process.stdout);
  process.stdout.write = ((chunk: string | Uint8Array) => {
    stdout += chunk.toString();
    return true;
  }) as typeof process.stdout.write;
});

afterEach(() => {
  process.stdout.write = originalWrite;
});

function loadJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

function normalizedDoctor(report: DoctorReport): DoctorReport {
  const normalized = structuredClone(report);
  normalized.build = "<build-metadata>";
  normalized.package.version = "<logical-version>";
  normalized.package.release_state = "<release-state>";
  normalized.protocol_version = "<discovery-protocol>";
  normalized.runtime = { name: "<runtime-name>", version: "<runtime-version>" };
  normalized.capabilities.artifact_formats = ["<artifact-formats>"];
  normalized.capabilities.model_loaders = ["<model-loaders>"];
  normalized.capabilities.conformance = {
    version: "<conformance-version>",
    status: "<conformance-status>",
  };
  return normalized;
}

test("doctor --json matches the shared v1 golden and schema under Bun", async () => {
  expect(await main(argv("doctor", "--json"))).toBe(0);
  const report = JSON.parse(stdout) as DoctorReport;
  const release = loadJson<ReleaseMetadata>(join(ROOT, "release-metadata.json"));
  const build = loadJson<unknown>(join(ROOT, "build-metadata.json"));
  const golden = loadJson<DoctorReport>(
    join(CONFORMANCE, "doctor/doctor-v1-common.golden.json"),
  );
  expect(normalizedDoctor(report)).toEqual(golden);
  expect(report.protocol_version).toBe(release.discovery_protocol);
  expect(report.package).toEqual({
    name: "softschema",
    version: release.logical_version,
    release_state: release.release_state,
  });
  expect(report.runtime.name).toBe("bun");
  expect(release.artifact_formats).toEqual({
    current: "1",
    supported: ["legacy-0.2", "1"],
  });
  expect(report.capabilities.model_loaders).toEqual(["json-schema", "zod"]);
  expect(report.capabilities.artifact_formats).toEqual(
    [...release.artifact_formats.supported].sort(),
  );
  expect(report.capabilities.conformance).toEqual(release.conformance);
  expect(report.build).toEqual(build);

  const doctorSchema = loadJson<AnySchema>(
    join(CONFORMANCE, "schemas/doctor-result.schema.json"),
  );
  const buildSchema = loadJson<AnySchema>(
    join(CONFORMANCE, "schemas/build-metadata.schema.json"),
  );
  const ajv = new Ajv2020({ strict: false });
  ajv.addSchema(buildSchema);
  expect(ajv.validate(doctorSchema, report), JSON.stringify(ajv.errors)).toBe(true);
});

test("skill embeds release-pinned bootstrap candidates in fixed order", () => {
  const fixture = loadJson<{
    commands: Array<{ kind: string; command: string; argv: string[] }>;
  }>(
    join(CONFORMANCE, "agent-skills/bootstrap-commands-v1.json"),
  );
  const release = loadJson<ReleaseMetadata>(join(ROOT, "release-metadata.json"));
  const commands = fixture.commands;
  expect(commands.map((item) => item.kind)).toEqual([
    "local",
    "python-fallback",
    "node-fallback",
    "bun-fallback",
  ]);
  expect(commands[1]?.argv[1]).toBe(`softschema==${release.packages.python.pin}`);
  expect(commands[2]?.argv[1]).toBe(`softschema@${release.packages.npm.pin}`);
  expect(commands[3]?.argv[1]).toBe(`softschema@${release.packages.npm.pin}`);
  const skill = readFileSync(join(ROOT, "skills/softschema/SKILL.md"), "utf8");
  const offsets = commands.map((item) => skill.indexOf(item.command));
  expect(offsets.every((offset) => offset >= 0)).toBe(true);
  expect(offsets).toEqual([...offsets].sort((a, b) => a - b));
});

test("activation fixture covers positive and negative cases without false live claims", () => {
  const matrix = loadJson<ActivationMatrix>(
    join(CONFORMANCE, "agent-skills/activation-matrix-v1.json"),
  );
  expect(new Set(matrix.observations.map((item) => item.agent))).toEqual(
    new Set([
      "codex",
      "claude",
      "gemini",
      "copilot",
      "cursor",
      "windsurf",
      "opencode",
      "aider",
      "cline",
      "roo",
    ]),
  );
  expect(new Set(matrix.activation_cases.map((item) => item.expected_activation))).toEqual(
    new Set([true, false]),
  );
  expect(matrix.observations.some((item) => item.activation_observed)).toBe(false);
});
