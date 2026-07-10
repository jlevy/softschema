/** Runtime-neutral deterministic JSON serialization helpers. */

/** Compare Unicode strings by scalar value, matching Python's string ordering. */
export function compareUnicodeCodePoints(left: string, right: string): number {
  const leftPoints = [...left];
  const rightPoints = [...right];
  const length = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < length; index += 1) {
    const leftPoint = leftPoints[index]?.codePointAt(0) as number;
    const rightPoint = rightPoints[index]?.codePointAt(0) as number;
    if (leftPoint !== rightPoint) return leftPoint < rightPoint ? -1 : 1;
  }
  return leftPoints.length < rightPoints.length
    ? -1
    : leftPoints.length > rightPoints.length
      ? 1
      : 0;
}

/**
 * Render one finite JavaScript number like Python's JSON encoder after softschema's
 * portable-value normalization. Both runtimes use a shortest round-trip mantissa; the
 * only remaining spelling difference in the portable domain is Python's exponent
 * threshold and its signed, two-digit exponent.
 */
function canonicalNumberText(value: number): string {
  if (!Number.isFinite(value)) throw new TypeError("JSON numbers must be finite");
  if (Object.is(value, -0)) return "0";
  if (Number.isInteger(value)) {
    if (!Number.isSafeInteger(value)) {
      throw new TypeError("JSON integers must be inside the safe range");
    }
    return String(value);
  }
  const absolute = Math.abs(value);
  if (absolute > 0 && absolute < 1e-4) {
    const raw = value.toExponential();
    const separator = raw.indexOf("e");
    const mantissa = raw.slice(0, separator);
    const exponent = raw.slice(separator + 1);
    const negative = exponent.startsWith("-");
    const digits = exponent.replace(/^[-+]/, "").padStart(2, "0");
    return `${mantissa}e${negative ? "-" : "+"}${digits}`;
  }
  return String(value);
}

function scalarJson(value: null | boolean | number | string): string {
  if (typeof value === "number") return canonicalNumberText(value);
  if (typeof value === "string" && hasUnpairedSurrogate(value)) {
    throw new TypeError("JSON strings must contain only Unicode scalar values");
  }
  return JSON.stringify(value);
}

function serializeJson(
  value: unknown,
  indent: number | null,
  depth: number,
  active: Set<object>,
): string {
  if (
    value === null ||
    typeof value === "boolean" ||
    typeof value === "number" ||
    typeof value === "string"
  ) {
    return scalarJson(value);
  }
  if (typeof value !== "object" || value === undefined) {
    throw new TypeError(`value of type ${typeof value} is not JSON-serializable`);
  }
  if (active.has(value)) throw new TypeError("circular values are not JSON-serializable");
  active.add(value);
  try {
    const nextDepth = depth + 1;
    const padding = indent === null ? "" : " ".repeat(indent * depth);
    const childPadding = indent === null ? "" : " ".repeat(indent * nextDepth);
    if (Array.isArray(value)) {
      const keys = Object.keys(value);
      if (keys.length !== value.length || keys.some((key, index) => key !== String(index))) {
        throw new TypeError("JSON arrays must contain dense own data elements only");
      }
      if (value.length === 0) return "[]";
      const items = Array.from({ length: value.length }, (_, index) =>
        serializeJson(ownDataValue(value, String(index)), indent, nextDepth, active),
      );
      return indent === null
        ? `[${items.join(",")}]`
        : `[\n${childPadding}${items.join(`,\n${childPadding}`)}\n${padding}]`;
    }

    const object = value as Record<string, unknown>;
    const prototype = Object.getPrototypeOf(object);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new TypeError("non-plain objects are not JSON-serializable");
    }
    const keys = Object.keys(object).sort(compareUnicodeCodePoints);
    if (keys.length === 0) return "{}";
    const separator = indent === null ? ":" : ": ";
    const properties = keys.map((key) => {
      if (hasUnpairedSurrogate(key)) {
        throw new TypeError("JSON object keys must contain only Unicode scalar values");
      }
      return `${JSON.stringify(key)}${separator}${serializeJson(ownDataValue(object, key), indent, nextDepth, active)}`;
    });
    return indent === null
      ? `{${properties.join(",")}}`
      : `{\n${childPadding}${properties.join(`,\n${childPadding}`)}\n${padding}}`;
  } finally {
    active.delete(value);
  }
}

function ownDataValue(object: object, key: string): unknown {
  const descriptor = Object.getOwnPropertyDescriptor(object, key);
  if (descriptor === undefined || !("value" in descriptor)) {
    throw new TypeError("JSON containers must not contain inherited values or accessors");
  }
  return descriptor.value;
}

function hasUnpairedSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (index + 1 >= value.length || next < 0xdc00 || next > 0xdfff) return true;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true;
    }
  }
  return false;
}

/** Pretty JSON matching Python's sorted, literal-Unicode encoder. */
export function stableStringify(value: unknown, indent = 2): string {
  if (!Number.isSafeInteger(indent) || indent < 0) {
    throw new TypeError("JSON indentation must be a nonnegative safe integer");
  }
  return serializeJson(value, indent, 0, new Set());
}

/** Compact JSON matching Python's sorted, literal-Unicode encoder. */
export function canonicalJson(value: unknown): string {
  return serializeJson(value, null, 0, new Set());
}
