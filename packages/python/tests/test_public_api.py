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


def test_v0_2_root_api_remains_importable_during_v0_3() -> None:
    public = set(softschema.__all__)
    assert public >= V0_2_PUBLIC_API
    assert all(getattr(softschema, name) is not None for name in V0_2_PUBLIC_API)


def test_root_all_is_an_explicit_well_formed_compatibility_surface() -> None:
    public = softschema.__all__
    assert public
    assert len(public) == len(set(public))
    assert all(isinstance(name, str) and name and not name.startswith("_") for name in public)
    assert all(hasattr(softschema, name) for name in public)
