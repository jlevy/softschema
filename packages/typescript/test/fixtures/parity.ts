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
    active: z.boolean(),
    kind: z.enum(["alpha", "beta", "gamma"]),
    priority: z.int().default(1),
    label: z.string().default("none"),
    enabled: z.boolean().default(true),
    tags: z.array(z.string()).min(1),
    notes: z.string().nullable().default(null),
    nickname: z.string().nullable().default("n/a"),
    rank: z.enum(["low", "high"]).nullable().default(null),
    primary: Address,
    secondary: Address.nullable().default(null),
    history: z.array(Event).optional(),
    last_event: Event.nullable().default(null),
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
