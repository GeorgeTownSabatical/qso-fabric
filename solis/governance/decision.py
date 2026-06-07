from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from solis.schemas import SCHEMA_VERSION, parse_semver
from solis.shared.canonical_json import canonical_json
from solis.shared.hashing import sha256_hex_text

GOVERNOR_DECISION_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "governor_decision.schema.json"


class GovernorDecisionKind(str, Enum):
    REJECTED = "REJECTED"
    APPROVED_SHADOW = "APPROVED_SHADOW"
    APPROVED_EXECUTE = "APPROVED_EXECUTE"


class InvariantTraceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: str = Field(pattern="^(PASS|FAIL|SKIP)$")
    detail: str = Field(min_length=1)


class GovernorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    decision_id: str = Field(min_length=1)
    decision_ts: datetime
    intent_id: str = Field(min_length=1)
    decision: GovernorDecisionKind
    reason_codes: list[str] = Field(default_factory=list)
    invariant_trace: list[InvariantTraceRow] = Field(default_factory=list)
    policy_version: str = Field(min_length=2)
    actor: str = Field(min_length=1)
    signature: str = ""
    decision_hash: str | None = None

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        parse_semver(value)
        return value

    @field_validator("policy_version")
    @classmethod
    def _validate_policy_version(cls, value: str) -> str:
        text = str(value).strip()
        if not text.startswith("v") or not text[1:].isdigit():
            raise ValueError("policy_version must match v<integer>")
        return text

    @model_validator(mode="after")
    def _validate_decision_semantics(self) -> "GovernorDecision":
        if self.decision == GovernorDecisionKind.REJECTED and not self.reason_codes:
            raise ValueError("REJECTED decisions must include reason_codes")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude={"signature", "decision_hash"})
        return json.loads(canonical_json(payload))

    def compute_hash(self) -> str:
        return sha256_hex_text(canonical_json(self.canonical_payload()))

    def sign(self, signer: Callable[[str], str]) -> "GovernorDecision":
        digest = self.compute_hash()
        signature = signer(canonical_json(self.canonical_payload()))
        return self.model_copy(update={"decision_hash": digest, "signature": signature})


def validate_governor_decision(payload: dict[str, Any]) -> GovernorDecision:
    return GovernorDecision.model_validate(payload)


def load_governor_decision_schema(path: Path | None = None) -> dict[str, Any]:
    target = path or GOVERNOR_DECISION_SCHEMA_PATH
    loaded = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("governor decision schema must be a JSON object")
    return loaded
