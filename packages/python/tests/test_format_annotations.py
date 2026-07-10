from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator

from softschema import validate_structural, validate_values

VECTORS_PATH = Path(__file__).resolve().parents[3] / "tests/parity/format-annotations.json"


def _vectors() -> dict[str, Any]:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def _schema_file(tmp_path: Path, schema: dict[str, Any]) -> Path:
    path = tmp_path / "format-annotation.schema.json"
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


def test_known_and_unknown_formats_are_warning_free_annotations(
    tmp_path: Path,
    capsys: Any,
) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for case in _vectors()["cases"]:
            result = validate_structural(
                case["value"],
                _schema_file(
                    tmp_path,
                    {"type": "string", "format": case["format"]},
                ),
            )
            assert result.ok is True, case["id"]
            assert result.errors == [], case["id"]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_non_format_assertions_still_apply(tmp_path: Path) -> None:
    schema = _schema_file(
        tmp_path,
        {"type": "string", "format": "email", "minLength": 20},
    )
    result = validate_structural("not-an-email", schema)
    assert result.ok is False
    assert [error["validator"] for error in result.errors] == ["minLength"]


class TrustedModel(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def reject_blocked(cls, value: str) -> str:
        if value == "blocked":
            raise ValueError("blocked by the trusted semantic model")
        return value


def test_semantic_model_remains_independent_of_format_annotations(tmp_path: Path) -> None:
    schema = _schema_file(
        tmp_path,
        {
            "type": "object",
            "properties": {"value": {"type": "string", "format": "email"}},
            "required": ["value"],
        },
    )
    result = validate_values({"value": "blocked"}, model=TrustedModel, schema=schema)
    assert result.structural.ok is True
    assert result.semantic.ok is False
