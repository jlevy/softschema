"""Runtime-neutral softschema contract core.

This namespace accepts and returns JSON-compatible values. It does not parse YAML,
touch the filesystem, load Pydantic models, dynamically import code, or implement a
command-line interface. Those operations remain in the compatibility/runtime modules.
"""

from __future__ import annotations

from softschema.canonicalize import (
    ENFORCEMENT_UNSUPPORTED_MESSAGE,
    EnforcementUnsupportedError,
    apply_enforced_extras,
    canonicalize_json_schema,
)
from softschema.core.envelope import EnvelopeAmbiguityError, infer_envelope_key
from softschema.core.identity import (
    validate_contract_id,
    validate_extension_namespace,
    validate_schema_id,
)
from softschema.core.metadata import ARTIFACT_FORMAT_VERSION, SchemaProfile, SchemaStatus
from softschema.core.results import SemanticResult, StructuralResult, ValidationResult
from softschema.core.value_domain import (
    DEFAULT_VALIDATION_LIMITS,
    JsonValue,
    PortableValueError,
    ValidationLimits,
    normalize_portable_value,
)
from softschema.errors import (
    SCHEMA_INVALID_MESSAGES,
    SCHEMA_VIOLATION_KIND,
    SchemaInvalidReason,
    canonical_number,
    render_structural_message,
    schema_invalid_error,
    structural_error_record,
)
from softschema.patterns import (
    PORTABLE_PATTERN_MAX_QUANTIFIER,
    PORTABLE_PATTERN_PROFILE,
    PortablePatternError,
    first_unsupported_pattern,
    is_portable_pattern,
    portable_pattern_matches,
)

__all__ = [
    "ARTIFACT_FORMAT_VERSION",
    "DEFAULT_VALIDATION_LIMITS",
    "ENFORCEMENT_UNSUPPORTED_MESSAGE",
    "PORTABLE_PATTERN_MAX_QUANTIFIER",
    "PORTABLE_PATTERN_PROFILE",
    "SCHEMA_INVALID_MESSAGES",
    "SCHEMA_VIOLATION_KIND",
    "EnforcementUnsupportedError",
    "EnvelopeAmbiguityError",
    "JsonValue",
    "PortablePatternError",
    "PortableValueError",
    "SchemaInvalidReason",
    "SchemaProfile",
    "SchemaStatus",
    "SemanticResult",
    "StructuralResult",
    "ValidationLimits",
    "ValidationResult",
    "apply_enforced_extras",
    "canonical_number",
    "canonicalize_json_schema",
    "first_unsupported_pattern",
    "infer_envelope_key",
    "is_portable_pattern",
    "normalize_portable_value",
    "portable_pattern_matches",
    "render_structural_message",
    "schema_invalid_error",
    "structural_error_record",
    "validate_contract_id",
    "validate_extension_namespace",
    "validate_schema_id",
]
