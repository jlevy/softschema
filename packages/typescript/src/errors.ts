/**
 * Engine-neutral structural error records. ajv words violations differently from
 * Python's jsonschema, so the message is synthesized here from the same template
 * table as the Python `errors.py`, and ajv errors are normalized into the same
 * record shape. Checked-profile verdicts must match; explicitly pinned native-engine
 * record-set deviations are allowed.
 */
import type { ErrorObject } from "ajv";

export const SCHEMA_VIOLATION_KIND = "schema_violation";

/**
 * `kind` + `code` + `path` + `property` is the documented field-repair match surface.
 * `validator` names the *mechanism* — which JSON Schema keyword fired — and is
 * diagnostic: one authoring mistake can reach a consumer through more than one keyword,
 * because an undeclared key reports `additionalProperties` on a simple schema and
 * `unevaluatedProperties` on a composed one. `code` names *what the author got wrong*
 * and is stable across both.
 */
export interface StructuralErrorRecord {
  kind: string;
  code: string;
  path: (string | number)[];
  property?: string;
  validator: string;
  validator_value: unknown;
  value: unknown;
  message: string;
}

// The stable category for a structural violation, as a pure function of `validator`.
// Keep in lockstep with the equivalent map in the Python `errors.py`.
const UNDECLARED_PROPERTY_VALIDATORS = new Set(["additionalProperties", "unevaluatedProperties"]);
const MISSING_PROPERTY_VALIDATORS = new Set(["required"]);

// Every keyword the message table renders a specific template for. A keyword outside
// this allowlist is reported as `unmapped_keyword` rather than silently folded into
// `invalid_value`, so the gap is greppable instead of invisible.
const INVALID_VALUE_VALIDATORS = new Set([
  "enum",
  "type",
  "minimum",
  "maximum",
  "exclusiveMinimum",
  "exclusiveMaximum",
  "minItems",
  "maxItems",
  "uniqueItems",
  "minLength",
  "maxLength",
  "pattern",
  "multipleOf",
  "const",
  "minProperties",
  "maxProperties",
  "anyOf",
  "oneOf",
  "allOf",
  "not",
  "dependentRequired",
  "format",
  "contains",
  "propertyNames",
  "prefixItems",
  "items",
]);

/** Return the stable softschema category for one JSON Schema keyword. */
export function structuralErrorCode(validator: string): string {
  if (UNDECLARED_PROPERTY_VALIDATORS.has(validator)) return "undeclared_property";
  if (MISSING_PROPERTY_VALIDATORS.has(validator)) return "missing_property";
  if (INVALID_VALUE_VALIDATORS.has(validator)) return "invalid_value";
  return "unmapped_keyword";
}

/**
 * Format a number in softschema's canonical form (matching Python's `repr()`).
 * Handles NaN, Infinity, and routes through exponential notation for abs >= 1e21
 * or (0 < abs < 1e-4 and non-integer), matching Python's float repr output.
 *
 * Canonical rule: a whole-valued number below 1e21 renders without a trailing fraction
 * and without an exponent (`2`, `10000000000000000`) — the natural `String(value)`
 * output, since JS has no int/float distinction and prints whole-valued numbers in
 * plain integer form below 1e21. The Python side converts its whole-valued floats below
 * 1e21 to int to match (see `canonical_number` in errors.py), so the two are
 * byte-identical (ss-wbnm). Exact agreement is guaranteed within the IEEE-754
 * safe-integer range (abs < 2**53); a larger non-round integer value may differ between
 * the runtimes (golden README, "Number formatting", edge b).
 */
