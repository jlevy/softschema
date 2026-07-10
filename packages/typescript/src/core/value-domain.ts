/** Portable JSON-compatible values and materialized-value normalization. */

const MIB = 1024 * 1024;

export interface JsonObject {
  [key: string]: JsonValue;
}

export type JsonValue = null | boolean | number | string | JsonValue[] | JsonObject;

/** Resource budgets applied at untrusted artifact and schema boundaries. */
export interface ValidationLimits {
  maxResourceBytes: number;
  maxBundleBytes: number;
  maxResources: number;
  maxNodesPerResource: number;
  maxDepth: number;
  maxScalarCodePoints: number;
}

/** Trusted per-call overrides; omitted fields retain the portable defaults. */
export type ValidationLimitOverrides = Partial<ValidationLimits>;

export const DEFAULT_VALIDATION_LIMITS: Readonly<ValidationLimits> = Object.freeze({
  maxResourceBytes: 8 * MIB,
  maxBundleBytes: 64 * MIB,
  maxResources: 256,
  maxNodesPerResource: 100_000,
  maxDepth: 128,
  maxScalarCodePoints: MIB,
});

/** Base class for stable portable-data boundary failures. */
export class PortableYamlError extends Error {
  readonly path: string;
  readonly line: number | null;
  readonly column: number | null;

  constructor(
    message: string,
    options: { path?: string; line?: number | null; column?: number | null } = {},
  ) {
    super(message);
    this.path = options.path ?? "";
    this.line = options.line ?? null;
    this.column = options.column ?? null;
  }
}

/** The input is not a single syntactically valid YAML document. */
export class PortableYamlSyntaxError extends PortableYamlError {}

/** The input is outside the bounded JSON-compatible value domain. */
export class PortableValueError extends PortableYamlError {}

interface Budget {
  limits: ValidationLimits;
  nodes: number;
}

export interface NormalizedValue {
  value: JsonValue;
  sizeBytes: number;
}

/** Resolve and validate caller-provided limit overrides. */
export function resolveValidationLimits(
  overrides: ValidationLimitOverrides = {},
): ValidationLimits {
  const limits = { ...DEFAULT_VALIDATION_LIMITS, ...overrides };
  const nonnegative = ["maxResourceBytes", "maxBundleBytes", "maxScalarCodePoints"] as const;
  const positive = ["maxResources", "maxNodesPerResource", "maxDepth"] as const;
  for (const name of [...nonnegative, ...positive]) {
    if (!Number.isSafeInteger(limits[name])) throw new TypeError(`${name} must be an integer`);
  }
  for (const name of nonnegative) {
    if (limits[name] < 0) throw new RangeError(`${name} must be nonnegative`);
  }
  for (const name of positive) {
    if (limits[name] < 1) throw new RangeError(`${name} must be positive`);
  }
  return limits;
}

/** Normalize a materialized value and return its compact canonical JSON size. */
export function normalizePortableValue(
  value: unknown,
  validationLimits: ValidationLimitOverrides = {},
  encodedSize?: number,
): NormalizedValue {
  const limits = resolveValidationLimits(validationLimits);
  if (encodedSize !== undefined && encodedSize > limits.maxResourceBytes) {
    throw new PortableValueError("maximum resource size exceeded");
  }
  const budget: Budget = { limits, nodes: 0 };
  const normalized = normalizeMaterialized(value, [], 1, budget, new Set());
  const sizeBytes = encodedSize ?? canonicalPortableJsonSize(normalized);
  if (sizeBytes > limits.maxResourceBytes) {
    throw new PortableValueError("maximum resource size exceeded");
  }
  return { value: normalized, sizeBytes };
}

/** Return the UTF-8 size of compact JSON with recursively sorted object keys. */
export function canonicalPortableJsonSize(value: JsonValue): number {
  if (value === null) return 4;
  if (typeof value === "boolean") return value ? 4 : 5;
  if (typeof value === "number") return canonicalNumberText(value).length;
  if (typeof value === "string") return utf8Size(JSON.stringify(value));
  if (Array.isArray(value)) {
    return (
      2 +
      Math.max(0, value.length - 1) +
      value.reduce<number>((size, item) => size + canonicalPortableJsonSize(item), 0)
    );
  }
  const keys = Object.keys(value).sort();
  return (
    2 +
    Math.max(0, keys.length - 1) +
    keys.reduce<number>(
      (size, key) =>
        size +
        utf8Size(JSON.stringify(key)) +
        1 +
        canonicalPortableJsonSize(value[key] as JsonValue),
      0,
    )
  );
}

