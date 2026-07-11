"""Compatibility tests for the intentionally small package-root API."""

from __future__ import annotations

import softschema

V0_2_PUBLIC_API = frozenset(
    {
        "SOFTSCHEMA_FORMAT_VERSION",
        "ArtifactValidationResult",
        "CompileResult",
        "Contract",
        "Contracts",
        "EnvelopeAmbiguityError",
        "FieldInfo",
        "GeneratedSection",
        "RegenerateResult",
        "RepairKind",
        "SchemaMetadata",
        "SchemaProfile",
        "SchemaStatus",
        "SchemaView",
        "SchemaWarning",
        "SemanticResult",
        "SoftField",
        "SoftFieldMeta",
        "SoftOwner",
        "SoftTier",
        "StructuralResult",
        "ValidationResult",
        "WarningCode",
        "apply_enforced_extras",
        "canonicalize_json_schema",
        "compile_model",
        "infer_envelope_key",
        "parse_schema_metadata",
        "regenerate",
        "validate_artifact",
        "validate_semantic",
        "validate_structural",
        "validate_values",
    }
)


def test_v0_2_root_api_remains_explicit_and_importable_during_v0_3() -> None:
    exports = softschema.__all__
    public = set(exports)
    assert len(exports) == len(public)
    assert public >= V0_2_PUBLIC_API
    assert all(getattr(softschema, name) is not None for name in V0_2_PUBLIC_API)
