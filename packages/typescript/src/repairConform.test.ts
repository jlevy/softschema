/**
 * Repair and conform, driven by the shared vectors.
 *
 * The vectors own the *rules* — which documents repair, which conform, which are
 * deliberately left alone — and running the same file here is what proves the two
 * implementations agree. This module adds the handful of cases the shared corpus cannot
 * carry: the filesystem boundary, and the semantic (Zod) conform source, which is
 * per-language by design.
 */
import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as parseYaml, stringify as stringifyYaml } from "yaml";
import { z } from "zod";
import { conformArtifact } from "./conform.js";
import type { Contract, SchemaProfile } from "./models.js";
import { repairArtifact } from "./repair.js";
import { repairAndValidateArtifact } from "./repairValidate.js";
import { validateArtifact } from "./validate.js";

const VECTORS = join(import.meta.dir, "../../../tests/vectors/hardening.yaml");

interface RepairCase {
  id: string;
  profile: SchemaProfile;
  text: string;
  repaired: boolean;
  expected_text?: string;
  code?: string;
}

interface ConformCase {
  id: string;
  schema: Record<string, unknown>;
  text: string;
  envelope: string;
  changed: boolean;
  expected_text?: string;
}

function vectors<T>(name: string): T[] {
  return (parseYaml(readFileSync(VECTORS, "utf8")) as Record<string, T[]>)[name] as T[];
}

function scratch(): string {
  return mkdtempSync(join(tmpdir(), "softschema-repair-"));
}

function contractFor(overrides: Partial<Contract> = {}): Contract {
  return {
    id: "test:Thing",
    model: null,
    envelopeKey: "thing",
    status: "soft",
    profile: "frontmatter-md",
    schemaPath: null,
    ...overrides,
  };
}

describe("yaml repair vectors", () => {
  for (const item of vectors<RepairCase>("yaml_repair")) {
    test(item.id, () => {
      const suffix = item.profile === "pure-yaml" ? ".yaml" : ".md";
      const path = join(scratch(), `artifact${suffix}`);
      writeFileSync(path, item.text);

      const result = repairArtifact(path, { profile: item.profile, write: true });

      expect(result.changed).toBe(item.repaired);
      if (item.repaired) {
        expect(readFileSync(path, "utf8")).toBe(item.expected_text as string);
      } else {
        // Whatever the reason, an unrepaired document is left exactly as it was found.
        expect(readFileSync(path, "utf8")).toBe(item.text);
        if (item.code !== undefined) expect(result.errorCode).toBe(item.code);
      }
    });
  }
});

describe("schema conform vectors", () => {
  for (const item of vectors<ConformCase>("schema_conform")) {
    test(item.id, () => {
      const dir = scratch();
      const path = join(dir, "artifact.md");
      writeFileSync(path, item.text);
      const schemaPath = join(dir, "schema.yaml");
      writeFileSync(schemaPath, stringifyYaml(item.schema));

      const result = conformArtifact(path, {
        schema: parseYaml(readFileSync(schemaPath, "utf8")) as Record<string, unknown>,
        envelopeKey: item.envelope,
        write: true,
      });

      expect(result.changed).toBe(item.changed);
      expect(readFileSync(path, "utf8")).toBe(item.expected_text ?? item.text);
    });
  }
});

describe("filesystem boundary", () => {
  test("repair is idempotent", () => {
    const path = join(scratch(), "a.md");
    writeFileSync(path, "---\nthing:\n  summary: Note: actually Q1\n---\nBody.\n");

    repairArtifact(path, { profile: "frontmatter-md", write: true });
    const once = readFileSync(path, "utf8");
    repairArtifact(path, { profile: "frontmatter-md", write: true });

    expect(readFileSync(path, "utf8")).toBe(once);
  });

  test("check mode never writes", () => {
    const path = join(scratch(), "a.md");
    const original = "---\nthing:\n  summary: Note: actually Q1\n---\nBody.\n";
    writeFileSync(path, original);

    const result = repairArtifact(path, { profile: "frontmatter-md", write: false });

    expect(result.changed).toBe(true);
    expect(readFileSync(path, "utf8")).toBe(original);
  });

  test("a missing file is reported, not thrown", () => {
    const result = repairArtifact(join(scratch(), "nope.md"), { profile: "frontmatter-md" });

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe("artifact_unreadable");
  });
});