function pyReprNumber(value: number): string {
  if (Number.isNaN(value)) return "nan";
  if (value === Infinity) return "inf";
  if (value === -Infinity) return "-inf";

  const abs = Math.abs(value);

  // Exponential formatting for large or small magnitudes (matches Python repr).
  if (abs >= 1e21 || (abs > 0 && abs < 1e-4 && !Number.isInteger(value))) {
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
  property?: string,
): string {
  switch (validator) {
    case "enum":
      return `value ${pyRepr(value)} is not one of [${pyReprList(validatorValue)}]`;
    case "type":
      return `value ${pyRepr(value)} is not of type ${pyReprList(validatorValue)}`;
    case "required":
      return `required property ${pyRepr(property ?? validatorValue)} is missing`;
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
    // Both closure keywords are one category to the author, so they share a message.
    // The generic fallback would otherwise spill the whole payload into the string.
    case "additionalProperties":
    case "unevaluatedProperties":
      return property === undefined
        ? "object has properties that are not allowed"
        : `property ${pyRepr(property)} is not allowed`;
    case "multipleOf":
      return `value ${pyRepr(value)} is not a multiple of ${pyRepr(validatorValue)}`;
    default:
      return `value ${pyRepr(value)} failed ${validator} constraint ${pyRepr(validatorValue)}`;
  }
}

export function structuralErrorRecord(args: {
  path: (string | number)[];
  property?: string;
  validator: string;
  validatorValue: unknown;
  value: unknown;
}): StructuralErrorRecord {
  const record: StructuralErrorRecord = {
    kind: SCHEMA_VIOLATION_KIND,
    code: structuralErrorCode(args.validator),
    path: args.path,
    validator: args.validator,
    validator_value: args.validatorValue,
    value: args.value,
    message: renderStructuralMessage(
      args.validator,
      args.validatorValue,
      args.value,
      args.property,
    ),
  };
  if (args.property !== undefined) record.property = args.property;
  return record;
}

function decodePointerToken(token: string): string {
  return token.replace(/~1/g, "/").replace(/~0/g, "~");
}

const ARRAY_INDEX_TOKEN = /^(?:0|[1-9][0-9]*)$/u;

function decodeInstancePath(instancePath: string, instance: unknown): (string | number)[] {
  let current = instance;
  return instancePath
    .split("/")
    .slice(1)
    .map((token) => {
      const decoded = decodePointerToken(token);
      if (Array.isArray(current) && ARRAY_INDEX_TOKEN.test(decoded)) {
        const index = Number(decoded);
        current = current[index];
        return index;
      }
      if (current !== null && typeof current === "object") {
        current = (current as Record<string, unknown>)[decoded];
      } else {
        current = undefined;
      }
      return decoded;
    });
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
export function normalizeAjvError(error: ErrorObject, instance?: unknown): StructuralErrorRecord {
  const path = decodeInstancePath(error.instancePath, instance);
  const property = ajvErrorProperty(error);
  return structuralErrorRecord({
    path,
    property,
    validator: error.keyword,
    validatorValue: error.schema,
    value: error.data,
  });
}

/** Extract the affected field name from ajv's keyword-specific parameters. */
function ajvErrorProperty(error: ErrorObject): string | undefined {
  const params = error.params as Record<string, unknown>;
  if (error.keyword === "required" && typeof params.missingProperty === "string") {
    return params.missingProperty;
  }
  if (error.keyword === "additionalProperties" && typeof params.additionalProperty === "string") {
    return params.additionalProperty;
  }
  if (error.keyword === "unevaluatedProperties" && typeof params.unevaluatedProperty === "string") {
    return params.unevaluatedProperty;
  }
  return undefined;
}

/**
 * Deduplicate undeclared-property errors by object path and affected property.
 *
 * ajv can report the same closure violation through multiple evaluated branches. Keep
 * one record for each affected field so consumers never lose field identity.
 *
 * Keyed on the `undeclared_property` code rather than a keyword list, so this stays
 * correct for both closure keywords: a simple schema reports `additionalProperties`
 * and a composed one reports `unevaluatedProperties`, and ajv over-reports both.
 */
export function collapseUndeclaredProperties(
  records: StructuralErrorRecord[],
): StructuralErrorRecord[] {
  const seen = new Set<string>();
  return records.filter((record) => {
    if (record.code !== "undeclared_property") return true;
    const key = JSON.stringify([record.path, record.property ?? null]);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/**
 * Drop ajv's `if` wrapper records.
 *
 * When a conditional fails, ajv emits the inner cause *and* an `if` record reading
 * `must match "then" schema`, which only restates it. Python's jsonschema never emits
 * one — a failing `if` is a false condition, not an error — so dropping the wrapper
 * aligns the engines without losing information.
 */
export function dropConditionalWrappers(records: StructuralErrorRecord[]): StructuralErrorRecord[] {
  return records.filter((record) => record.validator !== "if");
}

/** Deterministic, engine-independent order: path, keyword, then affected property. */
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
  const propertyA = a.property ?? "";
  const propertyB = b.property ?? "";
  if (propertyA < propertyB) return -1;
  if (propertyA > propertyB) return 1;
  return 0;
}
