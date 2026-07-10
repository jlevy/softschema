/** Executable contracts for public TypeScript API examples. */

import { expect, test } from "bun:test";
import {
  type SchemaResources,
  type ValidationLimitOverrides,
  validateValues,
} from "../src/node.js";

const addressId = "https://example.com/schemas/address/v1";
const resources: SchemaResources = {
  [addressId]: {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    $id: addressId,
    type: "object",
    required: ["city"],
    properties: { city: { type: "string" } },
    additionalProperties: false,
  },
};
const validationLimits: ValidationLimitOverrides = {
  maxResourceBytes: 16 * 1024 * 1024,
};

test("API resource and limit examples use the typed public option shapes", () => {
  const result = validateValues(
    { address: { city: "Kyoto" } },
    {
      schema: {
        $schema: "https://json-schema.org/draft/2020-12/schema",
        type: "object",
        required: ["address"],
        properties: { address: { $ref: addressId } },
        additionalProperties: false,
      },
      resources,
      validationLimits,
    },
  );
  expect(result.structural).toEqual({
    ok: true,
    errors: [],
    engine: "json_schema",
    skipped_reason: null,
  });
});
