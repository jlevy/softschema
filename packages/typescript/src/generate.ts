/**
 * Generated schema sections: deterministic Markdown blocks rendered from a SchemaView.
 * Idiomatic mirror of the Python `generate.py`; renderer output is byte-identical so a
 * `softschema generate` on either CLI produces the same marker bodies.
 */
import { readFileSync } from "node:fs";
import { dirname, isAbsolute, join } from "node:path";
import { writeFileSync } from "atomically";
import { SchemaView } from "./schemaView.js";

const MARKER_OPEN = /<!--\s*softschema:generated\s+([^>]*?)\s*-->/g;
const MARKER_CLOSE = "<!-- /softschema:generated -->";
const ATTR_PATTERN = /([A-Za-z_][A-Za-z0-9_]*)="([^"]*)"/g;
const KNOWN_ATTRS = new Set(["kind", "schema", "pointer", "sha256"]);
const CONTRACT_ATTR_RENAME =
  'softschema:generated marker uses the removed "contract" attribute for a schema ' +
  'path; rename it to "schema" (contract is a logical ID, not a file path)';

export interface GeneratedSection {
  start: number;
  end: number;
  attrs: Record<string, string>;
  existingContent: string;
}

export interface RegenerateResult {
  path: string;
  sections: number;
  drift: boolean;
  driftDetails: string[];
}

function parseAttrs(attrString: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  for (const match of attrString.matchAll(ATTR_PATTERN)) {
    attrs[match[1] as string] = match[2] as string;
  }
  return attrs;
}

export function parseSections(text: string): GeneratedSection[] {
  const sections: GeneratedSection[] = [];
  MARKER_OPEN.lastIndex = 0;
  let openMatch: RegExpExecArray | null = MARKER_OPEN.exec(text);
  while (openMatch !== null) {
    const contentStart = openMatch.index + openMatch[0].length;
    const closeIndex = text.indexOf(MARKER_CLOSE, contentStart);
    if (closeIndex === -1) {
      throw new Error(
        `unterminated softschema:generated marker starting at offset ${openMatch.index}`,
      );
    }
    sections.push({
      start: contentStart,
      end: closeIndex,
      attrs: parseAttrs(openMatch[1] as string),
      existingContent: text.slice(contentStart, closeIndex),
    });
    MARKER_OPEN.lastIndex = closeIndex + MARKER_CLOSE.length;
    openMatch = MARKER_OPEN.exec(text);
  }
  return sections;
}

function resolveSchemaPath(schema: string, base: string): string {
  const path = isAbsolute(schema) ? schema : join(base, schema);
  return path;
}

function renderEnumTable(view: SchemaView): string {
  const lines = ["| Field | Allowed values |", "| --- | --- |"];
  for (const fieldInfo of view.iterFields()) {
    if (fieldInfo.enum === null) continue;
    lines.push(`| \`${fieldInfo.name}\` | ${fieldInfo.enum.join(", ")} |`);
  }
  if (lines.length === 2) lines.push("| _(no enum fields)_ | _(none)_ |");
  return lines.join("\n");
}

function renderFieldList(view: SchemaView): string {
  const lines: string[] = [];
  for (const fieldInfo of view.iterFields()) {
    if (fieldInfo.pointer.split("/properties/").length - 1 > 1) continue;
    const typeLabel = fieldInfo.jsonType ?? "object";
    const required = fieldInfo.required ? "required" : "optional";
    const description = fieldInfo.description ?? "";
    if (description) {
      lines.push(`- \`${fieldInfo.name}\` (${typeLabel}, ${required}): ${description}`);
    } else {
      lines.push(`- \`${fieldInfo.name}\` (${typeLabel}, ${required})`);
    }
  }
  if (lines.length === 0) lines.push("- _(no fields)_");
  return lines.join("\n");
}

function renderVocab(view: SchemaView, attrs: Record<string, string>): string {
  const pointer = attrs.pointer;
  if (!pointer) throw new Error("softschema:generated kind=vocab requires a 'pointer' attribute");
  const values = view.enumValues(pointer);
  if (values === null) throw new Error(`no enum at pointer ${JSON.stringify(pointer)}`);
  return values.map((v) => `- \`${v}\``).join("\n");
}

const RENDERERS: Record<string, (view: SchemaView, attrs: Record<string, string>) => string> = {
  enum_table: (view) => renderEnumTable(view),
  field_list: (view) => renderFieldList(view),
  vocab: renderVocab,
};

function renderSection(section: GeneratedSection, schemaRoot: string): string {
  if ("contract" in section.attrs) throw new Error(CONTRACT_ATTR_RENAME);
  const unknown = Object.keys(section.attrs)
    .filter((key) => !KNOWN_ATTRS.has(key))
    .sort();
  if (unknown.length > 0) {
    throw new Error(`softschema:generated marker has unknown attribute(s): ${unknown.join(", ")}`);
  }
  const kind = section.attrs.kind ?? "";
  const schema = section.attrs.schema ?? "";
  if (!kind) throw new Error("softschema:generated marker is missing 'kind'");
  if (!schema) throw new Error("softschema:generated marker is missing 'schema'");
  const renderer = RENDERERS[kind];
  if (renderer === undefined) {
    const known = Object.keys(RENDERERS).sort().join(", ");
    throw new Error(`unknown softschema:generated kind ${JSON.stringify(kind)}; known: ${known}`);
  }
  const schemaPath = resolveSchemaPath(schema, schemaRoot);
  const view = SchemaView.load(schemaPath);
  return `\n${renderer(view, section.attrs)}\n`;
}

export function regenerate(
  path: string,
  options: { check?: boolean; schemaRoot?: string } = {},
): RegenerateResult {
  const text = readFileSync(path, "utf8");
  const sections = parseSections(text);
  const result: RegenerateResult = {
    path,
    sections: sections.length,
    drift: false,
    driftDetails: [],
  };
  if (sections.length === 0) return result;

  const base = options.schemaRoot ?? dirname(path);
  let newText = "";
  let cursor = 0;
  for (const section of sections) {
    const rendered = renderSection(section, base);
    newText += text.slice(cursor, section.start) + rendered;
    cursor = section.end;
    if (rendered !== section.existingContent) {
      result.drift = true;
      result.driftDetails.push(`${path}: section ${section.attrs.kind ?? "?"} drifted`);
    }
  }
  newText += text.slice(cursor);

  if (!options.check && result.drift) {
    writeFileSync(path, newText, { encoding: "utf8" });
  }
  return result;
}
