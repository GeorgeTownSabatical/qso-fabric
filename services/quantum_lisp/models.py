from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class QuantumLispProgram:
    source: str
    forms: list[Any]
    source_hash: str
    ast_hash: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "forms": self.forms,
            "source_hash": self.source_hash,
            "ast_hash": self.ast_hash,
        }


@dataclass(frozen=True, slots=True)
class QuantumReasoningIR:
    version: str
    source_hash: str
    ast_hash: str
    ir_hash: str
    declared_effects: list[str]
    backend_targets: list[str]
    forms: list[dict[str, Any]]
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source_hash": self.source_hash,
            "ast_hash": self.ast_hash,
            "ir_hash": self.ir_hash,
            "declared_effects": list(self.declared_effects),
            "backend_targets": list(self.backend_targets),
            "forms": [dict(form) for form in self.forms],
            "lineage": dict(self.lineage),
        }
