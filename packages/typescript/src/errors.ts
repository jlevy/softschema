/**
 * Engine-neutral structural error records. ajv words violations differently from
 * Python's jsonschema, so the message is synthesized here from the same template
 * table as the Python `errors.py`, and ajv errors are normalized into the same
 * record shape. Output must be byte-identical across implementations.
 */
import type { ErrorObject } from "ajv";

export const SCHEMA_VIOLATION_KIND = "schema_violation";

export interface StructuralErrorRecord {
  kind: string;
  path: (string | number)[];
  validator: string;
  validator_value: unknown;
  value: unknown;
  message: string;
}

/** Mimic Python's `repr()` for the value kinds that appear in messages. */
function pyRepr(value: unknown): string {
  if (value === null || value === undefined) return "None";
  if (typeof value === "boolean") return value ? "True" : "False";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return pyReprStr(value);
  if (Array.isArray(value)) return `[${value.map(pyRepr).join(", ")}]`;
  return String(value);
}

function pyReprStr(s: string): string {
  const quote = s.includes("'") && !s.includes('"') ? '"' : "'";
  let out = "";
  for (const ch of s) {
    if (ch === "\\") out += "\\\\";
    else if (ch === quote) out += `\\${quote}`;
    else if (ch === "\n") out += "\\n";
    else if (ch === "\t") out += "\\t";
    else if (ch === "\r") out += "\\r";
    else out += ch;
  }
  return `${quote}${out}${quote}`;
}

function pyReprList(value: unknown): string {
  if (Array.isArray(value)) return value.map(pyRepr).join(", ");
  return pyRepr(value);
}

/**
 * Synthesize a stable, engine-neutral message for one structural error. The wording
 * is the cross-language contract and must match Python's `render_structural_message`.
 */
export function renderStructuralMessage(
  validator: string,
  validatorValue: unknown,
  value: unknown,
): string {
  switch (validator) {
    case "enum":
      return `value ${pyRepr(value)} is not one of [${pyReprList(validatorValue)}]`;
    case "type":
      return `value ${pyRepr(value)} is not of type ${pyReprList(validatorValue)}`;
    case "required":
      return `required property ${pyRepr(validatorValue)} is missing`;
    case "minimum":
      return `value ${pyRepr(value)} is less than the minimum of ${pyRepr(validatorValue)}`;
    case "maximum":
      return `value ${pyRepr(value)} is greater than the maximum of ${pyRepr(validatorValue)}`;
    case "exclusiveMinimum":
      return `value ${pyRepr(value)} is not greater than ${pyRepr(validatorValue)}`;
    case "exclusiveMaximum":
      return `value ${pyRepr(value)} is not less than ${pyRepr(validatorValue)}`;
    case "minItems":
      return `array is shorter than the minimum of ${pyRepr(validatorValue)} items`;
    case "maxItems":
      return `array is longer than the maximum of ${pyRepr(validatorValue)} items`;
    case "minLength":
      return `string is shorter than the minimum length of ${pyRepr(validatorValue)}`;
    case "maxLength":
      return `string is longer than the maximum length of ${pyRepr(validatorValue)}`;
    case "pattern":
      return `value ${pyRepr(value)} does not match pattern ${pyRepr(validatorValue)}`;
    case "additionalProperties":
      return "object has properties that are not allowed";
    case "multipleOf":
      return `value ${pyRepr(value)} is not a multiple of ${pyRepr(validatorValue)}`;
    default:
      return `value ${pyRepr(value)} failed ${validator} constraint ${pyRepr(validatorValue)}`;
  }
}

export function structuralErrorRecord(args: {
  path: (string | number)[];
  validator: string;
  validatorValue: unknown;
  value: unknown;
}): StructuralErrorRecord {
  return {
    kind: SCHEMA_VIOLATION_KIND,
    path: args.path,
    validator: args.validator,
    validator_value: args.validatorValue,
    value: args.value,
    message: renderStructuralMessage(args.validator, args.validatorValue, args.value),
  };
}

function decodePointerToken(token: string): string {
  return token.replace(/~1/g, "/").replace(/~0/g, "~");
}

function resolvePointer(data: unknown, path: string[]): unknown {
  let current: unknown = data;
  for (const key of path) {
    if (current !== null && typeof current === "object") {
      current = (current as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }
  return current;
}

function validatorValueFor(error: ErrorObject): unknown {
  const params = error.params as Record<string, unknown>;
  switch (error.keyword) {
    case "enum":
      return params.allowedValues;
    case "type":
      return params.type;
    case "required":
      return params.missingProperty;
    case "additionalProperties":
      return false;
    case "pattern":
      return params.pattern;
    default:
      // minimum/maximum/exclusive*/minItems/maxItems/minLength/maxLength/multipleOf
      return "limit" in params ? params.limit : undefined;
  }
}

/** Normalize one ajv error into the engine-neutral record (matching jsonschema's). */
export function normalizeAjvError(error: ErrorObject, data: unknown): StructuralErrorRecord {
  const path = error.instancePath.split("/").slice(1).map(decodePointerToken);
  return structuralErrorRecord({
    path,
    validator: error.keyword,
    validatorValue: validatorValueFor(error),
    value: resolvePointer(data, path),
  });
}

/** Deterministic, engine-independent order: by path (element-wise), then validator. */
export function compareStructuralRecords(
  a: StructuralErrorRecord,
  b: StructuralErrorRecord,
): number {
  const pa = a.path.map(String);
  const pb = b.path.map(String);
  for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
    const x = pa[i] as string;
    const y = pb[i] as string;
    if (x < y) return -1;
    if (x > y) return 1;
  }
  if (pa.length !== pb.length) return pa.length - pb.length;
  if (a.validator < b.validator) return -1;
  if (a.validator > b.validator) return 1;
  return 0;
}