describe("semantic conform source", () => {
  /**
   * A contract with a model and no schema path still conforms.
   *
   * This is the regression guard for the case that motivated reading both validation
   * layers. A host registering contracts as Zod schemas binds no compiled schema, so the
   * structural layer reports `skipped_reason: "no_schema"` and a conform keyed only on it
   * would silently do nothing.
   */
  test("conform fires for a model-only contract", () => {
    const path = join(scratch(), "a.md");
    writeFileSync(path, "---\nthing:\n  name: 1850\n---\nBody.\n");

    const result = conformArtifact(path, {
      model: z.object({ name: z.string() }),
      envelopeKey: "thing",
      write: true,
    });

    expect(result.changed).toBe(true);
    expect(readFileSync(path, "utf8")).toBe("---\nthing:\n  name: '1850'\n---\nBody.\n");
  });

  test("no schema and no model says so rather than reporting success", () => {
    const path = join(scratch(), "a.md");
    writeFileSync(path, "---\nthing:\n  name: 1850\n---\nBody.\n");

    const result = conformArtifact(path, { envelopeKey: "thing", write: true });

    expect(result.changed).toBe(false);
    expect(result.skipped_reason).toBe("no_contract_binding");
  });
});

describe("the escalating pass", () => {
  test("writes once and reports both passes", () => {
    const dir = scratch();
    const schemaPath = join(dir, "schema.yaml");
    writeFileSync(
      schemaPath,
      "type: object\nrequired: [name, summary]\nproperties:\n  name: {type: string}\n  summary: {type: string}\n",
    );
    const path = join(dir, "a.md");
    writeFileSync(path, "---\nthing:\n  name: 1850\n  summary: Note: actually Q1\n---\nBody.\n");

    const result = repairAndValidateArtifact(path, contractFor({ schemaPath }), { write: true });

    expect(result.outcome).toBe("valid");
    expect(result.repairs.map((r) => r.code)).toEqual(["yaml_quoted_scalar", "scalar_conformed"]);
    expect(readFileSync(path, "utf8")).toBe(
      "---\nthing:\n  name: '1850'\n  summary: \"Note: actually Q1\"\n---\nBody.\n",
    );
  });

  /** The no-widening invariant, at the level a caller sees it. */
  test("leaves a valid document byte-identical", () => {
    const dir = scratch();
    const schemaPath = join(dir, "schema.yaml");
    writeFileSync(schemaPath, "type: object\nproperties:\n  name: {type: string}\n");
    const path = join(dir, "a.md");
    const original = "---\nthing:\n  name: 'fine'   # spaced comment\n---\nBody.\n";
    writeFileSync(path, original);

    const result = repairAndValidateArtifact(path, contractFor({ schemaPath }), { write: true });

    expect(result.repairs).toEqual([]);
    expect(readFileSync(path, "utf8")).toBe(original);
  });

  test("does not invent a missing field or rename a near-miss key", () => {
    const dir = scratch();
    const schemaPath = join(dir, "schema.yaml");
    writeFileSync(
      schemaPath,
      "type: object\nrequired: [rationale]\nproperties:\n  rationale: {type: string}\n",
    );
    const path = join(dir, "a.md");
    writeFileSync(path, "---\nthing:\n  reason: because\n---\nBody.\n");

    const result = repairAndValidateArtifact(path, contractFor({ schemaPath }), { write: true });

    expect(result.outcome).toBe("invalid");
    expect(result.repairs).toEqual([]);
    expect(readFileSync(path, "utf8")).toBe("---\nthing:\n  reason: because\n---\nBody.\n");
    expect(result.structural.errors.map((e) => e.code)).toEqual(["missing_property"]);
  });
});

describe("the failure path", () => {
  /**
   * The failure path hands validation the file, not a marker of the pipeline's own.
   *
   * Regression guard for the Python sentinel bug: `--repair` on a document repair cannot
   * rescue must report exactly what plain `validate` reports — same kind, same outcome.
   */
  test("an unrepairable document matches plain validate", () => {
    const path = join(scratch(), "a.md");
    const original = "---\nthing: [unclosed\n---\nBody.\n";
    writeFileSync(path, original);
    const contract = contractFor({ envelopeKey: null });

    const repaired = repairAndValidateArtifact(path, contract, { write: true });
    const plain = validateArtifact(path, contract);

    expect(repaired.repairs).toEqual([]);
    expect(repaired.outcome).toBe(plain.outcome);
    expect(repaired.structural.errors[0]?.kind).toBe(plain.structural.errors[0]?.kind);
    expect(repaired.structural.errors[0]?.kind).toBe("yaml_parse_error");
    expect(readFileSync(path, "utf8")).toBe(original);
  });

  test("a missing file is an input error", () => {
    const result = repairAndValidateArtifact(join(scratch(), "nope.md"), contractFor(), {
      write: true,
    });

    expect(result.outcome).toBe("input_error");
    expect(result.structural.errors[0]?.kind).toBe("artifact_unreadable");
    expect(result.repairs).toEqual([]);
  });
});
