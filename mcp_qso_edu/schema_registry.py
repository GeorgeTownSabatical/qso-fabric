from __future__ import annotations

from copy import deepcopy
from typing import Any


class SchemaRegistry:
    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {
            "object": {"type": "object"},
            "simulation": {"type": "simulation", "properties": {"state": {"type": "object"}}},
            "identity": {"type": "identity", "properties": {"subject_ref": {"type": "string"}}},
            "transport_simulation": {
                "type": "transport_simulation",
                "properties": {
                    "latency_ms": {"type": "number"},
                    "error_rate": {"type": "number"},
                    "volatility": {"type": "number"},
                },
            },
            "conversation": {
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string"},
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "author", "role", "content", "timestamp"],
                            "properties": {
                                "id": {"type": "string"},
                                "author": {"type": "string"},
                                "role": {"type": "string", "enum": ["user", "assistant", "system", "agent"]},
                                "content": {"type": "string"},
                                "timestamp": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }

    def list_schemas(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self._schemas)

    def get(self, name: str) -> dict[str, Any]:
        if name not in self._schemas:
            raise KeyError(f"unknown schema: {name}")
        return deepcopy(self._schemas[name])
