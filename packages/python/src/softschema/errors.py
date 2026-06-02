"""Engine-neutral structural error records.

`jsonschema` (Python) and `ajv` (the future TypeScript port) word the same
violation differently. To keep structural errors byte-identical across
implementations, softschema does not surface the engine's native message.
Instead it normalizes each engine error into a stable record and synthesizes
the human-readable ``message`` from a shared template keyed on the failing
JSON Schema keyword (``validator``).

Record shape (every structural validation error):

    {
        "kind": "schema_violation",
        "path": ["properties", "..."] | [...],   # JSON path to the value
        "validator": "enum" | "minimum" | ...,    # the JSON Schema keyword
        "validator_value": <the keyword's value>,
        "value": <the offending instance value>,
        "message": "<synthesized, engine-neutral>",
    }

Softschema-level artifact errors (missing envelope, malformed metadata, ...)
use the separate ``{"kind": ..., "message": ...}`` shape produced by
``softschema.validate._error`` and are not routed through here.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VIOLATION_KIND = "schema_violation"


def _fmt(value: Any) -> str:
    """Render a value compactly and deterministically for messages."""
    return repr(value)


def _fmt_list(values: Any) -> str:
    if isinstance(values, (list, tuple)):
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
    template table is the single source of truth.
    """
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
    return {
        "kind": SCHEMA_VIOLATION_KIND,
        "path": path,
        "validator": validator,
        "validator_value": validator_value,
        "value": value,
        "message": render_structural_message(validator, validator_value, value),
    }
