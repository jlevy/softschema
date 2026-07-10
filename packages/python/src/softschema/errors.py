"""Engine-neutral structural error records.

`jsonschema` (Python) and `ajv` (the future TypeScript port) word the same
violation differently. To keep structural errors byte-identical across
implementations, softschema does not surface the engine's native message.
Instead it normalizes each engine error into a stable record and synthesizes
the human-readable ``message`` from a shared template keyed on the failing
JSON Schema keyword (``validator``).

Schema-violation record shape:

    {
        "kind": "schema_violation",
        "path": ["properties", "..."] | [...],   # JSON path to the value
        "validator": "enum" | "minimum" | ...,    # the JSON Schema keyword
        "validator_value": <the keyword's value>,
        "value": <the offending instance value>,
        "message": "<synthesized, engine-neutral>",
    }

Numeric values in a record (and in the rendered message) use a canonical form:
a whole-valued float renders without a trailing fraction (``2.0`` -> ``2``), the
JSON-natural form the TypeScript implementation emits natively. See
``canonical_number``.

Malformed compiled schemas instead use a stable ``schema_invalid`` record with a
reason, constant message, and RFC 6901 ``schema_path``. Engine exception prose is
never copied into that record.

softschema-level artifact errors (missing envelope, malformed metadata, ...)
use the separate ``{"kind": ..., "message": ...}`` shape produced by
``softschema.validate._error`` and are not routed through here.
"""

from __future__ import annotations

from typing import Any, Literal

SCHEMA_VIOLATION_KIND = "schema_violation"
SchemaInvalidReason = Literal[
    "syntax",
    "value_domain",
    "root",
    "dialect",
    "metaschema",
    "identity",
    "profile",
    "pattern",
    "reference",
    "compile",
]

SCHEMA_INVALID_MESSAGES: dict[SchemaInvalidReason, str] = {
    "syntax": "compiled schema is not valid YAML or JSON",
    "value_domain": "compiled schema contains a non-portable YAML value",
    "root": "compiled schema root must be a mapping",
    "dialect": "compiled schema uses an unsupported JSON Schema dialect",
    "metaschema": "compiled schema does not conform to Draft 2020-12",
    "identity": "compiled schema resource identity is invalid",
    "profile": "compiled schema is outside the softschema profile",
    "pattern": "compiled schema contains an unsupported or invalid pattern",
    "reference": "compiled schema reference is unavailable offline",
    "compile": "compiled schema could not be compiled",
}


def schema_invalid_error(
    reason: SchemaInvalidReason,
    *,
    schema_path: str,
    **details: Any,
) -> dict[str, Any]:
    """Build a stable compiled-schema failure without engine exception prose."""
    return {
        "kind": "schema_invalid",
        "reason": reason,
        "message": SCHEMA_INVALID_MESSAGES[reason],
        "schema_path": schema_path,
        **details,
    }


def canonical_number(value: Any) -> Any:
    """Render a whole-valued float in its canonical (integer) form.

    JSON does not distinguish ``2`` from ``2.0``; the canonical softschema form
    drops a redundant trailing fraction so numeric values render byte-identically
    across the Python and TypeScript implementations (a YAML ``2.0`` token parses
    as the integer ``2`` in JS, which has no int/float distinction to lose).

    A whole-valued float below ``1e21`` is returned as ``int`` — that is exactly the
    range where JavaScript serializes a whole-valued ``number`` in plain integer form
    (``JSON.stringify``/``String``), so the Python ``int`` repr matches it. At or beyond
    ``1e21`` JavaScript switches to exponential notation, which Python's float repr also
    uses, so those floats are left unchanged. Ints, bools, and non-whole floats are
    returned unchanged.

    Byte-parity is guaranteed within the IEEE-754 safe-integer range (``abs < 2**53``).
    A larger *non-round* integer-valued magnitude cannot render identically on a
    double-only runtime and an arbitrary-precision one (Python's exact ``int`` vs JS's
    shortest round-trip), and is out of scope — see the golden corpus README, "Number
    formatting", edge (b).
    """
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e21:
        return int(value)
    return value


def _canonical(value: Any) -> Any:
    """Apply :func:`canonical_number` recursively through lists and dicts."""
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_canonical(v) for v in value)
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    return canonical_number(value)


def _fmt(value: Any) -> str:
    """Render a value compactly and deterministically for messages."""
    return repr(value)


def _fmt_list(values: Any) -> str:
    if isinstance(values, list | tuple):
        return ", ".join(_fmt(v) for v in values)
    return _fmt(values)


def render_structural_message(
    validator: str,
    validator_value: Any,
    value: Any,
) -> str:
    """Synthesize a stable, engine-neutral message for one structural error.

    The wording here is the cross-language contract: both the Python and the
    TypeScript implementations must produce byte-identical strings, so this
    template table is the single source of truth. Numeric values are rendered in
    their canonical form (whole-valued floats without a trailing fraction) so the
    string matches the TS renderer, which has no float/int distinction.
    """
    value = _canonical(value)
    validator_value = _canonical(validator_value)
    if validator == "enum":
        return f"value {_fmt(value)} is not one of [{_fmt_list(validator_value)}]"
    if validator == "type":
        return f"value {_fmt(value)} is not of type {_fmt_list(validator_value)}"
    if validator == "required":
        return f"required property {_fmt(validator_value)} is missing"
    if validator == "minimum":
        return f"value {_fmt(value)} is less than the minimum of {_fmt(validator_value)}"
    if validator == "maximum":
        return f"value {_fmt(value)} is greater than the maximum of {_fmt(validator_value)}"
    if validator == "exclusiveMinimum":
        return f"value {_fmt(value)} is not greater than {_fmt(validator_value)}"
    if validator == "exclusiveMaximum":
        return f"value {_fmt(value)} is not less than {_fmt(validator_value)}"
    if validator == "minItems":
        return f"array is shorter than the minimum of {_fmt(validator_value)} items"
    if validator == "maxItems":
        return f"array is longer than the maximum of {_fmt(validator_value)} items"
    if validator == "minLength":
        return f"string is shorter than the minimum length of {_fmt(validator_value)}"
    if validator == "maxLength":
        return f"string is longer than the maximum length of {_fmt(validator_value)}"
    if validator == "pattern":
        return f"value {_fmt(value)} does not match pattern {_fmt(validator_value)}"
    if validator == "additionalProperties":
        return "object has properties that are not allowed"
    if validator == "multipleOf":
        return f"value {_fmt(value)} is not a multiple of {_fmt(validator_value)}"
    # Fallback keeps unknown keywords legible without leaking engine text.
    return f"value {_fmt(value)} failed {validator} constraint {_fmt(validator_value)}"


def structural_error_record(
    *,
    path: list[Any],
    validator: str,
    validator_value: Any,
    value: Any,
) -> dict[str, Any]:
    """Build one engine-neutral structural error record."""
    # Store numbers in canonical form so the echoed `value`/`validator_value`
    # fields match the rendered message and the TS records byte-for-byte.
    validator_value = _canonical(validator_value)
    value = _canonical(value)
    return {
        "kind": SCHEMA_VIOLATION_KIND,
        "path": path,
        "validator": validator,
        "validator_value": validator_value,
        "value": value,
        "message": render_structural_message(validator, validator_value, value),
    }
