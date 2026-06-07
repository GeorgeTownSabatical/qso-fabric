from __future__ import annotations

import json
from pathlib import Path

from solis.schemas import is_backward_compatible, parse_semver


def test_parse_semver_and_compatibility_rules() -> None:
    assert parse_semver("1.0") == (1, 0)
    assert parse_semver("12.7") == (12, 7)

    assert is_backward_compatible("1.0", "1.0") is True
    assert is_backward_compatible("1.0", "1.3") is True
    assert is_backward_compatible("1.2", "1.1") is False
    assert is_backward_compatible("1.2", "2.0") is False


def test_all_governed_schemas_require_schema_version() -> None:
    schemas_dir = Path("solis/schemas")
    schema_paths = sorted(schemas_dir.glob("*.schema.json"))
    assert schema_paths

    for schema_path in schema_paths:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        assert "schema_version" in required, f"{schema_path} missing required schema_version"
        assert "schema_version" in properties, f"{schema_path} missing schema_version property"

        field = properties["schema_version"]
        assert field["type"] == "string", f"{schema_path} schema_version must be string"
