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

Numeric values in a record (and in the rendered message) use a canonical form:
a whole-valued float renders without a trailing fraction (``2.0`` -> ``2``), the
JSON-natural form the TypeScript implementation emits natively. See
``canonical_number``.

softschema-level artifact errors (missing envelope, malformed metadata, ...)
use the separate ``{"kind": ..., "message": ...}`` shape produced by
``softschema.validate._error`` and are not routed through here.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VIOLATION_KIND = "schema_violation"


def canonical_number(value: Any) -> Any:
    """Render a whole-valued float in its canonical (integer) form.

    JSON does not distinguish ``2`` from ``2.0``; the canonical softschema form
    drops a redundant trailing fraction so numeric values render byte-identically
    across the Python and TypeScript implementations (a YAML ``2.0`` token parses
    as the integer ``2`` in JS, which has no int/float distinction to lose). A
    whole-valued float is returned as ``int``; everything else — ``int``, ``bool``,
    non-whole floats, and floats at or beyond ``1e16`` (where ``repr`` switches to
    exponential notation, matching the TS formatter) — is returned unchanged.
    """
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e16:
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
