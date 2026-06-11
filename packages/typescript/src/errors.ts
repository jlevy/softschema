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

/**
 * Format a number the way Python's `repr()` would. Handles NaN, Infinity, and
 * routes through exponential notation for abs >= 1e16 or (0 < abs < 1e-4 and
 * non-integer), matching Python's float repr output. Integer-valued floats
 * below 1e16 render without `.0` (the ss-wbnm limitation: YAML `2.0` parses as
 * JS integer `2`, so `.0` cannot be recovered).
 */
function pyReprNumber(value: number): string {
  if (Number.isNaN(value)) return "nan";
  if (value === Infinity) return "inf";
  if (value === -Infinity) return "-inf";

  const abs = Math.abs(value);

  // Exponential formatting for large or small magnitudes (matches Python repr).
  if (abs >= 1e16 || (abs > 0 && abs < 1e-4 && !Number.isInteger(value))) {
    // Use JS toExponential() (no fixed precision → shortest representation),
    // then reformat the exponent to Python style: always signed, at least 2 digits.
    const raw = value.toExponential();
    // raw is like "1.5e+16" or "1e-7" — split on 'e'
    const eIdx = raw.indexOf("e");
    const mantissa = raw.slice(0, eIdx);
    const expPart = raw.slice(eIdx + 1); // "+16" or "-7" or "16"
    let sign: string;
    let digits: string;
    if (expPart.startsWith("-")) {
      sign = "-";
      digits = expPart.slice(1);
    } else if (expPart.startsWith("+")) {
      sign = "+";
      digits = expPart.slice(1);
    } else {
      sign = "+";
      digits = expPart;
    }
    // Pad to at least 2 digits
    if (digits.length < 2) digits = `0${digits}`;
    return `${mantissa}e${sign}${digits}`;
  }

  return String(value);
}

/** Mimic Python's `repr()` for the value kinds that appear in messages. */
function pyRepr(value: unknown): string {
  if (value === null || value === undefined) return "None";
  if (typeof value === "boolean") return value ? "True" : "False";
  if (typeof value === "number") return pyReprNumber(value);
  if (typeof value === "string") return pyReprStr(value);
  if (Array.isArray(value)) return `[${value.map(pyRepr).join(", ")}]`;
  if (typeof value === "object") {
    // Python dict repr: {'k': v, ...} with repr'd string keys, ": " and ", " separators,
    // insertion order preserved. Matches `repr(dict)` so object-valued instances and enum
    // members render byte-identically (e.g. an object supplied where a string is expected).
    const entries = Object.entries(value as Record<string, unknown>).map(
      ([key, val]) => `${pyReprStr(key)}: ${pyRepr(val)}`,
    );
    return `{${entries.join(", ")}}`;
  }
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

/**
 * Normalize one ajv error into the engine-neutral record (matching jsonschema's).
 *
 * ajv must run with `verbose: true` so each error carries `schema` (the value of the
 * failing keyword) and `data` (the offending instance value). Those map exactly onto
 * Python jsonschema's `error.validator_value` and `error.instance`, so reading them
 * directly keeps the record byte-identical across implementations for every keyword.
 * The previous per-keyword `params` mapping diverged from Python (e.g. `multipleOf`
 * lives in `params.multipleOf`, not `params.limit`, and `required` is the missing key,
 * not the required list); `schema`/`data` sidestep all of that.
 */
export function normalizeAjvError(error: ErrorObject): StructuralErrorRecord {
  const path = error.instancePath.split("/").slice(1).map(decodePointerToken);
  return structuralErrorRecord({
    path,
    validator: error.keyword,
    validatorValue: error.schema,
    value: error.data,
  });
}

/**
 * Collapse `additionalProperties` errors to one record per object path.
 *
 * ajv (with `allErrors`) reports one `additionalProperties` error per disallowed key,
 * whereas Python jsonschema reports a single error for the whole object. After
 * normalization the ajv records for the same object are byte-identical, so keeping the
 * first per path reproduces jsonschema's one-record shape. Other keywords (e.g.
 * `required`, which jsonschema also reports once per missing key) are left untouched.
 */
export function collapseAdditionalProperties(
  records: StructuralErrorRecord[],
): StructuralErrorRecord[] {
  const seen = new Set<string>();
  return records.filter((record) => {
    if (record.validator !== "additionalProperties") return true;
    const key = JSON.stringify(record.path);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
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
