"""Load human-reviewed YAML fixtures without using softschema code under test."""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def load_yaml_fixture(path: Path) -> Any:
    parser = YAML(typ="safe")
    parser.allow_duplicate_keys = False
    return parser.load(path)