function normalizeMaterialized(
  value: unknown,
  path: readonly (string | number)[],
  depth: number,
  budget: Budget,
  active: Set<object>,
): JsonValue {
  countNode(budget, path, depth);
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "string") {
    if ([...value].length > budget.limits.maxScalarCodePoints) {
      throw new PortableValueError("maximum scalar size exceeded", { path: jsonPointer(path) });
    }
    if (hasUnpairedSurrogate(value)) {
      throw new PortableValueError("string contains an invalid Unicode scalar", {
        path: jsonPointer(path),
      });
    }
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new PortableValueError("number must be finite", { path: jsonPointer(path) });
    }
    if (Number.isInteger(value) && !Number.isSafeInteger(value)) {
      throw new PortableValueError("integer is outside the safe range", {
        path: jsonPointer(path),
      });
    }
    return Object.is(value, -0) ? 0 : value;
  }
  if (typeof value !== "object" || value === undefined) {
    throw new PortableValueError("value is not JSON-compatible", { path: jsonPointer(path) });
  }
  if (active.has(value)) {
    throw new PortableValueError("cycles are not portable", { path: jsonPointer(path) });
  }
  active.add(value);
  try {
    if (Array.isArray(value)) {
      return value.map((item, index) =>
        normalizeMaterialized(item, [...path, index], depth + 1, budget, active),
      );
    }
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new PortableValueError("value is not JSON-compatible", { path: jsonPointer(path) });
    }
    const result: Record<string, JsonValue> = {};
    // Hidden and symbol metadata is outside the materialized JSON object surface.
    // Enumerable accessors remain forbidden so normalization never invokes user code.
    for (const key of Object.keys(value)) {
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (descriptor === undefined || !("value" in descriptor)) {
        throw new PortableValueError("value is not JSON-compatible", {
          path: jsonPointer([...path, key]),
        });
      }
      countNode(budget, path, depth + 1);
      if ([...key].length > budget.limits.maxScalarCodePoints) {
        throw new PortableValueError("maximum scalar size exceeded", { path: jsonPointer(path) });
      }
      if (hasUnpairedSurrogate(key)) {
        throw new PortableValueError("string contains an invalid Unicode scalar", {
          path: jsonPointer(path),
        });
      }
      Object.defineProperty(result, key, {
        configurable: true,
        enumerable: true,
        value: normalizeMaterialized(descriptor.value, [...path, key], depth + 1, budget, active),
        writable: true,
      });
    }
    return result;
  } finally {
    active.delete(value);
  }
}

function canonicalNumberText(value: number): string {
  const absolute = Math.abs(value);
  if (absolute > 0 && absolute < 1e-4 && !Number.isInteger(value)) {
    const [mantissa, rawExponent] = value.toExponential().split("e") as [string, string];
    const negative = rawExponent.startsWith("-");
    const digits = rawExponent.replace(/^[-+]/, "").padStart(2, "0");
    return `${mantissa}e${negative ? "-" : "+"}${digits}`;
  }
  return String(value);
}

function hasUnpairedSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (next < 0xdc00 || next > 0xdfff) return true;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true;
    }
  }
  return false;
}

function countNode(budget: Budget, path: readonly (string | number)[], depth: number): void {
  if (depth > budget.limits.maxDepth) {
    throw new PortableValueError("maximum depth exceeded", { path: jsonPointer(path) });
  }
  budget.nodes += 1;
  if (budget.nodes > budget.limits.maxNodesPerResource) {
    throw new PortableValueError("maximum node count exceeded", { path: jsonPointer(path) });
  }
}

function jsonPointer(path: readonly (string | number)[]): string {
  return path.map((part) => `/${String(part).replace(/~/g, "~0").replace(/\//g, "~1")}`).join("");
}

function utf8Size(value: string): number {
  return new TextEncoder().encode(value).byteLength;
}
