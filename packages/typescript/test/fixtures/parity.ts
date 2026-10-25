/**
 * Comprehensive cross-language parity fixture (Zod side): the idiomatic mirror of
 * examples/parity/model.py. Both must compile to the same canonical schema
 * (schema_sha256 of examples/parity/parity.schema.yaml). Nested objects carry `id` meta
 * so their $defs keys match the Pydantic class names.
 */
import { z } from "zod";
import { softField } from "../../src/softField.js";

export const Address = z
  .strictObject({
    street: z.string(),
    zip_code: z.string().regex(/^[0-9]{5}$/),
  })
  .meta({ id: "Address", description: "A nested object, extracted to $defs and referenced by $ref." });

export const Event = z
  .strictObject({
    name: z.string(),
    timestamp: z.int().min(0),
  })
  .meta({
    id: "Event",
    description:
      "A nested object referenced from more than one field (reuse → single $defs entry).",
  });

export const KitchenSink = z
  .strictObject({
    title: z.string(),
    count: z.int().min(0).max(100),
    ratio: z.number().gt(0).lt(1),
    step: z.int().multipleOf(5),
    code: z.string().min(2).max(8).regex(/^[A-Z]+$/),
    sku: z.string().startsWith("SKU-"),
    filename: z.string().endsWith(".md"),
    contact: z.string().includes("@"),
    active: z.boolean(),
    calendar_date: z.iso.date(),
    calendar_datetime: z.iso.datetime({ offset: true }),
    calendar_duration: z.iso.duration(),
    calendar_time: z.iso.time(),
    kind: z.enum(["alpha", "beta", "gamma"]),
    priority: z.int().default(1),
    label: z.string().default("none"),
    enabled: z.boolean().default(true),
    tags: z.array(z.string()).min(1),
    notes: z.string().nullable().default(null),
    nickname: z.string().nullable().default("n/a"),
    rank: z.enum(["low", "high"]).nullable().default(null),
    // Text the compilers must escape: U+0085, U+2028 and U+2029 in a description, a
    // default, and an enum value. Both writers emit `\N`, `\L` and `\P`, and both readers
    // read the sidecar back; raw, the portable preflight would reject it.
    separator: z
      .enum(["next\u0085line", "line\u2028separator"])
      .default("next\u0085line")
      .describe("Carries a next line\u0085a line\u2028and a paragraph\u2029separator."),
    // Text one writer or the other once wrote in a form the other reader refused: a CRLF
    // (Python folded it in a block literal), a tab in a plain scalar and a bare `=` (the
    // yaml package wrote them plain, ruamel refused them). Both writers now quote them.
    control_text: z
      .enum(["=", "tab\there"])
      .default("tab\there")
      .describe("Carries a CRLF\r\nand a tab\tand ends with ="),
    primary: Address,
    secondary: Address.nullable().default(null),
    history: z.array(Event).optional(),
    last_event: Event.nullable().default(null),
    pair: z.tuple([z.string(), z.int()]),
    scores: z.record(z.string(), z.int()).optional(),
    mixed: z.union([z.int(), z.string()]),
    channels: softField(z.array(z.string()).min(1), {
      description: "Delivery channels.",
      group: "routing",
      order: 1,
      tier: "constrained",
      owner: "agent",
      instruction: "Pick from the approved channel vocabulary.",
      examples: ["email", "sms"],
      aliases: { email: ["e-mail", "mail"] },
      repair: "suggest_alias",
    }),
  })
  .meta({ description: "Every portable field shape softschema supports across Pydantic and Zod." });
